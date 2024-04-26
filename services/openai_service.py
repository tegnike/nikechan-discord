import aiofiles
import os
import re
import time
from openai import OpenAI
from services.function_calling_service import search_web, describe_image, create_image
from services.system_message_service import get_system_message
from services.attachment_service import get_attachment_data

client = OpenAI()

async def send_openai_response(message, messages_for_history, model_name, thread_id):
    ASSISTANT_ID = 'asst_Dyf8M2h6lPdojCmouzgDbc7t'
    END_ACTIONS = ["completed", "expired", "failed", "cancelled"]

    images = {}
    image_names = []
    file_names = []
    file_ids = []
    if message.attachments:
        for attachment in message.attachments:
            if re.search(r'\.(png|jpeg|jpg|gif|webp)$', attachment.filename):
                images[attachment.filename] = await get_attachment_data(attachment)
                image_names.append(attachment.filename)
                print("Temporary image saved:", attachment.filename)
            elif re.search(r'\.(c|cpp|csv|docx|html|java|json|md|pdf|php|pptx|py|py|rb|tex|txt)$', attachment.filename):
                # ファイルの内容を一時ファイルに保存
                temp_file_path = f"/tmp/{attachment.filename}"
                file_bytes = await attachment.read()  # Discordからファイルのバイトを読み込む

                # 非同期でファイルを一時的に保存
                async with aiofiles.open(temp_file_path, 'wb') as temp_file:
                    await temp_file.write(file_bytes)

                # 一時ファイルをOpenAI APIに渡す
                try:
                    with open(temp_file_path, 'rb') as file_stream:
                        file = client.files.create(
                            file=file_stream,
                            purpose='assistants'
                        )
                        file_ids.append(file.id)
                        print("file uploaded:", file.id)
                        file_names.append(attachment.filename)
                finally:
                    # 使用後は一時ファイルを削除
                    os.remove(temp_file_path)

    for index, message_for_history in enumerate(messages_for_history):
        # index がmessages_for_historyの長さ-1のときは、最後のメッセージなので、画像を添付する
        if index == len(messages_for_history) - 1:
            content = message_for_history
            if image_names:
                content += f"\n次の画像が添付されています：{', '.join(image_names)}。\nこれらの画像から新しい画像を生成したい場合は、最初に describe_image 関数を使用し、その後で create_image 関数を使用してください。"
            if file_names:
                content += f"\n次のファイルが添付されています：{', '.join(file_names)}。\nユーザがこれらのファイルを使用して何かを行うことを期待している場合は、file_searchを使用してファイルの中身を確認してください。"
        else:
            content = message_for_history

        retry_count = 0
        while retry_count < 5:
            try:
                attachments = []
                for file_id in file_ids:
                    attachments.append({
                        "file_id": file_id,
                        "tools": [
                            {"type": "code_interpreter"},
                            {"type": "file_search"}
                        ]
                    })
                client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=content,
                    attachments=attachments
                )
                break
            except Exception as e:
                if re.search("Can't add messages to thread_.* while a run .* is active.", str(e)):
                    time.sleep(2)
                    retry_count += 1
                    continue
                else:
                    raise e
        if retry_count >= 10:
            return "Couldn't add messages to thread while a run is active.", thread_id

    try:
        create_run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
            truncation_strategy={
                "type": "last_messages",
                "last_messages": 20,
            }
        )

        while True:
            retrieve_run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=create_run.id
            )
            print(retrieve_run.status)
            # completed, expired, failed, cancelled の場合
            if retrieve_run.status in END_ACTIONS:
                break
            elif retrieve_run.status == "requires_action":
                tool_outputs = []
                for index, tool_call in enumerate(retrieve_run.required_action.submit_tool_outputs.tool_calls):
                    function_name = tool_call.function.name
                    print(f"function_name[{index}]: {function_name}")
                    call_id = tool_call.id
                    if function_name == "describe_image":
                        res = await describe_image(tool_call, images)

                    elif function_name == "create_image":
                        res = await create_image(message, tool_call)

                    elif function_name == "search_web":
                        res = await search_web(tool_call)

                    tool_outputs.append({
                        "tool_call_id": call_id,
                        "output": res,
                    })

                client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=create_run.id,
                    tool_outputs=tool_outputs
                )
            time.sleep(1)

        messages = client.beta.threads.messages.list(
            thread_id=thread_id
        )

        # メッセージを送信
        response_message = messages.data[0].content[0].text.value
        await message.channel.send(response_message)
        return response_message, thread_id
    except Exception as e:
        cancel_run = client.beta.threads.runs.cancel(
            thread_id=thread_id,
            run_id=create_run.id
        )
        while True:
            retrieve_run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=cancel_run.id
            )
            print(retrieve_run.status)
            if retrieve_run.status in END_ACTIONS:
                break
            time.sleep(1)
        raise e

async def judge_if_i_response(message, history):
    # URLのみ/添付のみ/スタンプのみ/botかどうかをチェック
    url_regex = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    if re.search(url_regex, message.content): # URLチェック
        return False
    for attachment in message.attachments: # ファイルサイズチェック
        if attachment.size > 512000000:
            return False
    if len(message.attachments) > 0: # 添付チェック
        if message.content == '':
            return False
        else:
            return True
    if len(message.stickers) > 0: # スタンプチェック
        return False
    if message.author.bot: # botチェック
        return False

    # 過去5件のメッセージを取得
    latest_messages = history[-5:]
    past_messages = "You're name is 'ニケ'\n"
    for latest_message in latest_messages:
        if latest_message["role"] == "user":
            # latest_message["content"]から日付部分を削除する
            past_messages += re.sub(r'\(\d{4}/\d{2}/\d{2} \d{2}:\d{2}\)', '', latest_message["content"]) + "\n"
        else:
            past_messages += "ニケ: " + latest_message["content"] + "\n"

    # OpenAIによる応答生成
    prompt = get_system_message("judge_if_i_response.txt").replace("{{conversations}}", past_messages)
    response = client.completions.create(model="gpt-3.5-turbo-instruct", prompt=prompt)
    print("judge_if_i_response: response:", response.choices[0].text)
    result = response.choices[0].text.lower()
    return result.replace(" ", "") == "true"

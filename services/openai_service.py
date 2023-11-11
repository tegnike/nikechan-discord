import re
import time
from openai import OpenAI
from services.function_calling_service import search_web, describe_image, create_image
from services.system_message_service import get_system_message
from services.attachment_service import get_attachment_data

client = OpenAI()

async def send_openai_response(message, messages_for_history, model_name, thread_id):
    assistant_id = 'asst_Dyf8M2h6lPdojCmouzgDbc7t'

    images = {}
    image_name = ""
    file_ids = []
    if message.attachments:
        for attachment in message.attachments:
            if re.search(r'\.(png|jpeg|jpg|gif|webp)$', attachment.filename):
                if image_name != "":
                    continue
                images[attachment.filename] = await get_attachment_data(attachment)
                image_name = attachment.filename
                print("Temporary image saved:", attachment.filename)
            elif re.search(r'\.(c|cpp|csv|docx|html|java|json|md|pdf|php|pptx|py|py|rb|tex|txt)$', attachment.filename):
                file = client.files.create(
                    file=open(attachment.filename, "rb"),
                    purpose='assistants'
                )
                file_ids.push(file.id)
                print("file uploaded:", file.id)

    for index, message_for_history in enumerate(messages_for_history):
        # index がmessages_for_historyの長さ-1のときは、最後のメッセージなので、画像を添付する
        if index == len(messages_for_history) - 1:
            if images == {}:
                content = message_for_history
            else:
                content = f"{message_for_history}\n次の画像が添付されています。{image_name}\nIf user wants to generate an image from an image, please use describe_image function first, then create_image function."
        else:
            content = message_for_history

        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content,
            file_ids=file_ids
        )

    try:
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

        while True:
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            print(run.status)
            # completed, expired, failed, cancelled の場合
            if run.status in ["completed", "expired", "failed", "cancelled"]:
                break
            elif run.status == "requires_action":
                tool_outputs = []
                for index, tool_call in enumerate(run.required_action.submit_tool_outputs.tool_calls):
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

                run = client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
            time.sleep(1)

        messages = client.beta.threads.messages.list(
            thread_id=thread_id
        )

        # メッセージを送信
        response_message = messages.data[0].content[0].text.value
        await message.channel.send(response_message)
        return response_message
    except Exception as e:
        cancel_run = client.beta.threads.runs.cancel(
            thread_id=thread_id,
            run_id=run.id
        )
        while True:
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=cancel_run.id
            )
            print(run.status)
            if run.status == "cancelled":
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

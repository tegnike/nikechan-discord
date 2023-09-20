from services.function_calling_service import ask_function_calling
import json, re
import openai

def get_system_message(file_name):
    with open('services/system_messages/' + file_name, 'r') as file:
        return file.read().strip()

def get_response_system_message(type):
    # 置換文字列が書かれたJSONファイルを読み込む
    with open(f'services/system_messages/system_{type}.json', 'r', encoding='utf-8') as file:
        replacement_dict = json.load(file)

    # 元の文章のtxtファイルを読み込む
    with open('services/system_messages/response_message.txt', 'r', encoding='utf-8') as file:
        content = file.read()

    # 文章の中の特定の英字を探す & その英字を先ほどの辞書に基づいて置換する
    for original, replacement in replacement_dict.items():
        if original == "{{EXAMPLES}}":
            replacement = json.dumps(replacement, ensure_ascii=False, indent=2)
        if original == "{{NOTE}}":
            replacement = ' '.join(replacement)
        content = content.replace(original, replacement)

    return content

async def get_openai_response(history, model_name, type):
    # functuion_calling
    function_calling_result = await ask_function_calling(history[-15:])
    if function_calling_result != None:
        print("function calling: True")
        print("function calling result:", function_calling_result)
        history.append({"role": "user", "content": "検索結果: " + function_calling_result})
    else:
        print("function calling: False")

    retry_count = 0
    response_result = ''
    while True:
        try:
            # OpenAIによる応答生成
            messages = [{"role": "system", "content": get_response_system_message(type)}] + history
            if retry_count > 0:
                messages = messages + [{"role": "user", "content": "途中で切れているようなので、続きから回答短めでお願いします。"}]
            model_name = "gpt-3.5-turbo" if retry_count > 0 else model_name
            response = openai.ChatCompletion.create(
                model=model_name,
                messages=messages,
                temperature=0,
                max_tokens=350
            )
            response_message = response["choices"][0]["message"]["content"]

            # 会話履歴を更新
            history.append({"role": "assistant", "content": response_message})

            response_result = response_result + response_message
            retry_count = retry_count + 1

            # 応答が終了したかどうか判断
            if response["choices"][0]["finish_reason"] == "stop" or retry_count > 5:
                print("AI:", response_result)
                return response_result
        except Exception as e:
            # トークン超過の場合はhistoryを短くして再トライ
            if "This model's maximum context length" in str(e):
                history = history[2:]
            else:
                raise e

    # if type != 'base':
    #     messages = [SystemMessage(content="次の発言をAIが回答するような、丁寧な口調に戻してください。")] + [HumanMessage(content=(response_message))]
    #     llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    #     response = llm(messages)
    #     # 通常口調に戻してから会話履歴を更新
    #     history.add_ai_message(response.content)
    #     if type == 'gal':
    #         messages2 = [SystemMessage(content=get_system_message(f"message_convert_galmoji.txt"))] + [HumanMessage(content=response.content)]
    #         llm2 = ChatOpenAI(model_name=model_name, temperature=0)
    #         response2 = llm2(messages2)
    #         return response2.content
    #     else:
    #         return response_message
    # else:
    #     # 会話履歴を更新
    #     history.add_ai_message(response_message)
    #     return response_message

async def judge_if_i_response(message, history):
    # URLのみ/添付のみ/スタンプのみ/botかどうかをチェック
    url_regex = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    if re.search(url_regex, message.content): # URLチェック
        return False
    if len(message.attachments) > 0 and message.content == '': # 添付チェック
        print('添付のみ')
        return False
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
    messages = [{"role": "system", "content": get_system_message("judge_if_i_response.txt")}, {"role": "user", "content": past_messages}]
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages, temperature=1.0, max_tokens=2)

    result = response["choices"][0]["message"]["content"].lower()
    return result == "true"

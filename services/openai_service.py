from services.my_function_calling_service import check_if_i_dont_know, web_search_detail
from services.system_message_service import get_system_message, get_response_system_message
from services.select_random_message_service import select_random_message
import re, asyncio, random
import openai

async def send_openai_response(message, history, model_name, type):
    MAX_RETRIES = 5
    BACKOFF_FACTOR = 0.1
    JITTER_FACTOR = 0.02
    retry_count = 0
    response_result = ''
    
    while retry_count < MAX_RETRIES:
        try:
            # OpenAIによる応答生成
            messages = [{"role": "system", "content": get_response_system_message(type)}] + history
            if retry_count > 0:
                messages = messages + [{"role": "user", "content": "途中で切れているようなので、続きから回答短めでお願いします。"}]
                response = openai.Completion.create(
                    model="gpt-3.5-turbo-instruct",
                    prompt="途中で切れているようなので、続きから回答短めでお願いします。" + "\n\n" + history[-1]["content"],
                    max_tokens=350,
                    temperature=1.0,
                )
                response_message = response["choices"][0]["text"]
            else:
                response = openai.ChatCompletion.create(
                    model=model_name,
                    messages=messages,
                    temperature=0,
                    max_tokens=350
                )
                response_message = response["choices"][0]["message"]["content"]

            # if retry_count == 0:
            #     # 知らないときの応答
            #     if_i_dont_know_result = await check_if_i_dont_know(history + [{"role": "assistant", "content": response_message}])
            #     if not if_i_dont_know_result["if_i_know"]:
            #         i_dont_know_message = select_random_message('i_dont_know_messages')
            #         # メッセージリストからランダムに選択
            #         print("AI:", i_dont_know_message)
            #         history.append({"role": "assistant", "content": i_dont_know_message})
            #         await message.channel.send(i_dont_know_message)

            #         try:
            #             web_search_result = await web_search_detail(if_i_dont_know_result)
            #             # 会話履歴を更新
            #             history.append({"role": "user", "content": f"検索結果: {web_search_result}"})
            #             # OpenAIによる応答生成
            #             messages = [{"role": "system", "content": get_response_system_message(type)}] + history
            #             model_name = "gpt-3.5-turbo"
            #             response = openai.ChatCompletion.create(
            #                 model=model_name,
            #                 messages=messages,
            #                 temperature=0,
            #                 max_tokens=350
            #             )
            #             response_message = response["choices"][0]["message"]["content"]
            #         except Exception as e:
            #             print(f"web_search_detail: Error: {e}")
            #             finally_couldnt_find_message = select_random_message('finally_couldnt_find_messages')
            #             # やっぱりわからなかったときのメッセージをリストからランダムに選択
            #             print("AI:", finally_couldnt_find_message)
            #             history.append({"role": "assistant", "content": finally_couldnt_find_message})
            #             await message.channel.send(finally_couldnt_find_message)
            #             return finally_couldnt_find_message

            # 会話履歴を更新
            history.append({"role": "assistant", "content": response_message})

            response_result = response_result + response_message
            retry_count = retry_count + 1

            # 応答が終了したかどうか判断
            if response["choices"][0]["finish_reason"] == "stop" or retry_count > 3:
                print("AI:", response_result)
                # メッセージを送信
                await message.channel.send(response_result)
                return response_result

            retry_count += 1

        except Exception as e:
            # トークン超過の場合はhistoryを短くして再トライ
            if "This model's maximum context length" in str(e):
                history = history[2:]
                await asyncio.sleep(BACKOFF_FACTOR * (2 ** retry_count) + random.uniform(0,JITTER_FACTOR))
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
    prompt = get_system_message("judge_if_i_response.txt").replace("{{conversations}}", past_messages)
    response = openai.Completion.create(model="gpt-3.5-turbo-instruct", prompt=prompt, temperature=1.0, max_tokens=2)

    result = response["choices"][0]["text"].lower()
    print("judge_if_i_response: result:", result.replace(" ", ""))
    return result.replace(" ", "") == "true"

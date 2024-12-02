import json


def get_system_message(file_name):
    with open("services/system_messages/" + file_name, "r") as file:
        return file.read().strip()


def get_response_system_message(type):
    # 置換文字列が書かれたJSONファイルを読み込む
    with open(
        f"services/system_messages/system_{type}.json", "r", encoding="utf-8"
    ) as file:
        replacement_dict = json.load(file)

    # 元の文章のtxtファイルを読み込む
    with open(
        "services/system_messages/response_message.txt", "r", encoding="utf-8"
    ) as file:
        content = file.read()

    # 文章の中の特定の英字を探す & その英字を先ほどの辞書に基づいて置換する
    for original, replacement in replacement_dict.items():
        if original == "{{EXAMPLES}}":
            replacement = json.dumps(replacement, ensure_ascii=False, indent=2)
        if original == "{{NOTE}}":
            replacement = " ".join(replacement)
        content = content.replace(original, replacement)

    return content

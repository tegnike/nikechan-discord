import json, random

def select_random_message(script):
    # ファイルからメッセージをロード
    with open(f'services/scripts/{script}', 'r') as f:
        messages = json.load(f)
    return random.choice(messages)

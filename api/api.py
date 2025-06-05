import os
from dotenv import load_dotenv
import requests

load_dotenv()


def get_headers(api_key):
    return {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

def get_vscode_url(conversation_id, api_key):
    response = requests.get(
        f'https://app.all-hands.dev/api/conversations/{conversation_id}/vscode-url',
        headers=get_headers(api_key)
    )
    return response.json()

def create_conversation(task, api_key):
    url = 'https://app.all-hands.dev/api/conversations'
    data = {
        'initial_user_msg': task,
    }
    response = requests.post(url, json=data, headers=get_headers(api_key))
    conversation_id = response.json()['conversation_id']
    reply = f'You can check the conversation at https://app.all-hands.dev/conversations/{conversation_id}'
    return reply

if __name__ == '__main__':
    # print(create_conversation('print todays date', os.getenv('OPENHANDS_API_KEY')))
    print(get_vscode_url('e50de0b48e37480d9fdcfbfc2f779a94', os.getenv('OPENHANDS_API_KEY')))

#!python
import json
import os
import re
import subprocess
import sys
import webbrowser
from pprint import pprint

import requests

if sys.argv[1:]:
    file = sys.argv[1]
else:
    from pyperclip import paste

    file = paste()
    if 'evaluation/' not in file or 1:
        file = r'evaluation/evaluation_outputs/outputs/swe-bench-lite/CodeActAgent/gemini-1.5-flash-latest_maxiter_20_N_v1.9/output.jsonl'

# output.json or trajectory.json
if 1 or sys.argv[1:]:
    with open(file, 'r') as f:
        data = f.readlines()
        ansi_color_escape = re.compile(r'\\u001b\[[0-9;]*m')
        data = [ansi_color_escape.sub('', line) for line in data]
        null_observation = ', {"message": "No observation", "observation": "null", "content": "", "extras": {}}'
        data = [line.replace(null_observation, '') for line in data]
        data = [json.loads(line) for line in data]
        history = []
        for d in data:
            history.extend(d['history'])
            # if d.get('error'):
            #     history.append({'error': d['error']})
        # history = [i for sublist in history for i in sublist]
        # history = history[3:]

else:
    fp = r'evaluation\evaluation_outputs\instance.json'
    with open(fp, 'r') as f:
        data = json.load(f)
        history = data['traj']
    history = [i for sublist in history for i in sublist]

if not sys.argv[1:] and 0:
    pprint(history)
    # exit()
json_data = {}
git_hash = 'git rev-parse HEAD'

git_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()

model = sys.argv[2] if len(sys.argv) > 2 else 'Unknown Model'
agent = 'CodeActAgent'
config = {
    'action': 'initialize',
    'args': {
        'LLM_MODEL': model,
        'AGENT': agent,
        'LANGUAGE': f'EN | Using Kevin Fork on {git_hash[:7]}',
        'CONFIRMATION_MODE': 'false',
        'SECURITY_ANALYZER': '',
    },
}
json_data.update(
    {
        'version': git_hash,
        'feedback': 'negative',
        'email': 'eval@anon.com',
        'permissions': 'public' if os.environ.get('PUBLIC_EVAL_HISTORY') else 'private',
        'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzaWQiOiJiNWIwNjRmYi1mMTFlLTQxMTQtOWYxYy1hOTQ3MmZmYjY1ZGUifQ.MjMpKSWLYI4Cg85Uq8HnjY3MY9iBj8yeNawOwgjX5MU',
    }
)
# flatten the history
history = [config] + history

for idx, item in enumerate(history):
    try:
        if item.get('action') == 'message' and item.get('source') == 'user':
            msg = item.get('message')
            if (
                msg
                == 'Please continue working on the task on whatever approach you think is suitable. You have full access to the repository. Eg: You can run <execute_python> os.listdir() </execute_python> to list the files in the current directory.\nIMPORTANT: YOU SHOULD NEVER ASK FOR HUMAN HELP.\n'
            ):
                msg = 'Auto reply 🤖'
            # history[idx] = {'user': msg}
    except Exception as e:
        print(f'{item}')
        pprint((history))
        raise e

step_count = 0
for idx, item in enumerate(history[:]):
    if item.get('log'):
        item = {'step': item['log'].split()[-1]}
        history[idx] = item
    if item.get('observation') == 'error':
        item = {'error': item['content']}
        history[idx] = item


json_data['trajectory'] = history

# pprint(json_data);exit()
FEEDBACK_URL = 'https://share-od-trajectory-3u9bw9tx.uc.gateway.dev/share_od_trajectory'

response = requests.post(
    FEEDBACK_URL,
    json=json_data,
)


rj = response.json()
try:
    f_id = rj['body']['feedback_id']
    url = f'https://www.all-hands.dev/share?share_id={f_id}'
    print(f'Feedback URL: {url}')

except Exception:
    print(rj)
    exit()

webbrowser.open(url)

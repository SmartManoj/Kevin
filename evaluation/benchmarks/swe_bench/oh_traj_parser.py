import json

from pyperclip import paste

try:
    traj_content = paste()
    traj = json.loads(traj_content)
    if not isinstance(traj, list):
        raise Exception('Invalid trajectory')
    with open('evaluation/benchmarks/swe_bench/oh_traj.json', 'w') as f:
        f.write(traj_content)
except Exception as e:
    print(e)
    with open('evaluation/benchmarks/swe_bench/oh_traj.json', 'r') as f:
        traj = json.load(f)

step_count = 0
for i in traj:
    if i['role'] == 'assistant':
        step_count += 1
        print(f'Step {step_count}:')
    print(i['role'])
    try:
        contents = i['content']
        if contents:
            print(
                contents[0]['text']
                .replace('\r', '')
                .replace(
                    '[Python Interpreter: /opt/miniconda3/envs/testbed/bin/python]', ''
                )
            )
    except Exception as e:
        print(e)
        print(i)

    if i['role'] == 'assistant':
        tool_calls = i.get('tool_calls', [])
        if tool_calls:
            print('=' * 10)

        for tool_call in tool_calls:
            arguments = tool_call['function']['arguments']
            arguments = json.loads(arguments)
            for k, v in arguments.items():
                print(f'{k}: {v}')

    print('-' * 100)

import json

from pyperclip import paste

try:
    traj_content = paste()
    traj = json.loads(traj_content)
    if not isinstance(traj, dict):
        raise Exception('Invalid trajectory')
    with open('evaluation/benchmarks/swe_bench/gru_traj.json', 'w') as f:
        f.write(traj_content)
except Exception as e:
    print(e)
    with open('evaluation/benchmarks/swe_bench/gru_traj.json', 'r') as f:
        traj = json.load(f)
# // script to print chat human friendly
for i in traj['trajectory']['details'][0]['exportedConversation']['plans'][0]:
    for j in i:
        try:
            print(j['thought'])
            print(j['name'], j['args'])
            # print(j['observation'])
            print(' ' * 50)
            print('--' * 50)
            print(' ' * 50)
        except Exception as e:
            print(e)
            print(j)

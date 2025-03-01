import json
from time import sleep

import requests
import os 
sandbox_port = os.environ.get('SANDBOX_PORT', 63710)
def run_ipython(code):
    return {
        'action': {
            'action': 'run_ipython',
            'args': {
                'code': code,
            },
        }
    }


def run(command):
    if command.startswith('!') or command.startswith('%'):
        return run_ipython(command)
    return {
        'action': {
            'action': 'run',
            'args': {
                'command': command,
            },
            'timeout': 1,
        }
    }


def read_file(path):
    return {
        'action': {
            'action': 'read',
            'args': {'path': path},
        }
    }

def write_file(path, content):
    return {
        'action': {
            'action': 'write',
            'args': {'path': path, 'content': content},
        }
    }

def execute_action(data, timeout=5):
    data = json.dumps(data)
    for k in [1, 2]:
        try:
            url = f'http://localhost:{sandbox_port}/execute_action'
            response = requests.post(url, data=data, timeout=timeout)
            rj = response.json()
            print(rj['content'].replace('\r', ''))
            if rj.get('suffix'):
                print(rj['suffix'])
            break
        except requests.exceptions.Timeout:
            if k == 2:
                print('Timeout')
            # sleep(1)
            pass
        except Exception as e:
            print(e)
            print(response.json())
            print(response.status_code)


if __name__ == '__main__':
    execute_action(run_ipython('%pwd'))
    # execute_action(run_ipython('!which python'))
    if 0:
        if 0:
            execute_action(
                run_ipython(
                    'import IPython\nIPython.Application.instance().kernel.do_shutdown(True)'
                )
            )
            sleep(3)
        execute_action(
            run_ipython(
                'from openhands.runtime.plugins.agent_skills.agentskills import *'
            )
        )
    # execute_action(run_ipython('open_file'))
    execute_action(run('pwd'))
    execute_action(write_file('test', 'hello'))
    execute_action(read_file('test'))
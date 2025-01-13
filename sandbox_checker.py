import json
from time import sleep

import requests

sandbox_port = 63710
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


def execute_action(data):
    data = json.dumps(data)
    for timeout in [600,]:
        try:
            response = requests.post(
                f'http://localhost:{sandbox_port}/execute_action', data=data, timeout=timeout
            )
            print(response.json()['content'].replace('\r', ''))
            break
        except requests.exceptions.Timeout:
            if timeout == 2:
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

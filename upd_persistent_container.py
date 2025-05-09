import os
from datetime import datetime

import docker

full_file_names = [
    'openhands/runtime/plugins/agent_skills/agentskills.py',
    'openhands/runtime/plugins/agent_skills/file_ops/file_ops.py',
    'openhands/runtime/plugins/agent_skills/file_ops/cst_ops.py',
    'openhands/runtime/plugins/agent_skills/file_ops/ast_ops.py',
    'openhands/runtime/plugins/agent_skills/file_ops/file_utils.py',
    'openhands/runtime/plugins/agent_skills/file_ops/so.py',
    'openhands/runtime/plugins/jupyter/execute_server.py',
    'openhands/runtime/plugins/jupyter/__init__.py',
    'openhands/runtime/plugins/vscode/__init__.py',
    'openhands/runtime/utils/bash.py',
    'openhands/runtime/utils/bash_pexpect.py',
    'openhands/runtime/action_execution_server.py',
    'openhands/linter/__init__.py',
    'openhands/events/event.py',
    'sandbox.env'
]
client = docker.from_env()
for c in client.containers.list():
    name = c.name
    if not name.startswith('kevin-'):
        continue
    if 'persisted' in name:
        print(name)
        # break
        # copy the file to the container
        container_id = c.id
        for full_file_name in full_file_names:
            try:
                cmd = f'docker cp {full_file_name} {container_id}:/openhands/code/{full_file_name}'
                os.system(cmd)
            except Exception as e:
                print(e)
        # restart the container
        print('Restarting the container')
        c.restart()
        print(datetime.now())
        if 1:
            if 'root' in c.name:
                break

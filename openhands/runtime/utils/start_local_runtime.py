cmd =['C:\\Users\\smart\\AppData\\Local\\pypoetry\\Cache\\virtualenvs\\openhands-ai-dCXCNKa6-py3.12\\Scripts\\python.exe', '-u', '-m', 'openhands.runtime.action_execution_server', '31234', '--working-dir', 'C:\\Users\\smart\\Desktop\\GD\\Kevin\\workspace', '--plugins', 'agent_skills', 'jupyter', 'vscode', '--username', 'openhands', '--user-id', '1000', '--git-user-name', 'openhands', '--git-user-email', 'openhands@all-hands.dev']

import os

code_repo_path = 'C:\\Users\\smart\\Desktop\\GD\\Kevin\\openhands'
os.environ['OPENHANDS_REPO_PATH'] = code_repo_path
os.environ['PYTHONPATH'] = os.pathsep.join([code_repo_path, os.environ.get('PYTHONPATH', '')])
os.environ['LOCAL_RUNTIME_MODE'] = '1'
import subprocess

os.system(' '.join(cmd))

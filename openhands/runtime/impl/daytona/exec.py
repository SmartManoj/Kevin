import os
from daytona_sdk import Daytona, DaytonaConfig
from dotenv import load_dotenv

load_dotenv()

daytona = Daytona(DaytonaConfig(api_key=os.getenv('DAYTONA_ API_KEY')))
sandbox_id = 'd58beaad-49d3-4bf0-ad0b-3d0cd40dcf3e'
sandbox = daytona.get_current_sandbox(sandbox_id)

def exec_command(command):
    while 1:
        command = input('Enter command: ')
        response = sandbox.process.exec(
            command,  timeout=10
        )
        print(response.result)

if __name__ == "__main__":
    exec_command('pwd')


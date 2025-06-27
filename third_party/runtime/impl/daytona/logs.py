import os
from dotenv import load_dotenv
load_dotenv()
daytona_api_key = os.getenv('DAYTONA_API_KEY')
sandbox_id = '5e939b9f-79e2-471d-bf68-47128fc5ff84'
session_id = 'action-execution-server'
exec_command_id = 'd1e013d8-7fdd-4171-9cbc-f2cc97765ebd'
import time
import daytona_sdk
daytona_sdk.DaytonaConfig(api_key=daytona_api_key)

daytona = daytona_sdk.Daytona(daytona_sdk.DaytonaConfig(api_key=daytona_api_key))

sandbox = daytona.get_current_sandbox(sandbox_id)
def check_exec_logs():
    logs = sandbox.process.get_session_command_logs(
    session_id,
    exec_command_id
)
    print(f"Command output: {logs}")

if __name__ == "__main__":
    for i in range(20):
        check_exec_logs()
        print('--------------------------------')
        try:
            print('EC',sandbox.process.get_session(session_id).commands[0].exit_code)
            break
        except Exception as e:
            print(e)
        print(i)
        time.sleep(5)

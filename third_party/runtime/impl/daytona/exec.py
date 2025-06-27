import os
from daytona_sdk import CreateSandboxParams, Daytona, DaytonaConfig
from dotenv import load_dotenv

load_dotenv()

daytona = Daytona(DaytonaConfig(api_key=os.getenv('DAYTONA_API_KEY')))
image = 'docker.all-hands.dev/all-hands-ai/runtime:0.40-nikolaik'
image = 'ghcr.io/smartmanoj/kevin-sandbox:oh_v0.40.0_p3hl9v56jrfymbsz_y49eklt66h256yhr'
if 1:
    sandbox = daytona.create(
        CreateSandboxParams(
            image=image,
            public=True,
            env_vars={
                'DEBUG': 'true',
            },
        )
    )
else:
    sandbox_id = 'd58beaad-49d3-4bf0-ad0b-3d0cd40dcf3e'
    sandbox = daytona.get_current_sandbox(sandbox_id)

def exec_command(command):
    response = sandbox.process.exec(
        command,  timeout=10
    )
    print(response.result)

if __name__ == "__main__":
    exec_command('pwd')


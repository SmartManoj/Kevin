import subprocess
import os

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
import uvicorn

os.chdir(os.path.dirname(os.path.abspath(__file__)))
app = FastAPI(title="Remote Runtime Kubernetes Server")

class Data(BaseModel):
    runtime_id: str

@app.post("/pause")
async def pause_runtime(data: Data):
    print(f"Pausing runtime {data.runtime_id}")
    return {"message": "Runtime paused"}

@app.post("/resume")
async def resume_runtime(data: Data):
    print(f"Resuming runtime {data.runtime_id}")
    return {"message": "Runtime resumed"}

@app.post("/registry_prefix")
async def get_registry_prefix():
    return {"registry_prefix": "ghcr.io/all-hands-ai"}

ip_dict = {}

@app.get("/sessions/{session_id}")
async def get_session(session_id):
    print(f"Getting session {session_id}")
    if session_id == 'None':
        session_id = '0'
    if session_id not in ip_dict:
        # create sandbox
        output = subprocess.run(["python3", "create_sandbox.py", session_id], capture_output=True, text=True).stdout.strip().split("\n")
        print(output)
        ip = output[-1]
        print(session_id, ip)
        ip_dict[session_id] = ip
    else:
        ip = ip_dict[session_id]
    return {
            "status": "running", 
            "runtime_id": session_id, 
            "url": f"http://{ip}",
            "work_hosts": None
        }

@app.get("/runtime/{runtime_id}")
async def get_runtime(runtime_id):
    print(f"Getting runtime {runtime_id}")
    if 1:
        return {"runtime_id": runtime_id, "pod_status": "ready", "restart_count": 0, "restart_reasons": None}
    else:
        return {"runtime_id": runtime_id, "pod_status": "not_found"}

if __name__ == "__main__":
    uvicorn.run('remote_runtime_server:app', host="0.0.0.0", port=12345, reload=0)


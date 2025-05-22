import os
import subprocess
import traceback
import warnings
from contextlib import asynccontextmanager
from fastapi.params import Depends
from openhands.server.user_auth import get_user_id
from pydantic import SecretStr

from fastapi.responses import JSONResponse

from openhands.integrations.provider import PROVIDER_TOKEN_TYPE, ProviderHandler
from openhands.server.user_auth import get_access_token, get_provider_tokens
from typing import AsyncIterator

from fastapi.routing import Mount

with warnings.catch_warnings():
    warnings.simplefilter('ignore')

from fastapi import (
    FastAPI,
    Request,
)

import openhands.agenthub  # noqa F401 (we import this to get the agents registered)
from openhands import __version__
from openhands.server.routes.billing import app as billing_api_router
from openhands.server.routes.config_ui import app as config_ui_router
from openhands.server.routes.conversation import app as conversation_api_router
from openhands.server.routes.feedback import app as feedback_api_router
from openhands.server.routes.files import app as files_api_router
from openhands.server.routes.git import app as git_api_router
from openhands.server.routes.health import add_health_endpoints
from openhands.server.routes.manage_conversations import (
    app as manage_conversation_api_router,
)
from openhands.server.routes.mcp import mcp_server
from openhands.server.routes.public import app as public_api_router
from openhands.server.routes.secrets import app as secrets_router
from openhands.server.routes.security import app as security_api_router
from openhands.server.routes.settings import app as settings_router
from openhands.server.routes.trajectory import app as trajectory_router
from openhands.server.shared import conversation_manager

@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with conversation_manager:
        yield


app = FastAPI(
    title='OpenHands',
    description='OpenHands: Code Less, Make More',
    version=__version__,
    lifespan=_lifespan,
    routes=[Mount(path='/mcp', app=mcp_server.sse_app())],
)


app.include_router(billing_api_router)
app.include_router(public_api_router)
app.include_router(files_api_router)
app.include_router(security_api_router)
app.include_router(feedback_api_router)
app.include_router(conversation_api_router)
app.include_router(manage_conversation_api_router)
app.include_router(settings_router)
app.include_router(secrets_router)
app.include_router(git_api_router)
app.include_router(trajectory_router)


@app.post("/api/authenticate")
@app.get("/api/authenticate")
async def authenticate(request: Request,
                    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
                    access_token: SecretStr | None = Depends(get_access_token),):
    """Authenticate the user"""
    try:
        if request.session.get("github_token"):
            try:
                # check if the token is valid
                client = ProviderHandler(
                    provider_tokens=provider_tokens, external_auth_token=access_token
                )
                await client.get_user()
            except Exception as e:
                traceback.print_exc()
                return JSONResponse(
                    content={"error": str(e)},
                    status_code=401
                )
            request.state.github_token = request.session.get("github_token")
            os.environ[f'GITHUB_TOKEN_{request.session.get("github_user_id")}'] = request.session.get("github_token")
            request.state.github_user_id = request.session.get("github_user_id")
            request.state.user_id = request.session.get("user_id")
            return JSONResponse(
                content={"authenticated": True},
                status_code=200

            )
        else:
            return JSONResponse(
                content={"authenticated": False},
                status_code=401
            )
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@app.post("/api/logout")
@app.get("/api/logout")
async def logout(request: Request):
    """Logout the user"""
    request.session.clear()
    request.state.provider_tokens = None
    request.state.github_token = None
    request.state.github_user_id = None
    request.state.user_id = None

    return JSONResponse(
        content={"message": "Logged out"},
        status_code=200)



@app.get("/set_github_details")
async def set_github_details(request: Request):
    """Set the github details"""
    request.session["github_token"] = 'dummy_for_testing'
    request.session["github_user_id"] = 'dummy_for_testing'
    return JSONResponse(
        content={"message": "GitHub details set"},
        status_code=200
    )


@app.get("/get_github_details")
async def get_github_details(request: Request):
    """Get the github token"""
    if pts := getattr(request.state, 'provider_tokens', None):
        pts = [pt.value for pt in pts]
    else:
        pts = None
    return JSONResponse(
        content={
            "github_token_from_session": request.session.get("github_token"),
            "github_user_id_from_session": request.session.get("github_user_id"),
            "user_id_from_session": request.session.get("user_id"),
            "github_token_from_state": getattr(request.state, 'github_token', None),
            "github_user_id_from_state": getattr(request.state, 'github_user_id', None),
            "user_id_from_state": getattr(request.state, 'user_id', None),
            "provider_tokens_from_state": pts,
            "user_id": await get_user_id(request)
        },
        status_code=200
    )


@app.get("/version")
async def version():
    """Get the version of the app"""
    try:
        short_sha = open('version.txt').read().strip()
    except Exception:
        try:
            short_sha = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('utf-8').strip()
        except Exception:
            short_sha = "unknown"
    return JSONResponse(
        content={"version": __version__, "commit_hash": short_sha},
        status_code=200
    )

if os.environ.get("APP_MODE") != "saas":
    app.include_router(config_ui_router)

add_health_endpoints(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)

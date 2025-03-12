import os
import warnings
from contextlib import asynccontextmanager

from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse

from openhands.integrations.github.github_service import GithubServiceImpl

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
from openhands.server.routes.github import app as github_api_router
from openhands.server.routes.manage_conversations import (
    app as manage_conversation_api_router,
)
from openhands.server.routes.public import app as public_api_router
from openhands.server.routes.security import app as security_api_router
from openhands.server.routes.settings import app as settings_router
from openhands.server.routes.trajectory import app as trajectory_router
from openhands.server.shared import conversation_manager

@asynccontextmanager
async def _lifespan(app: FastAPI):
    async with conversation_manager:
        yield


app = FastAPI(
    title='OpenHands',
    description='OpenHands: Code Less, Make More',
    version=__version__,
    lifespan=_lifespan,
)


@app.get('/health')
async def health():
    return 'OK'


app.include_router(billing_api_router)
app.include_router(public_api_router)
app.include_router(files_api_router)
app.include_router(security_api_router)
app.include_router(feedback_api_router)
app.include_router(conversation_api_router)
app.include_router(manage_conversation_api_router)
app.include_router(settings_router)
app.include_router(github_api_router)
app.include_router(trajectory_router)



@app.post("/api/authenticate")
async def authenticate(request: Request):
    """Authenticate the user"""
    try:
        if request.session.get("github_token"):
            try:
                # check if the token is valid
                client = GithubServiceImpl(user_id=request.session.get("github_user_id"), github_token=request.session.get("github_token"))
                await client.get_user()
            except Exception as e:
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
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@app.post("/api/logout")
async def logout(request: Request):
    """Logout the user"""
    request.session.clear()
    return JSONResponse(
        content={"message": "Logged out"},
        status_code=200)



@app.get("/get_github_details")
async def get_github_details(request: Request):
    """Get the github token"""
    return JSONResponse(
        content={"github_token": request.session.get("github_token"), "github_user_id": request.session.get("github_user_id"), "github_token_from_state": getattr(request.state, 'github_token', None), "github_user_id_from_state": getattr(request.state, 'github_user_id', None)},
        status_code=200
    )


if os.environ.get("APP_MODE") != "saas":
    app.include_router(config_ui_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
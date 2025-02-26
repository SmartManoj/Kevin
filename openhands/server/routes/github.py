import traceback
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
import jwt
from pydantic import SecretStr
from openhands.server.shared import SettingsStoreImpl, config


from openhands.integrations.github.github_service import GithubServiceImpl
from openhands.integrations.github.github_types import (
    GhAuthenticationError,
    GHUnknownException,
    GitHubRepository,
    GitHubUser,
    SuggestedTask,
)
from openhands.server.auth import get_github_token, get_user_id

app = APIRouter(prefix='/api/github')


@app.get('/repositories')
async def get_github_repositories(
    page: int = 1,
    per_page: int = 10,
    sort: str = 'pushed',
    installation_id: int | None = None,
    github_user_id: str | None = Depends(get_user_id),
    github_user_token: SecretStr | None = Depends(get_github_token),
):
    client = GithubServiceImpl(user_id=github_user_id, token=github_user_token)
    try:
        repos: list[GitHubRepository] = await client.get_repositories(
            page, per_page, sort, installation_id
        )
        return repos

    except GhAuthenticationError as e:
        return JSONResponse(
            content=str(e),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    except GHUnknownException as e:
        return JSONResponse(
            content=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@app.get('/user')
async def get_github_user(
    github_user_id: str | None = Depends(get_user_id),
    github_user_token: SecretStr | None = Depends(get_github_token),
):
    client = GithubServiceImpl(user_id=github_user_id, token=github_user_token)
    try:
        user: GitHubUser = await client.get_user()
        return user

    except GhAuthenticationError as e:
        return JSONResponse(
            content=str(e),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    except GHUnknownException as e:
        return JSONResponse(
            content=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@app.get('/installations')
async def get_github_installation_ids(
    github_user_id: str | None = Depends(get_user_id),
    github_user_token: SecretStr | None = Depends(get_github_token),
):
    client = GithubServiceImpl(user_id=github_user_id, token=github_user_token)
    try:
        installations_ids: list[int] = await client.get_installation_ids()
        return installations_ids

    except GhAuthenticationError as e:
        return JSONResponse(
            content=str(e),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    except GHUnknownException as e:
        return JSONResponse(
            content=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@app.get('/search/repositories')
async def search_github_repositories(
    query: str,
    per_page: int = 5,
    sort: str = 'stars',
    order: str = 'desc',
    github_user_id: str | None = Depends(get_user_id),
    github_user_token: SecretStr | None = Depends(get_github_token),
):
    client = GithubServiceImpl(user_id=github_user_id, token=github_user_token)
    try:
        repos: list[GitHubRepository] = await client.search_repositories(
            query, per_page, sort, order
        )
        return repos

    except GhAuthenticationError as e:
        return JSONResponse(
            content=str(e),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    except GHUnknownException as e:
        return JSONResponse(
            content=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@app.get('/callback')
async def github_callback(
    request: Request,
):
    try:
        code = request.query_params.get('code')
        if not code:
            return JSONResponse(
                content="Missing 'code' in request body",
                status_code=422,
            )
            
        client = GithubServiceImpl(None)
        response = await client.handle_github_callback(code)
        print(response)
        access_token = response['access_token']
        request.session['github_token'] = access_token
        request.state.github_token = access_token
        client.token = SecretStr(access_token)
        user = await client.get_user()
        user.id = str(user.id)
        request.session['github_user_id'] = user.id
        request.state.github_user_id = user.id
        print(f"github_user_id: {request.state.github_user_id}")
        # save settings
        settings_store = await SettingsStoreImpl.get_instance(config, user.id)
        settings = await settings_store.load()
        settings.github_token = SecretStr(access_token)
        await settings_store.store(settings)
        # set the cookie of github_user_id encoded in jwt
        jwt_secret = (
            config.jwt_secret.get_secret_value()
            if isinstance(config.jwt_secret, SecretStr)
            else config.jwt_secret
        )
        encoded = jwt.encode({'github_user_id': user.id}, jwt_secret, algorithm='HS256')

        response = RedirectResponse(url='/')
        response.set_cookie(key="openhands_auth", value=encoded)
        return response
    except Exception as e:
        traceback.print_exc()

@app.get('/suggested-tasks')
async def get_suggested_tasks(
    github_user_id: str | None = Depends(get_user_id),
    github_user_token: SecretStr | None = Depends(get_github_token),
):
    """
    Get suggested tasks for the authenticated user across their most recently pushed repositories.
    Returns:
    - PRs owned by the user
    - Issues assigned to the user
    """
    client = GithubServiceImpl(user_id=github_user_id, token=github_user_token)
    try:
        tasks: list[SuggestedTask] = await client.get_suggested_tasks()
        return tasks

    except GhAuthenticationError as e:
        return JSONResponse(
            content=str(e),
            status_code=401,
        )

    except GHUnknownException as e:
        return JSONResponse(
            content=str(e),
            status_code=500,
        )

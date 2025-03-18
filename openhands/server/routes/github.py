import traceback
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
import jwt
from pydantic import SecretStr
from openhands.server.shared import SettingsStoreImpl, config


from openhands.integrations.github.github_service import GithubServiceImpl
from openhands.integrations.provider import (
    PROVIDER_TOKEN_TYPE,
    ProviderHandler,
    ProviderType,
)
from openhands.integrations.service_types import (
    AuthenticationError,
    Repository,
    SuggestedTask,
    UnknownException,
    User,
)
from openhands.server.auth import get_access_token, get_provider_tokens

app = APIRouter(prefix='/api/github')


@app.get('/repositories', response_model=list[Repository])
async def get_github_repositories(
    page: int = 1,
    per_page: int = 10,
    sort: str = 'pushed',
    installation_id: int | None = None,
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    access_token: SecretStr | None = Depends(get_access_token),
):
    if provider_tokens and ProviderType.GITHUB in provider_tokens:
        token = provider_tokens[ProviderType.GITHUB]
        client = GithubServiceImpl(
            user_id=token.user_id, external_auth_token=access_token, token=token.token
        )

        try:
            repos: list[Repository] = await client.get_repositories(
                page, per_page, sort, installation_id
            )
            return repos

        except AuthenticationError as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        except UnknownException as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return JSONResponse(
        content='GitHub token required.',
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@app.get('/user', response_model=User)
async def get_github_user(
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    access_token: SecretStr | None = Depends(get_access_token),
):
    if provider_tokens:
        client = ProviderHandler(
            provider_tokens=provider_tokens, external_auth_token=access_token
        )

        try:
            user: User = await client.get_user()
            return user

        except AuthenticationError as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        except UnknownException as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return JSONResponse(
        content='GitHub token required.',
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@app.get('/installations', response_model=list[int])
async def get_github_installation_ids(
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    access_token: SecretStr | None = Depends(get_access_token),
):
    if provider_tokens and ProviderType.GITHUB in provider_tokens:
        token = provider_tokens[ProviderType.GITHUB]

        client = GithubServiceImpl(
            user_id=token.user_id, external_auth_token=access_token, token=token.token
        )
        try:
            installations_ids: list[int] = await client.get_installation_ids()
            return installations_ids

        except AuthenticationError as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        except UnknownException as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return JSONResponse(
        content='GitHub token required.',
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@app.get('/search/repositories', response_model=list[Repository])
async def search_github_repositories(
    query: str,
    per_page: int = 5,
    sort: str = 'stars',
    order: str = 'desc',
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    access_token: SecretStr | None = Depends(get_access_token),
):
    if provider_tokens and ProviderType.GITHUB in provider_tokens:
        token = provider_tokens[ProviderType.GITHUB]

        client = GithubServiceImpl(
            user_id=token.user_id, external_auth_token=access_token, token=token.token
        )
        try:
            repos: list[Repository] = await client.search_repositories(
                query, per_page, sort, order
            )
            return repos

        except AuthenticationError as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        except UnknownException as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return JSONResponse(
        content='GitHub token required.',
        status_code=status.HTTP_401_UNAUTHORIZED,
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
        access_token = response['access_token']
        request.session['github_token'] = access_token
        request.state.github_token = access_token
        client.github_token = SecretStr(access_token)
        user = await client.get_user()
        user.id = str(user.id)
        request.session['github_user_id'] = user.id
        request.state.github_user_id = user.id
        request.session['user_id'] = user.id
        request.state.user_id = user.id
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

@app.get('/suggested-tasks', response_model=list[SuggestedTask])
async def get_suggested_tasks(
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    access_token: SecretStr | None = Depends(get_access_token),
):
    """Get suggested tasks for the authenticated user across their most recently pushed repositories.

    Returns:
    - PRs owned by the user
    - Issues assigned to the user.
    """

    if provider_tokens and ProviderType.GITHUB in provider_tokens:
        token = provider_tokens[ProviderType.GITHUB]

        client = GithubServiceImpl(
            user_id=token.user_id, external_auth_token=access_token, token=token.token
        )
        try:
            tasks: list[SuggestedTask] = await client.get_suggested_tasks()
            return tasks

        except AuthenticationError as e:
            return JSONResponse(
                content=str(e),
                status_code=401,
            )

        except UnknownException as e:
            return JSONResponse(
                content=str(e),
                status_code=500,
            )

    return JSONResponse(
        content='GitHub token required.',
        status_code=status.HTTP_401_UNAUTHORIZED,
    )

import traceback
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
import jwt
from pydantic import SecretStr
from openhands.server.shared import SecretsStoreImpl, SettingsStoreImpl, config


from openhands.server.shared import server_config
from openhands.integrations.github.github_service import GithubServiceImpl
from openhands.core.logger import openhands_logger as logger
from openhands.integrations.provider import (
    PROVIDER_TOKEN_TYPE,
    ProviderHandler,
    ProviderType,
    ProviderToken,
)
from openhands.integrations.service_types import (
    AuthenticationError,
    Branch,
    Repository,
    SuggestedTask,
    UnknownException,
    User,
)
from openhands.server.shared import server_config
from openhands.server.user_auth import (
    get_access_token,
    get_provider_tokens,
    get_user_id,
)

app = APIRouter(prefix='/api/user')

@app.get('/repositories', response_model=list[Repository])
async def get_user_repositories(
    sort: str = 'pushed',
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    access_token: SecretStr | None = Depends(get_access_token),
    user_id: str | None = Depends(get_user_id),
) -> list[Repository] | JSONResponse:
    if provider_tokens:
        client = ProviderHandler(
            provider_tokens=provider_tokens,
            external_auth_token=access_token,
            external_auth_id=user_id,
        )

        try:
            return await client.get_repositories(sort, server_config.app_mode)

        except AuthenticationError as e:
            logger.info(
                f'Returning 401 Unauthorized - Authentication error for user_id: {user_id}, error: {str(e)}'
            )
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        except UnknownException as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    logger.info(
        f'Returning 401 Unauthorized - Git provider token required for user_id: {user_id}'
    )
    return JSONResponse(
        content='Git provider token required. (such as GitHub).',
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@app.get('/info', response_model=User)
async def get_user(
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    access_token: SecretStr | None = Depends(get_access_token),
    user_id: str | None = Depends(get_user_id),
) -> User | JSONResponse:
    if provider_tokens:
        client = ProviderHandler(
            provider_tokens=provider_tokens, external_auth_token=access_token
        )

        try:
            user: User = await client.get_user()
            return user

        except AuthenticationError as e:
            logger.info(
                f'Returning 401 Unauthorized - Authentication error for user_id: {user_id}, error: {str(e)}'
            )
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        except UnknownException as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    logger.info(
        f'Returning 401 Unauthorized - Git provider token required for user_id: {user_id}'
    )
    return JSONResponse(
        content='Git provider token required. (such as GitHub).',
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@app.get('/search/repositories', response_model=list[Repository])
async def search_repositories(
    query: str,
    per_page: int = 5,
    sort: str = 'stars',
    order: str = 'desc',
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    access_token: SecretStr | None = Depends(get_access_token),
    user_id: str | None = Depends(get_user_id),
) -> list[Repository] | JSONResponse:
    if provider_tokens:
        client = ProviderHandler(
            provider_tokens=provider_tokens, external_auth_token=access_token
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

    logger.info(
        f'Returning 401 Unauthorized - GitHub token required for user_id: {user_id}'
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
        access_token = response.get('access_token', 'dummy_for_testing')
        request.session['github_token'] = access_token
        request.state.github_token = access_token
        client.token = SecretStr(access_token)
        user = await client.get_user()
        user.id = str(user.id)
        request.session['github_user_id'] = user.id
        request.state.github_user_id = user.id
        request.session['user_id'] = user.id
        request.state.user_id = user.id
        # save settings
        secrets_store = await SecretsStoreImpl.get_instance(config, user.id)
        secrets = await secrets_store.load()
        # Create a new SecretStore with the GitHub token
        provider_token = ProviderToken(token=SecretStr(access_token), user_id=user.id)
        
        # Update the settings with the new secrets_store
        secrets = secrets.model_copy(update={'provider_tokens': {ProviderType.GITHUB: provider_token}})
        await secrets_store.store(secrets)
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
    user_id: str | None = Depends(get_user_id),
) -> list[SuggestedTask] | JSONResponse:
    """Get suggested tasks for the authenticated user across their most recently pushed repositories.

    Returns:
    - PRs owned by the user
    - Issues assigned to the user.
    """
    if provider_tokens:
        client = ProviderHandler(
            provider_tokens=provider_tokens, external_auth_token=access_token
        )
        try:
            tasks: list[SuggestedTask] = await client.get_suggested_tasks()
            return tasks

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
    logger.info(f'Returning 401 Unauthorized - No providers set for user_id: {user_id}')

    return JSONResponse(
        content='No providers set.',
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@app.get('/repository/branches', response_model=list[Branch])
async def get_repository_branches(
    repository: str,
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    access_token: SecretStr | None = Depends(get_access_token),
    user_id: str | None = Depends(get_user_id),
) -> list[Branch] | JSONResponse:
    """Get branches for a repository.

    Args:
        repository: The repository name in the format 'owner/repo'

    Returns:
        A list of branches for the repository
    """
    if provider_tokens:
        client = ProviderHandler(
            provider_tokens=provider_tokens, external_auth_token=access_token
        )
        try:
            branches: list[Branch] = await client.get_branches(repository)
            return branches

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

    logger.info(
        f'Returning 401 Unauthorized - Git provider token required for user_id: {user_id}'
    )

    return JSONResponse(
        content='Git provider token required. (such as GitHub).',
        status_code=status.HTTP_401_UNAUTHORIZED,
    )

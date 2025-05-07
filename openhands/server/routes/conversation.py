from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, JSONResponse

from openhands.core.logger import openhands_logger as logger
from openhands.runtime.base import Runtime

app = APIRouter(prefix='/api/conversations/{conversation_id}')


@app.get('/config')
async def get_remote_runtime_config(request: Request) -> JSONResponse:
    """Retrieve the runtime configuration.

    Currently, this is the session ID and runtime ID (if available).
    """
    runtime = request.state.conversation.runtime
    runtime_id = runtime.runtime_id if hasattr(runtime, 'runtime_id') else None
    session_id = runtime.sid if hasattr(runtime, 'sid') else None
    return JSONResponse(
        content={
            'runtime_id': runtime_id,
            'session_id': session_id,
        }
    )


@app.get('/vscode-url')
async def get_vscode_url(request: Request) -> JSONResponse:
    """Get the VSCode URL.

    This endpoint allows getting the VSCode URL.

    Args:
        request (Request): The incoming FastAPI request object.

    Returns:
        JSONResponse: A JSON response indicating the success of the operation.
    """
    try:
        runtime: Runtime = request.state.conversation.runtime
        logger.debug(f'Runtime type: {type(runtime)}')
        logger.debug(f'Runtime VSCode URL: {runtime.vscode_url}')
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={'vscode_url': runtime.vscode_url}
        )
    except Exception as e:
        logger.error(f'Error getting VSCode URL: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                'vscode_url': None,
                'error': f'Error getting VSCode URL: {e}',
            },
        )


@app.get('/web-hosts')
async def get_hosts(request: Request) -> JSONResponse:
    """Get the hosts used by the runtime.

    This endpoint allows getting the hosts used by the runtime.

    Args:
        request (Request): The incoming FastAPI request object.

    Returns:
        JSONResponse: A JSON response indicating the success of the operation.
    """
    try:
        if not hasattr(request.state, 'conversation'):
            return JSONResponse(
                status_code=500,
                content={'error': 'No conversation found in request state'},
            )

        if not hasattr(request.state.conversation, 'runtime'):
            return JSONResponse(
                status_code=500, content={'error': 'No runtime found in conversation'}
            )

        runtime: Runtime = request.state.conversation.runtime
        logger.debug(f'Runtime type: {type(runtime)}')
        logger.debug(f'Runtime hosts: {runtime.web_hosts}')
        return JSONResponse(status_code=200, content={'hosts': runtime.web_hosts})
    except Exception as e:
        logger.error(f'Error getting runtime hosts: {e}')
        return JSONResponse(
            status_code=500,
            content={
                'hosts': None,
                'error': f'Error getting runtime hosts: {e}',
            },
        )


@app.get('/logs')
async def get_container_logs(request: Request):
    """Get the container logs from the runtime.

    This endpoint allows fetching the logs from the sandbox container.

    Args:
        request (Request): The incoming FastAPI request object.

    Returns:
        JSONResponse: A JSON response containing the container logs or error details.
    """
    try:
        if not hasattr(request.state, 'conversation'):
            return JSONResponse(
                status_code=500,
                content={'error': 'No conversation found in request state'},
            )

        if not hasattr(request.state.conversation, 'runtime'):
            return JSONResponse(
                status_code=500, content={'error': 'No runtime found in conversation'}
            )

        runtime: Runtime = request.state.conversation.runtime
        logger.debug(f'Fetching logs for runtime: {type(runtime)}')
        container_logs = runtime.get_logs() if hasattr(runtime, 'get_logs') else None
        
        if container_logs is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={'error': 'Logs not available for this runtime'},
            )
            
        return HTMLResponse('<body style="background-color: black; color: white;"><pre>' + container_logs.decode() + '</pre></body>')
    except Exception as e:
        logger.error(f'Error fetching container logs: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                'logs': None,
                'error': f'Error fetching container logs: {e}',
            },
        )


@app.get('/restart')
async def restart_runtime(request: Request):
    """Restart the runtime.

    This endpoint allows restarting the runtime.
    """
    try:
        if not hasattr(request.state, 'conversation'):
            return JSONResponse(
                status_code=500,
                content={'error': 'No conversation found in request state'},
            )

        runtime: Runtime = request.state.conversation.runtime
        logger.debug(f'Restarting runtime: {type(runtime)}')
        runtime.restart()
        return JSONResponse(status_code=200, content={'message': 'Runtime restarted'})
    except Exception as e:
        logger.error(f'Error restarting runtime: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                'message': None,
                'error': f'Error restarting runtime: {e}',
            },
        )

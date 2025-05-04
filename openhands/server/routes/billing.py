from fastapi import APIRouter, Request
from openhands.db import get_credits
from openhands.server.user_auth import get_user_id


app = APIRouter(prefix='/api/billing')


@app.get('/credits')
async def get_credits_route(request: Request):
    user_id = await get_user_id(request)
    print('getting credits for', user_id)
    return {"credits": get_credits(user_id)}

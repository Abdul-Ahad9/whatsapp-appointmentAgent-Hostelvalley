from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from app.database import  AsyncSession, hostel_vellay_get_session
from sqlalchemy import select
from app.services.hostel.search_hostels import get_nearby_hostels, search_hostels_with_nominatim
from .webhook import verify_webhook, receive_webhook
from fastapi import Request, Response
router = APIRouter()


@router.get("/verify_webhook")
async def verify_webhook_route(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    return await verify_webhook(hub_mode, hub_challenge, hub_verify_token)

@router.post("/verify_webhook")
async def receive_webhook_route(request: Request):
    print('received a webhook')
    return await receive_webhook(request)


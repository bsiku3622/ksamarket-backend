from datetime import datetime, timedelta, timezone
from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
    HTTPException,
    BackgroundTasks,
)
from db.connection import get_db
from sqlalchemy.orm import Session as SQLSession

from db.models import *
from utils.chatting import ChatInstance
from utils.jwt import get_current_user


router = APIRouter()


@router.post("/market")
def create_market_item(
    data: MarketItemCreate,
    request: Request,
    db: SQLSession = Depends(get_db),
):
    try:
        user = get_current_user(request, db)
        new_item = Item(
            type=ItemType.MARKET,
            name=data.name,
            pricing=data.pricing,
            description=data.description,
            seller_id=user.id,
        )
        db.add(new_item)
        db.commit()
        return Response(status_code=201)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lost")
def create_lost_item(
    data: LostItemCreate,
    request: Request,
    db: SQLSession = Depends(get_db),
):
    try:
        user = get_current_user(request, db)
        new_item = Item(
            type=ItemType.LOST,
            name=data.name,
            location=data.location,
            description=data.description,
            seller_id=user.id,
        )
        db.add(new_item)
        db.commit()
        return Response(status_code=201)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{item_id}")
def get_market_items(
    item_id: int,
    db: SQLSession = Depends(get_db),
):
    try:
        item = (
            db.query(Item)
            .filter(
                Item.status != ItemStatus.DELETED,
                Item.id == item_id,
            )
            .first()
        )
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{item_id}/chat")
def get_market_item_chatroom(
    item_id: int,
    request: Request,
    db: SQLSession = Depends(get_db),
):
    try:
        user = get_current_user(request, db)
        item = (
            db.query(Item)
            .filter(
                Item.status != ItemStatus.DELETED,
                Item.id == item_id,
            )
            .first()
        )
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        if item.seller_id == user.id:  # type: ignore
            raise HTTPException(
                status_code=403, detail="Sellers cannot access their own chatrooms"
            )

        chatroom = Chatroom(
            type=item.type,
            item_id=item.id,
            seller_id=item.seller_id,  # type: ignore
            customer_id=user.id,
        )
        db.add(chatroom)
        db.commit()
        ChatInstance(str(chatroom.id))
        return Response(status_code=201)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

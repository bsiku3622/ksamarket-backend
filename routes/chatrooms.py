import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sse_starlette.sse import EventSourceResponse

from db.connection import get_db
from utils.chatting import ChatInstance, queue, DB_PATH
from utils.jwt import get_current_user
from fastapi import Request
from sqlalchemy.orm import Session as SQLSession
from db.models import *
import time

router = APIRouter()


class WriteRequest(BaseModel):
    message: str


@router.get("/chatrooms")
def list_chatrooms(request: Request, db: SQLSession = Depends(get_db)):
    user = get_current_user(request, db)
    databases = (
        db.query(Chatroom)
        .filter(or_(Chatroom.customer_id == user.id, Chatroom.seller_id == user.id))
        .all()
    )
    return {"chatrooms": [i.id for i in databases]}


@router.post("/chatrooms/{room_id}/chatting")
def write_chat(
    room_id: str, body: WriteRequest, request: Request, db: SQLSession = Depends(get_db)
):
    user = get_current_user(request, db)

    if not (
        db.query(Chatroom)
        .filter(
            or_(Chatroom.customer_id == user.id, Chatroom.seller_id == user.id),
            Chatroom.id == room_id,
        )
        .first()
    ):
        raise HTTPException(status_code=404, detail="Chatroom not found.")
    chatid = str(time.time_ns() // 1000)
    for chat_instance in queue:
        if chat_instance.room_id == room_id:
            chat_instance.write(chatid, str(user.id) + "\n" + body.message)
            return {"message": f"Data written to chat {room_id} with ID {chatid}."}
    try:
        chat_instance = ChatInstance(room_id, allow_create=False)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chat instance not found.")
    queue.append(chat_instance)
    chat_instance.write(chatid, str(user.id) + "\n" + body.message)
    return f"Data written to chat {room_id} with ID {chatid}."


@router.get("/chatrooms/{room_id}/chatting")
def read_chat_all(room_id: str, request: Request, db: SQLSession = Depends(get_db)):
    user = get_current_user(request, db)

    if not (
        db.query(Chatroom)
        .filter(
            or_(Chatroom.customer_id == user.id, Chatroom.seller_id == user.id),
            Chatroom.id == room_id,
        )
        .first()
    ):
        raise HTTPException(status_code=404, detail="Chatroom not found.")
    for chat_instance in queue:
        if chat_instance.room_id == room_id:
            try:
                data = chat_instance.findFrom(chat_instance.first_id)  # type: ignore
                return {"data": data, "last_id": chat_instance.last_id}
            except IndexError:
                raise HTTPException(status_code=404, detail="ID not found.")
    try:
        chat_instance = ChatInstance(room_id, allow_create=False)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chat instance not found.")
    queue.append(chat_instance)
    try:
        data = chat_instance.findFrom(chat_instance.first_id)  # type: ignore
        return {"data": data, "last_id": chat_instance.last_id}
    except IndexError:
        raise HTTPException(status_code=404, detail="ID not found.")


@router.get("/chatrooms/{room_id}/chatting/start_from/{id}")
def read_chat(
    room_id: str, id: str, request: Request, db: SQLSession = Depends(get_db)
):
    user = get_current_user(request, db)
    if not (
        db.query(Chatroom)
        .filter(
            or_(Chatroom.customer_id == user.id, Chatroom.seller_id == user.id),
            Chatroom.id == room_id,
        )
        .first()
    ):
        raise HTTPException(status_code=404, detail="Chatroom not found.")
    for chat_instance in queue:
        if chat_instance.room_id == room_id:
            try:
                data = chat_instance.findFrom(id)
                return {"data": data}
            except IndexError:
                raise HTTPException(status_code=404, detail="ID not found.")
    try:
        chat_instance = ChatInstance(room_id, allow_create=False)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chat instance not found.")
    queue.append(chat_instance)
    try:
        data = chat_instance.findFrom(id)
        return {"data": data}
    except IndexError:
        raise HTTPException(status_code=404, detail="ID not found.")


def message(text: list[str], last_id: str):
    return {"event": "message", "data": text, "last_id": last_id}


@router.get("/chatrooms/{room_id}/subscribe")
async def stream(
    request: Request, room_id: str, id_: str = "", db: SQLSession = Depends(get_db)
):
    user = get_current_user(request, db)
    if not (
        db.query(Chatroom)
        .filter(
            or_(Chatroom.customer_id == user.id, Chatroom.seller_id == user.id),
            Chatroom.id == room_id,
        )
        .first()
    ):
        raise HTTPException(status_code=404, detail="Chatroom not found.")
    chat_instance = None
    for ci in queue:
        if ci.room_id == room_id:
            chat_instance = ci
            break
    if chat_instance is None:
        try:
            chat_instance = ChatInstance(room_id, allow_create=False)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Chat instance not found.")
        queue.append(chat_instance)

    async def event_generator(id_):
        last_modified = chat_instance.last_modified
        find_from = id_ if id_ != "" else chat_instance.first_id
        id_ = chat_instance.last_id
        yield message(chat_instance.findFrom(find_from), id_)  # type: ignore

        while True:
            await asyncio.sleep(1)
            if chat_instance.last_modified != last_modified:
                last_modified = chat_instance.last_modified
                data = chat_instance.findFrom(id_)[1:]
                id_ = chat_instance.last_id
                yield message(data, id_)  # type: ignore

    return EventSourceResponse(event_generator(id_))

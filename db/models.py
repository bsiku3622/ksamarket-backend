from datetime import datetime
from enum import Enum as PyEnum
import re
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Enum,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from db.connection import Base
import python_multipart


class UserStatus(PyEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"


class ItemStatus(PyEnum):
    PUBLISHED = "PUBLISHED"
    DELETED = "DELETED"
    SOLD = "SOLD"


class ItemType(PyEnum):
    MARKET = "MARKET"
    LOST = "LOST"


class ChatroomStatus(PyEnum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="users_pk"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)
    password = Column(String(255), nullable=True)
    username = Column(String(100), nullable=False)
    avatar_url = Column(String(255), nullable=True)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    items = relationship("Item", back_populates="seller")
    chatrooms_as_seller = relationship(
        "Chatroom", foreign_keys="Chatroom.seller_id", back_populates="seller"
    )
    chatrooms_as_customer = relationship(
        "Chatroom", foreign_keys="Chatroom.customer_id", back_populates="customer"
    )
    favorites = relationship("ItemFavorite", back_populates="user")


class Item(Base):
    __tablename__ = "item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Enum(ItemType), nullable=False)
    name = Column(String(255), nullable=False)
    pricing = Column(Integer, nullable=True)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(ItemStatus), nullable=False, default=ItemStatus.PUBLISHED)
    image_url = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    seller = relationship("User", back_populates="items")
    chatrooms = relationship("Chatroom", back_populates="item")
    favorites = relationship("ItemFavorite", back_populates="item")


class Chatroom(Base):
    __tablename__ = "chatroom"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Enum(ItemType), nullable=False)
    item_id = Column(Integer, ForeignKey("item.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(ChatroomStatus), nullable=False, default=ChatroomStatus.ACTIVE)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    item = relationship("Item", back_populates="chatrooms")
    seller = relationship(
        "User",
        foreign_keys=[seller_id],  # Pass the column object here
        back_populates="chatrooms_as_seller",
    )
    customer = relationship(
        "User",
        foreign_keys=[customer_id],  # Pass the column object here
        back_populates="chatrooms_as_customer",
    )


class ItemFavorite(Base):
    __tablename__ = "item_favorate"

    item_id = Column(Integer, ForeignKey("item.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)

    # Relationships
    item = relationship("Item", back_populates="favorites")
    user = relationship("User", back_populates="favorites")


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserPatch(BaseModel):
    username: str | None
    password: str | None


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    status: UserStatus
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
    }


class VerificationEmailCreate(BaseModel):
    email: EmailStr


class TokenCreate(BaseModel):
    email: str
    password: str


class MarketItemCreate(BaseModel):
    name: str
    pricing: int
    description: str | None


class LostItemCreate(BaseModel):
    name: str
    location: str
    description: str | None

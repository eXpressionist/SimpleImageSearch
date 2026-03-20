from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Column, String, Integer, Text, Boolean, DateTime, 
    ForeignKey, Enum as SQLEnum, BigInteger, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship, DeclarativeBase
import enum

from src.domain.value_objects import BatchStatus, ItemStatus


class Base(DeclarativeBase):
    pass


class BatchModel(Base):
    __tablename__ = "batches"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    total_items = Column(Integer, nullable=False, default=0)
    processed_items = Column(Integer, nullable=False, default=0)
    failed_items = Column(Integer, nullable=False, default=0)
    status = Column(
        SQLEnum(BatchStatus),
        nullable=False,
        default=BatchStatus.PENDING
    )
    config = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    items = relationship("BatchItemModel", back_populates="batch", cascade="all, delete-orphan")


class BatchItemModel(Base):
    __tablename__ = "batch_items"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    batch_id = Column(PGUUID(as_uuid=True), ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False)
    original_query = Column(Text, nullable=False)
    normalized_query = Column(String(500), nullable=False)
    status = Column(
        SQLEnum(ItemStatus),
        nullable=False,
        default=ItemStatus.PENDING
    )
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    is_approved = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    batch = relationship("BatchModel", back_populates="items")
    image = relationship("ImageAssetModel", back_populates="item", uselist=False, cascade="all, delete-orphan")
    logs = relationship("ProcessingLogModel", back_populates="item", cascade="all, delete-orphan")


class ImageAssetModel(Base):
    __tablename__ = "image_assets"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    item_id = Column(PGUUID(as_uuid=True), ForeignKey("batch_items.id", ondelete="CASCADE"), nullable=False, unique=True)
    source_url = Column(Text, nullable=False)
    direct_url = Column(Text, nullable=False)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_hash = Column(String(64), nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    item = relationship("BatchItemModel", back_populates="image")


class ProcessingLogModel(Base):
    __tablename__ = "processing_logs"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    item_id = Column(PGUUID(as_uuid=True), ForeignKey("batch_items.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    item = relationship("BatchItemModel", back_populates="logs")

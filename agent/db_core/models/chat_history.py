import uuid
from sqlalchemy import Column, Text, String, TIMESTAMP, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from agent.db_core.core import Base

class ChatHistory(Base):
    __tablename__ = 'chat_history'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), server_default='NOW()')
    history_metadata = Column(JSONB, server_default="{}")
    attachments = Column(ARRAY(Text), server_default="{}")
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey('chat_history.id'), nullable=True)
    token_count = Column(Integer, default=0)
    processing_time_ms = Column(Integer, default=0)

    session = relationship("ChatSession", back_populates="messages")
    parent = relationship("ChatHistory", remote_side=[id], backref="replies")

import uuid
from sqlalchemy import Column, Text, String, Integer, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from agent.db_core.core import Base

class ChatSummary(Base):
    __tablename__ = 'chat_summaries'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False)
    summary = Column(Text, nullable=False)
    keywords = Column(ARRAY(Text), server_default="{}")
    sentiment = Column(String(20), server_default="'neutral'")
    message_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default='NOW()')
    updated_at = Column(TIMESTAMP(timezone=True), server_default='NOW()')

    session = relationship("ChatSession", back_populates="summaries")

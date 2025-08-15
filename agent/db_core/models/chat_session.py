import uuid
from sqlalchemy import Column, String, Boolean, TIMESTAMP, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from agent.db_core.core import Base
from sqlalchemy.sql import func

class ChatSession(Base):
    __tablename__ = 'chat_sessions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id  = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    title = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(),
    nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(),
    nullable=False)
    is_active = Column(Boolean, server_default='TRUE')
    session_metadata = Column(JSONB, server_default="{}")

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    agent = relationship("Agent", back_populates="chat_sessions")
    messages = relationship("ChatHistory", back_populates="session", cascade="all, delete-orphan")
    summaries = relationship("ChatSummary", back_populates="session", cascade="all, delete-orphan")

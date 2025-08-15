import uuid
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from db_core.core import Base

class ChatAnalytics(Base):
    __tablename__ = 'chat_analytics'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(String(50), nullable=False)
    event_data = Column(JSONB, server_default="{}")
    timestamp = Column(TIMESTAMP(timezone=True), server_default='NOW()')

    # Relationships omitted for brevity

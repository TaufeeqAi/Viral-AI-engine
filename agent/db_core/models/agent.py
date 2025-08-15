from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from ..core import Base
from .tool import Tool, agent_tool_association # Assuming tool.py defines Tool and agent_tool_association

class Agent(Base):
    """SQLAlchemy model for an Agent."""
    __tablename__ = "agents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # user_id should reference the 'users' table's primary key, which is likely UUID
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    model_provider = Column(String, nullable=False)
    
    settings = Column(JSON, nullable=False)
    system = Column(String)
    bio = Column(JSON)
    lore = Column(JSON)
    knowledge = Column(JSON)
    message_examples = Column(JSON)
    style = Column(JSON)

    # Add the missing columns for agent usage statistics
    last_used = Column(DateTime(timezone=True), server_default=func.now())
    total_sessions = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    avatar_url = Column(String, nullable=True)
    
    tools = relationship(
        "Tool",
        secondary=agent_tool_association,
        back_populates="agents"
    )

    chat_sessions = relationship(
        "ChatSession",
        back_populates="agent",
        cascade="all, delete-orphan",
    )

    # Optional: Add a __repr__ for easier debugging
    def __repr__(self):
        return f"<Agent(id={self.id}, name='{self.name}', user_id='{self.user_id}')>"


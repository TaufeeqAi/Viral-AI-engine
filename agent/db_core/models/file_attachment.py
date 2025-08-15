import uuid
from sqlalchemy import Column, String, BigInteger, Text, TIMESTAMP,ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from agent.db_core.core import Base

class FileAttachment(Base):
    __tablename__ = 'file_attachments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    message_id = Column(UUID(as_uuid=True), ForeignKey('chat_history.id', ondelete='CASCADE'))
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_path = Column(Text, nullable=False)
    upload_status = Column(String(20), server_default="'uploaded'")
    processed_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default='NOW()')
    attachments_metadata = Column(JSONB, server_default="{}")

    # Relationships omitted for brevity

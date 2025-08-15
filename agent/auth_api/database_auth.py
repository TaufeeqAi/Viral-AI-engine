# import os
# from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.sql import func
# from dotenv import load_dotenv

# load_dotenv()

# # Database URL - use environment variable
# DATABASE_URL = "postgresql://cyrene:taufeeq@127.0.0.1:5433/cyrene_auth"

# # Create engine
# engine = create_engine(DATABASE_URL)

# # Create session
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# # Base class for models
# Base = declarative_base()

# # User model
# class User(Base):
#     __tablename__ = "users"
    
#     id = Column(Integer, primary_key=True, index=True)
#     username = Column(String, unique=True, index=True, nullable=False)
#     email = Column(String, unique=True, index=True, nullable=False)
#     hashed_password = Column(String, nullable=False)
#     full_name = Column(String)
#     is_active = Column(Boolean, default=True)
#     is_verified = Column(Boolean, default=False)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# # Create tables
# def create_tables():
#     Base.metadata.create_all(bind=engine)

# # Dependency to get database session
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
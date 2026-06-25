import redis
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


DATABASE_URL_ASYNC = "postgresql+asyncpg://postgres:sanjay@localhost:5432/projects"

async_engine = create_async_engine(DATABASE_URL_ASYNC, echo=False)
sessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

#Redis Client Initialization (Used for Caching & Ephemeral Code State)
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
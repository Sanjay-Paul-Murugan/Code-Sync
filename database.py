import redis
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import redis.asyncio as aioredis

DATABASE_URL_ASYNC = "postgresql+asyncpg://postgres:sanjay@localhost:5432/projects"

async_engine = create_async_engine(DATABASE_URL_ASYNC, echo=False)
sessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

#Redis Client Initialization 
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


# async client for async listening , async version because to constantly listen to pub/sub messages without blocking the fastapi execution
async_redis_client = aioredis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
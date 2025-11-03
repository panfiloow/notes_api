from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./mydatabase.db"


engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    # echo=True # раскомментируйте, чтобы видеть SQL-запросы в консоли
)

async_session_local = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession 
)

Base = declarative_base()

async def get_db():
    async with async_session_local() as session:
        yield session
       
from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager
from .models import Base
from .database import engine 
from .crud import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Запускается инициализация приложения...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Инициализация завершена. Приложение запущено.")
    yield 
    print("Приложение остановлено. Выполняется очистка...")

app = FastAPI(lifespan=lifespan)
app.include_router(router)

@app.get('/')
async def root():
    return {"status": "Server work"}

if __name__ == "__main__":
    uvicorn.run("src.main:app") 
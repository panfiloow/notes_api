import asyncio
from fastapi.testclient import TestClient
from src.main import app 
import pytest


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    from src.database import engine
    from src.models import Base

    print("Запускается инициализация тестовой базы данных...")
    async def run_startup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(run_startup())
    print("Тестовая база данных инициализирована.")

    yield 

    print("Тестовая база данных очищена (если была добавлена логика).")

@pytest.fixture(scope="module")
def client(setup_test_db): 
    with TestClient(app) as c:
        yield c

def test_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "Server work"}

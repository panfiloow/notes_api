import asyncio
from datetime import datetime
from fastapi.testclient import TestClient
from src.main import app 
from src.schemas import Note as NoteSchema
import pytest
from pydantic import ValidationError
from src.database import engine
from src.models import Base

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
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

def test_create_note(client: TestClient):
    """
    Тестирует маршрут POST /notes/ для создания новой заметки.
    """
    new_note_data = {
        "title": "Тестовая заметка",
        "content": "Это содержание тестовой заметки."
    }

    response = client.post("/notes/", json=new_note_data) 

    assert response.status_code == 201 

    response_data = response.json()
    
    assert "id" in response_data
    assert "title" in response_data
    assert "content" in response_data
    assert "created_at" in response_data
    assert "updated_at" in response_data

    
    assert response_data["title"] == new_note_data["title"]
    assert response_data["content"] == new_note_data["content"]

    assert isinstance(response_data["id"], int)
    
    assert isinstance(response_data["created_at"], str)
    assert isinstance(response_data["updated_at"], str)

    try:
        NoteSchema.model_validate(response_data)
    except ValidationError as e:
        pytest.fail(f"Ответ не соответствует схеме NoteSchema: {e}")

def test_create_note_invalid_data(client: TestClient):
    """
    Тестирует маршрут POST /notes/ с неверными данными (например, без обязательного поля title).
    Ожидается HTTP 422 Unprocessable Entity.
    """

    invalid_note_data = {
        "content": "Это содержание без заголовка." 
    }

    response = client.post("/notes/", json=invalid_note_data)

    assert response.status_code == 422 


def test_get_notes(client: TestClient):
    """
    Тестирует маршрут GET /notes/ для получения заметок с пагинацией
    """
    note1_data = {"title": "Test Note 1", "content": "Content of note 1"}
    note2_data = {"title": "Test Note 2", "content": "Content of note 2"}
    note3_data = {"title": "Test Note 3", "content": "Content of note 3"}

    client.post("/notes/", json=note1_data)
    client.post("/notes/", json=note2_data)
    client.post("/notes/", json=note3_data)

    # --- Тест 1: Значения skip и limit по умолчанию ---
    response = client.get("/notes/")
    assert response.status_code == 200

    response_data = response.json()
    assert isinstance(response_data, list)

    for note in response_data:
        try:
            NoteSchema.model_validate(note) 
        except ValidationError as e:
            pytest.fail(f"Элемент списка заметок не соответствует схеме NoteSchema: {e}")


    titles_in_response = [note["title"] for note in response_data]
    assert note1_data["title"] in titles_in_response
    assert note2_data["title"] in titles_in_response
    assert note3_data["title"] in titles_in_response

    # --- Тест 2: Пагинация с параметрами ---
    # GET /notes/?skip=1&limit=1 -> должна вернуть только вторую созданную заметку
    response_paginated = client.get("/notes/?skip=1&limit=1")
    assert response_paginated.status_code == 200

    paginated_data = response_paginated.json()
    assert isinstance(paginated_data, list)
    assert len(paginated_data) == 1
    try:
        NoteSchema.model_validate(paginated_data[0])
    except ValidationError as e:
        pytest.fail(f"Элемент списка пагинированных заметок не соответствует схеме NoteSchema: {e}")


def test_get_note_by_id_success(client: TestClient):
    """
    Тестирует маршрут GET /notes/{id} для получения существующей заметки.
    """
    new_note_data = {
        "title": "Тестовая заметка для получения",
        "content": "Это содержание тестовой заметки для получения."
    }
    create_response = client.post("/notes/", json=new_note_data)
    assert create_response.status_code == 201
    created_note = create_response.json()
    note_id = created_note["id"]
    expected_title = created_note["title"]
    expected_content = created_note["content"]

    response = client.get(f"/notes/{note_id}")

    assert response.status_code == 200 

    response_data = response.json()
    try:
        NoteSchema.model_validate(response_data)
    except ValidationError as e:
        pytest.fail(f"Ответ не соответствует схеме NoteSchema: {e}")

   
    assert response_data["id"] == note_id
    assert response_data["title"] == expected_title
    assert response_data["content"] == expected_content
    
    assert isinstance(response_data["created_at"], str)
    assert isinstance(response_data["updated_at"], str)


def test_get_note_by_id_not_found(client: TestClient):
    """
    Тестирует маршрут GET /notes/{id} для получения несуществующей заметки.
    Ожидается HTTP 404 Not Found.
    """
    # Используем заведомо несуществующий ID (например, 99999)
    non_existent_id = 99999

    response = client.get(f"/notes/{non_existent_id}")

    assert response.status_code == 404 

    response_data = response.json()
    assert "detail" in response_data
    assert f"Note with id {non_existent_id} not found" in response_data["detail"]


def test_update_note_title_success(client: TestClient):
    """
    Тестирует маршрут PUT /notes/{id} для обновления только заголовка (title) существующей заметки.
    """

    initial_data = {
        "title": "Старый заголовок",
        "content": "Старое содержание"
    }
    create_response = client.post("/notes/", json=initial_data)
    assert create_response.status_code == 201
    created_note = create_response.json()
    note_id = created_note["id"]
    initial_created_at = created_note["created_at"]

    update_data = {
        "title": "Новый заголовок"
        # content не передаётся, должно остаться старым
    }

    response = client.put(f"/notes/{note_id}", json=update_data)

    assert response.status_code == 200 

    updated_note = response.json()
    try:
        NoteSchema.model_validate(updated_note)
    except ValidationError as e:
        pytest.fail(f"Ответ не соответствует схеме NoteSchema: {e}")

    assert updated_note["id"] == note_id
    assert updated_note["title"] == update_data["title"]
    assert updated_note["content"] == initial_data["content"]
    assert isinstance(updated_note["created_at"], str)
    assert isinstance(updated_note["updated_at"], str)
    assert updated_note["created_at"] == initial_created_at
    initial_created_at_dt = datetime.fromisoformat(initial_created_at.replace('Z', '+00:00')) if 'Z' in initial_created_at else datetime.fromisoformat(initial_created_at)
    updated_at_dt = datetime.fromisoformat(updated_note["updated_at"].replace('Z', '+00:00')) if 'Z' in updated_note["updated_at"] else datetime.fromisoformat(updated_note["updated_at"])

    assert updated_at_dt >= initial_created_at_dt 

def test_update_note_content_success(client: TestClient):
    """
    Тестирует маршрут PUT /notes/{id} для обновления только содержания (content) существующей заметки.
    """
    initial_data = {
        "title": "Старый заголовок",
        "content": "Старое содержание"
    }
    create_response = client.post("/notes/", json=initial_data)
    assert create_response.status_code == 201
    created_note = create_response.json()
    note_id = created_note["id"]
    initial_created_at = created_note["created_at"]

    # Подготовка данных для обновления (только content)
    update_data = {
        "content": "Новое содержание"
        # title не передаётся, должен остаться старым
    }

    response = client.put(f"/notes/{note_id}", json=update_data)

    assert response.status_code == 200 

    updated_note = response.json()
    try:
        NoteSchema.model_validate(updated_note)
    except ValidationError as e:
        pytest.fail(f"Ответ не соответствует схеме NoteSchema: {e}")

    assert updated_note["id"] == note_id
    assert updated_note["title"] == initial_data["title"] 
    assert updated_note["content"] == update_data["content"] 
    assert isinstance(updated_note["created_at"], str)
    assert isinstance(updated_note["updated_at"], str)
    assert updated_note["created_at"] == initial_created_at
    initial_created_at_dt = datetime.fromisoformat(initial_created_at.replace('Z', '+00:00')) if 'Z' in initial_created_at else datetime.fromisoformat(initial_created_at)
    updated_at_dt = datetime.fromisoformat(updated_note["updated_at"].replace('Z', '+00:00')) if 'Z' in updated_note["updated_at"] else datetime.fromisoformat(updated_note["updated_at"])
    assert updated_at_dt >= initial_created_at_dt

def test_update_note_title_and_content_success(client: TestClient):
    """
    Тестирует маршрут PUT /notes/{id} для обновления и заголовка, и содержания существующей заметки.
    """
    initial_data = {
        "title": "Старый заголовок",
        "content": "Старое содержание"
    }
    create_response = client.post("/notes/", json=initial_data)
    assert create_response.status_code == 201
    created_note = create_response.json()
    note_id = created_note["id"]
    initial_created_at = created_note["created_at"]

    # Подготовка данных для обновления (и title, и content)
    update_data = {
        "title": "Новый заголовок",
        "content": "Новое содержание"
    }

    response = client.put(f"/notes/{note_id}", json=update_data)

    assert response.status_code == 200 

    updated_note = response.json()
    try:
        NoteSchema.model_validate(updated_note)
    except ValidationError as e:
        pytest.fail(f"Ответ не соответствует схеме NoteSchema: {e}")

    assert updated_note["id"] == note_id
    assert updated_note["title"] == update_data["title"] 
    assert updated_note["content"] == update_data["content"] 
    assert isinstance(updated_note["created_at"], str)
    assert isinstance(updated_note["updated_at"], str)
    assert updated_note["created_at"] == initial_created_at
    initial_created_at_dt = datetime.fromisoformat(initial_created_at.replace('Z', '+00:00')) if 'Z' in initial_created_at else datetime.fromisoformat(initial_created_at)
    updated_at_dt = datetime.fromisoformat(updated_note["updated_at"].replace('Z', '+00:00')) if 'Z' in updated_note["updated_at"] else datetime.fromisoformat(updated_note["updated_at"])
    assert updated_at_dt >= initial_created_at_dt

def test_update_note_not_found(client: TestClient):
    """
    Тестирует маршрут PUT /notes/{id} для обновления несуществующей заметки.
    Ожидается HTTP 404 Not Found.
    """
    non_existent_id = 99999
    update_data = {
        "title": "Новый заголовок"
    }

    response = client.put(f"/notes/{non_existent_id}", json=update_data)

    assert response.status_code == 404

    response_data = response.json()
    assert "detail" in response_data
    assert f"Note with id {non_existent_id} not found" in response_data["detail"]


def test_update_note_invalid_data_both_null(client: TestClient):
    """
    Тестирует маршрут PUT /notes/{id} с данными, где и title, и content равны null.
    Это нарушает валидацию в схеме UpdateNote.
    Ожидается HTTP 422 Unprocessable Entity.
    """
    initial_data = {
        "title": "Старый заголовок",
        "content": "Старое содержание"
    }
    create_response = client.post("/notes/", json=initial_data)
    assert create_response.status_code == 201
    created_note = create_response.json()
    note_id = created_note["id"]

    invalid_update_data = {
        "title": None,
        "content": None
    }


    response = client.put(f"/notes/{note_id}", json=invalid_update_data)

    assert response.status_code == 422 


def test_delete_note_success(client: TestClient):
    """
    Тестирует маршрут DELETE /notes/{id} для удаления существующей заметки.
    """
    # Подготовка: Создаём заметку, чтобы получить её ID
    new_note_data = {
        "title": "Тестовая заметка для удаления",
        "content": "Это содержание тестовой заметки для удаления."
    }
    create_response = client.post("/notes/", json=new_note_data)
    assert create_response.status_code == 201
    created_note = create_response.json()
    note_id = created_note["id"]

    get_before_response = client.get(f"/notes/{note_id}")
    assert get_before_response.status_code == 200
    assert get_before_response.json()["id"] == note_id

    response = client.delete(f"/notes/{note_id}")

    assert response.status_code == 204 #

    get_after_response = client.get(f"/notes/{note_id}")
    assert get_after_response.status_code == 404 

def test_delete_note_not_found(client: TestClient):
    """
    Тестирует маршрут DELETE /notes/{id} для удаления несуществующей заметки.
    Ожидается HTTP 404 Not Found.
    """
    # Используем заведомо несуществующий ID (например, 99999)
    non_existent_id = 99999

    response = client.delete(f"/notes/{non_existent_id}")

    assert response.status_code == 404 

    response_data = response.json()
    assert "detail" in response_data
    assert f"Note with id {non_existent_id} not found" in response_data["detail"]
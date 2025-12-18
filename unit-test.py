import pytest
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()

def register_and_login(client, username="u1", password="p1"):
    # Регистрация
    client.post("/auth/register", data={"username": username, "password": password})
    # Логин
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 302  # Редирект после успешного входа
    return client

def test_crud_cycle(client):
    # Авторизация
    register_and_login(client)

    # Добавление записи
    r = client.post("/add", data={"amount": "100.5", "category": "food", "description": "lunch"})
    assert r.status_code == 302  # Редирект после добавления

    # Просмотр списка
    r = client.get("/list")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) > 0
    exp_id = data[0]["id"]

    # Редактирование записи
    r = client.post("/edit", json={"id": exp_id, "category": "groceries"})
    assert r.status_code == 302

    # Проверка, что категория изменилась
    r = client.get("/list")
    data = r.get_json()
    edited = next((e for e in data if e["id"] == exp_id), None)
    assert edited is not None
    assert edited["category"] == "groceries"

    # Удаление записи
    r = client.post("/delete", json={"id": exp_id})
    assert r.status_code == 302

    # Проверка, что запись исчезла
    r = client.get("/list")
    data = r.get_json()
    assert all(e["id"] != exp_id for e in data)

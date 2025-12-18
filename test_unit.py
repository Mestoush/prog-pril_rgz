import pytest
from app import app
import psycopg2

# Конфигурация БД для тестов
TEST_DATABASE = {
    "dbname": "prog-pril_rgz",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": "5432"
}

@pytest.fixture
def client():
    # Создание тестового клиента Flask
    app.config["TESTING"] = True
    return app.test_client()

@pytest.fixture(scope="function")
def clean_db(request):
    # Setup
    conn = psycopg2.connect(**TEST_DATABASE)
    cur = conn.cursor()
    cur.execute("DELETE FROM audit_logs; DELETE FROM expenses; DELETE FROM users;")
    conn.commit()
    cur.close()
    conn.close()
    
    # очистка БД через addfinalizer
    def cleanup():
        conn = psycopg2.connect(**TEST_DATABASE)
        cur = conn.cursor()
        cur.execute("DELETE FROM audit_logs; DELETE FROM expenses; DELETE FROM users;")
        conn.commit()
        cur.close()
        conn.close()
    
    request.addfinalizer(cleanup)

def _register_and_login(client, username="u1", password="p1"):
    client.post("/auth/register", data={"username": username, "password": password})
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 302
    return client

def test_crud_cycle(client, clean_db):
    _register_and_login(client)
    
    r = client.post("/add", data={"amount": "100.5", "category": "food", "description": "lunch"})
    assert r.status_code == 302
    
    r = client.get("/list")
    data = r.get_json()
    assert len(data) > 0
    exp_id = data[0]["id"]
    
    r = client.post("/edit", json={"id": exp_id, "category": "groceries"})
    assert r.status_code == 302
    
    r = client.get("/list")
    edited = next((e for e in r.get_json() if e["id"] == exp_id), None)
    assert edited["category"] == "groceries"
    
    r = client.post("/delete", json={"id": exp_id})
    assert r.status_code == 302
    
    r = client.get("/list")
    assert all(e["id"] != exp_id for e in r.get_json())

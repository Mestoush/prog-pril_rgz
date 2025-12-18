import psycopg2
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret"

database = {
    "dbname": "prog-pril_rgz",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": "5432"
}

login_manager = LoginManager(app)
login_manager.login_view = "login_page"

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

@login_manager.user_loader
def load_user(user_id):
    conn = psycopg2.connect(**database)
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return User(*row)
    return None

@app.get("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("expenses_page"))
    return redirect(url_for("login_page"))

@app.get("/login")
def login_page():
    return render_template("login.html")

@app.get("/expenses")
@login_required
def expenses_page():
    conn = psycopg2.connect(**database)
    cur = conn.cursor()
    cur.execute("SELECT id, amount, category, description FROM expenses WHERE user_id=%s", (current_user.id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("expenses.html", expenses=rows)

# аутентификация
@app.post("/auth/register")
def register():
    username = request.form.get("username")
    password = request.form.get("password")
    if not username or not password:
        return "username and password required", 400
    conn = psycopg2.connect(**database)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                    (username, generate_password_hash(password)))
        conn.commit()
    except psycopg2.Error:
        conn.rollback()
        return "username taken", 400
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("login_page"))

@app.post("/auth/login")
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    conn = psycopg2.connect(**database)
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash FROM users WHERE username=%s", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row or not check_password_hash(row[2], password):
        return "invalid credentials", 401
    user = User(*row)
    login_user(user)
    return redirect(url_for("expenses_page"))

@app.post("/auth/logout")
def logout():
    logout_user()
    return redirect(url_for("login_page"))

# настройка аудита
def record_audit(user_id, action, expense_id=None):
    conn = psycopg2.connect(**database)
    cur = conn.cursor()
    cur.execute("INSERT INTO audit_logs (user_id, action, expense_id, timestamp) VALUES (%s,%s,%s,%s)",
                (user_id, action, expense_id, datetime.utcnow()))
    conn.commit()
    cur.close()
    conn.close()

# данные о расходах
@app.get("/list")
@login_required
def list_expenses():
    conn = psycopg2.connect(**database)
    cur = conn.cursor()
    cur.execute("SELECT id, amount, category, description FROM expenses WHERE user_id=%s", (current_user.id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    expenses = [{"id": r[0], "amount": r[1], "category": r[2], "description": r[3]} for r in rows]
    return jsonify(expenses)

@app.post("/add")
@login_required
def add_expense():
    data = request.get_json() if request.is_json else request.form
    amount = data.get("amount")
    category = data.get("category")
    description = data.get("description")
    conn = psycopg2.connect(**database)
    cur = conn.cursor()
    cur.execute("INSERT INTO expenses (user_id, amount, category, description) VALUES (%s,%s,%s,%s) RETURNING id",
                (current_user.id, amount, category, description))
    exp_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    record_audit(current_user.id, "add", exp_id)
    return redirect(url_for("expenses_page"))

@app.post("/edit")
@login_required
def edit_expense():
    data = request.get_json() if request.is_json else request.form
    expense_id = data.get("id")
    new_category = data.get("category")
    conn = psycopg2.connect(**database)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM expenses WHERE id=%s", (expense_id,))
    row = cur.fetchone()
    if not row or row[0] != current_user.id:
        cur.close()
        conn.close()
        return "not found", 404
    cur.execute("UPDATE expenses SET category=%s, updated_at=%s WHERE id=%s",
                (new_category, datetime.utcnow(), expense_id))
    conn.commit()
    cur.close()
    conn.close()
    record_audit(current_user.id, "edit", expense_id)
    return redirect(url_for("expenses_page"))

@app.post("/delete")
@login_required
def delete_expense():
    data = request.get_json() if request.is_json else request.form
    expense_id = data.get("id")
    conn = psycopg2.connect(**database)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM expenses WHERE id=%s", (expense_id,))
    row = cur.fetchone()
    if not row or row[0] != current_user.id:
        cur.close()
        conn.close()
        return "not found", 404
    record_audit(current_user.id, "delete", expense_id)
    cur.execute("DELETE FROM expenses WHERE id=%s", (expense_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("expenses_page"))

if __name__ == "__main__":
    app.run(debug=True)

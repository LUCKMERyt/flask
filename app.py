from flask import Flask, request, render_template, redirect, url_for, flash
from flask_migrate import Migrate
from sqlalchemy import text
from models import db, User, TestDB, Category, Product, PageView
from admin import admin_bp
from functools import wraps

app = Flask(__name__)
app.secret_key = "super_secret_key_change_this"

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://myuser:1234@127.0.0.1:3306/myapp"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate = Migrate(app, db)

# Функция записи посещения
def log_visit(page_name):
    try:
        db.session.add(PageView(page=page_name, ip=request.remote_addr))
        db.session.commit()
    except Exception:
        db.session.rollback()

with app.app_context():
    try:
        db.session.execute(text("SELECT 1"))
        print(f"\033[1;3;4;92m Подключение к базе успешно выполнено \033[0m")
    except Exception as e:
        print(f"\033[1;3;4;91m Ошибка подключения: {e}\033[0m")

@app.route("/")
def home():
    log_visit("home")
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    log_visit("login")
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        return "Вы вошли в систему!"
    return render_template("login.html")

@app.route("/user/<username>-<int:user_id>")
def user_profile(username, user_id):
    return (
        f"<h1>Это профиль пользователя {username}.</h1>"
        f'<h2 style="color: red;">С ID {user_id}. Привет!</h2>'
    )

@app.route("/about")
def about():
    log_visit("about")
    return render_template("about.html")

@app.route("/neo")
def neo():
    return render_template("neo.html")

@app.route("/comm")
def comm():
    return render_template("comm.html")

@app.route("/test_db")
def test_db():
    log_visit("test_db")
    rows = TestDB.query.order_by(TestDB.id).all()
    return render_template("test_db.html", rows=rows)

@app.route("/add", methods=["POST"])
def add_record():
    name = request.form.get("name", "").strip()
    age = request.form.get("age", type=int)
    if not name or age is None or age < 0:
        return "Введите корректные имя и возраст", 400
    db.session.add(TestDB(name=name, age=age))
    db.session.commit()
    return redirect(url_for("test_db"))

@app.route("/update/<int:id>", methods=["POST"])
def update_record(id):
    row = db.session.get(TestDB, id)
    if row is None:
        return "Запись не найдена", 404
    name = request.form.get("name", "").strip()
    age = request.form.get("age", type=int)
    if not name or age is None or age < 0:
        return "Введите корректные имя и возраст", 400
    row.name = name
    row.age = age
    db.session.commit()
    return redirect(url_for("test_db"))

@app.route("/delete/<int:id>", methods=["POST"])
def delete_record(id):
    row = db.session.get(TestDB, id)
    if row is None:
        return "Запись не найдена", 404
    db.session.delete(row)
    db.session.commit()
    return redirect(url_for("test_db"))

@app.route("/catalog")
def catalog():
    log_visit("catalog")
    categories = Category.query.order_by(Category.name).all()
    category_id = request.args.get("category_id", type=int)
    query = Product.query.order_by(Product.id)
    if category_id is not None:
        query = query.filter_by(category_id=category_id)
    products = query.all()
    return render_template(
        "catalog.html",
        categories=categories,
        products=products,
        selected_category_id=category_id
    )

@app.route("/categories/add", methods=["POST"])
def add_category():
    name = request.form.get("name", "").strip()
    if not name:
        return "Введите название категории", 400
    db.session.add(Category(name=name))
    db.session.commit()
    return redirect(url_for("catalog"))

@app.route("/products/add", methods=["POST"])
def add_product():
    name = request.form.get("name", "").strip()
    price = request.form.get("price", type=float)
    category_id = request.form.get("category_id", type=int)
    if not name or price is None or price < 0:
        return "Введите корректные название и цену", 400
    category = db.session.get(Category, category_id)
    if category is None:
        return "Категория не найдена", 404
    db.session.add(Product(name=name, price=price, category=category))
    db.session.commit()
    return redirect(url_for("catalog"))

app.register_blueprint(admin_bp)

if __name__ == "__main__":
    app.run(debug=True)
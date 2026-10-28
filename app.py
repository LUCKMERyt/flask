from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import text

# --- НОВЫЕ ИМПОРТЫ ДЛЯ АДМИНКИ И АВТОРИЗАЦИИ ---
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://myuser:1234@127.0.0.1:3306/myapp"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "super-secret-key-change-me-in-production"  # <-- НОВОЕ (обязательно для сессий)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- ИНИЦИАЛИЗАЦИЯ FLASK-LOGIN ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- ОБНОВЛЁННАЯ МОДЕЛЬ USER ---
class User(UserMixin, db.Model):  # <-- ДОБАВЛЕНО: UserMixin
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # <-- НОВОЕ: флаг администратора

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

# --- ОСТАЛЬНЫЕ МОДЕЛИ (оставляем как у вас было) ---
class TestDB(db.Model):
    __tablename__ = "test_db"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    age = db.Column(db.Integer)

class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    products = db.relationship("Product", back_populates="category", cascade="all, delete-orphan")

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    category = db.relationship("Category", back_populates="products")


# --- НАСТРОЙКА FLASK-ADMIN ---
class AdminModelView(ModelView):
    """Защищает страницы админки: доступ только для авторизованных админов"""
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

# Инициализация админ-панели
admin = Admin(app, name='Панель управления')

# Добавляем ваши модели в админку
admin.add_view(AdminModelView(User, db.session, name='Пользователи'))
admin.add_view(AdminModelView(TestDB, db.session, name='TestDB'))
admin.add_view(AdminModelView(Category, db.session, name='Категории'))
admin.add_view(AdminModelView(Product, db.session, name='Товары'))


with app.app_context():
    try:
        db.session.execute(text("SELECT 1"))
        print(f"\033[1;3;4;92m Подключение к базе успешно выполнено \033[0m")
    except Exception as e:
        print(f"\033[1;3;4;91m Ошибка подключения: {e}\033[0m")


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    # Если уже вошёл, сразу кидаем в админку
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))
        
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        # <-- НОВОЕ: реальная проверка пароля через хэш
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin.index'))
            
        return "Неверный логин или пароль", 401

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/user/<username>-<int:user_id>")
def user_profile(username, user_id):
    return (
        f"<h1>Это профиль пользователя {username}.</h1>"
        f'<h2 style="color: red;">С ID {user_id}. Привет!</h2>'
    )


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/neo")
def neo():
    return render_template("neo.html")


@app.route("/comm")
def comm():
    return render_template("comm.html")


#! ------------------test_db------------------------------

@app.route("/test_db")
def test_db():
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



#! -----------------catalog--------------------

@app.route("/catalog")
def catalog():
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


if __name__ == "__main__":
    app.run(debug=True)
import os
import re

from flask import (
    Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for,
)
from flask_migrate import Migrate
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from utils import (
    admin_required, check_csrf, csrf_input, csrf_token, dt, is_admin, like_pattern,
    load_env_file, ru_plural, rub, safe_next, safe_query, utcnow,
)

load_env_file()

from models import db, User, TestDB, Category, Product, PageView, Review  # noqa: E402
from admin import admin_bp  # noqa: E402

app = Flask(__name__)

# Настройки берутся из переменных окружения / файла .env.
# Значения по умолчанию оставлены прежними, чтобы проект запускался как раньше.
app.secret_key = os.environ.get("SECRET_KEY", "super_secret_key_change_this")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "mysql+pymysql://myuser:1234@127.0.0.1:3306/myapp"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db.init_app(app)
migrate = Migrate(app, db)

PER_PAGE = 12
REVIEWS_PER_PAGE = 10
USERNAME_RE = re.compile(r"^[\w.\-]{3,30}$")

SORTS = {
    "new": ("Сначала новые", lambda: Product.id.desc()),
    "price_asc": ("Сначала дешевле", lambda: Product.price.asc()),
    "price_desc": ("Сначала дороже", lambda: Product.price.desc()),
    "name": ("По названию", lambda: Product.name.asc()),
}


# ==================== Шаблонные хелперы ====================

app.jinja_env.filters["rub"] = rub
app.jinja_env.filters["dt"] = dt


@app.context_processor
def inject_globals():
    def url_with(**changes):
        """Текущий URL с изменёнными GET-параметрами (None/'' — удалить параметр)."""
        args = request.args.to_dict()
        args.update(changes)
        args = {k: v for k, v in args.items() if v not in (None, "")}
        return url_for(request.endpoint, **args)

    username = session.get("username")
    return {
        "csrf_input": csrf_input,
        "csrf_token": csrf_token,
        "is_admin": is_admin,
        "now": utcnow,
        "ru_plural": ru_plural,
        "url_with": url_with,
        "current_user": {"id": session.get("user_id"), "username": username} if username else None,
    }


@app.before_request
def protect_from_csrf():
    if request.method == "POST":
        check_csrf()


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


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


# ==================== Страницы ====================

@app.route("/")
def home():
    log_visit("home")
    stats = {
        "products": safe_query(lambda: Product.query.count(), 0),
        "categories": safe_query(lambda: Category.query.count(), 0),
        "reviews": safe_query(lambda: Review.query.count(), 0),
    }
    latest = safe_query(lambda: Product.query.order_by(Product.id.desc()).limit(4).all(), [])
    return render_template("index.html", stats=stats, latest=latest)


@app.route("/login", methods=["GET", "POST"])
def login():
    log_visit("login")
    next_url = safe_next(request.values.get("next"), url_for("home"))
    mode = "register" if request.args.get("mode") == "register" else "login"
    username = ""

    if request.method == "POST":
        action = request.form.get("action", "login")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        try:
            if action == "register":
                mode = "register"
                confirm = request.form.get("confirm", "")
                error = None
                if not USERNAME_RE.match(username):
                    error = "Логин: 3–30 символов — буквы, цифры, точка, дефис и подчёркивание."
                elif len(password) < 6:
                    error = "Пароль должен быть не короче 6 символов."
                elif password != confirm:
                    error = "Пароли не совпадают."
                elif User.query.filter(func.lower(User.username) == username.lower()).first():
                    error = "Этот логин уже занят."

                if error:
                    flash(error, "error")
                else:
                    user = User(username=username, password_hash=generate_password_hash(password))
                    db.session.add(user)
                    db.session.commit()
                    session["user_id"] = user.id
                    session["username"] = user.username
                    flash(f"Добро пожаловать, {user.username}! Аккаунт создан.", "success")
                    return redirect(next_url)
            else:
                mode = "login"
                user = User.query.filter(func.lower(User.username) == username.lower()).first()
                if user and check_password_hash(user.password_hash, password):
                    session["user_id"] = user.id
                    session["username"] = user.username
                    flash(f"С возвращением, {user.username}!", "success")
                    return redirect(next_url)
                flash("Неверный логин или пароль.", "error")
        except SQLAlchemyError:
            db.session.rollback()
            flash("База данных сейчас недоступна. Попробуйте чуть позже.", "error")

    return render_template("login.html", mode=mode, username=username, next_url=next_url)


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for("home"))


@app.route("/user/<username>-<int:user_id>")
def user_profile(username, user_id):
    user = safe_query(lambda: db.session.get(User, user_id))
    known = bool(user and user.username == username)
    return render_template(
        "profile.html", username=username, user_id=user_id,
        created_at=user.created_at if known else None, known=known,
    )


@app.route("/about")
def about():
    log_visit("about")
    return render_template("about.html")


@app.route("/neo")
def neo():
    log_visit("neo")
    return render_template("neo.html")


# ==================== Отзывы ====================

@app.route("/comm", methods=["GET", "POST"])
def comm():
    form = {"name": session.get("username", ""), "rating": 0, "text": ""}

    if request.method == "POST":
        form["name"] = request.form.get("name", "").strip()
        form["text"] = request.form.get("text", "").strip()
        form["rating"] = request.form.get("rating", type=int) or 0

        if request.form.get("website"):  # honeypot: боты заполняют скрытое поле
            flash("Спасибо за отзыв!", "success")
            return redirect(url_for("comm"))

        error = None
        if not 2 <= len(form["name"]) <= 60:
            error = "Имя должно быть от 2 до 60 символов."
        elif form["rating"] not in (1, 2, 3, 4, 5):
            error = "Поставьте оценку от 1 до 5 звёзд."
        elif not 5 <= len(form["text"]) <= 1000:
            error = "Отзыв должен быть от 5 до 1000 символов."

        if error:
            flash(error, "error")
        else:
            try:
                db.session.add(Review(name=form["name"], rating=form["rating"], text=form["text"]))
                db.session.commit()
                flash("Спасибо! Ваш отзыв опубликован.", "success")
                return redirect(url_for("comm"))
            except SQLAlchemyError:
                db.session.rollback()
                flash("Не удалось сохранить отзыв. Проверьте, что выполнена миграция: flask db upgrade", "error")

    log_visit("comm")
    page = request.args.get("page", 1, type=int)
    table_ready = True
    pagination = None
    summary = {"count": 0, "average": 0.0, "distribution": {i: 0 for i in range(1, 6)}}
    try:
        pagination = (
            Review.query.order_by(Review.created_at.desc(), Review.id.desc())
            .paginate(page=page, per_page=REVIEWS_PER_PAGE, error_out=False)
        )
        total, avg = db.session.query(func.count(Review.id), func.avg(Review.rating)).one()
        summary["count"] = total or 0
        summary["average"] = float(avg or 0)
        for rating, cnt in db.session.query(Review.rating, func.count(Review.id)).group_by(Review.rating):
            if rating in summary["distribution"]:
                summary["distribution"][rating] = cnt
    except SQLAlchemyError:
        db.session.rollback()
        table_ready = False

    return render_template(
        "comm.html", form=form, pagination=pagination, summary=summary, table_ready=table_ready,
    )


# ==================== Таблица test_db ====================

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
        flash("Введите корректные имя и возраст", "error")
        return redirect(url_for("test_db"))

    db.session.add(TestDB(name=name, age=age))
    db.session.commit()
    flash("Запись успешно добавлена!", "success")
    return redirect(url_for("test_db"))


@app.route("/update/<int:id>", methods=["POST"])
def update_record(id):
    row = db.session.get(TestDB, id)
    if row is None:
        abort(404)
    name = request.form.get("name", "").strip()
    age = request.form.get("age", type=int)
    if not name or age is None or age < 0:
        flash("Введите корректные имя и возраст", "error")
        return redirect(url_for("test_db"))
    row.name = name
    row.age = age
    db.session.commit()
    flash("Запись обновлена", "success")
    return redirect(url_for("test_db"))


@app.route("/delete/<int:id>", methods=["POST"])
def delete_record(id):
    row = db.session.get(TestDB, id)
    if row is None:
        abort(404)
    db.session.delete(row)
    db.session.commit()
    flash("Запись удалена", "info")
    return redirect(url_for("test_db"))


# ==================== Каталог ====================

@app.route("/catalog")
def catalog():
    log_visit("catalog")

    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    sort = request.args.get("sort", "new")
    if sort not in SORTS:
        sort = "new"
    page = request.args.get("page", 1, type=int)

    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(like_pattern(q), escape="\\"))
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    query = query.order_by(SORTS[sort][1](), Product.id)

    pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)

    category_rows = (
        db.session.query(Category, func.count(Product.id))
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name)
        .all()
    )
    categories = [c for c, _ in category_rows]
    category_counts = {c.id: n for c, n in category_rows}
    total_products = sum(category_counts.values())
    price_min, price_max = db.session.query(func.min(Product.price), func.max(Product.price)).one()

    selected_category = next((c for c in categories if c.id == category_id), None)
    has_filters = bool(q or category_id is not None or min_price is not None or max_price is not None)

    return render_template(
        "catalog.html",
        categories=categories,
        category_counts=category_counts,
        total_products=total_products,
        pagination=pagination,
        products=pagination.items,
        selected_category_id=category_id,
        selected_category=selected_category,
        q=q, min_price=min_price, max_price=max_price,
        sort=sort, sorts=SORTS, has_filters=has_filters,
        price_bounds=(price_min, price_max),
    )


@app.route("/api/suggest")
def api_suggest():
    """Подсказки для живого поиска в каталоге."""
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    rows = (
        Product.query.filter(Product.name.ilike(like_pattern(q), escape="\\"))
        .order_by(Product.name).limit(6).all()
    )
    return jsonify([
        {
            "id": p.id,
            "name": p.name,
            "price": rub(p.price),
            "category": p.category.name if p.category else None,
            "url": url_for("catalog", q=p.name),
        }
        for p in rows
    ])


@app.route("/categories/add", methods=["POST"])
@admin_required
def add_category():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Введите название категории", "error")
        return redirect(url_for("catalog"))
    if Category.query.filter(func.lower(Category.name) == name.lower()).first():
        flash(f"Категория «{name}» уже существует", "error")
        return redirect(url_for("catalog"))
    db.session.add(Category(name=name))
    db.session.commit()
    flash(f"Категория «{name}» добавлена", "success")
    return redirect(url_for("catalog"))


@app.route("/products/add", methods=["POST"])
@admin_required
def add_product():
    name = request.form.get("name", "").strip()
    price = request.form.get("price", type=float)
    category_id = request.form.get("category_id", type=int)
    if not name or price is None or price < 0:
        flash("Введите корректные название и цену", "error")
        return redirect(url_for("catalog"))
    category = db.session.get(Category, category_id) if category_id else None
    if category is None:
        flash("Категория не найдена", "error")
        return redirect(url_for("catalog"))
    db.session.add(Product(name=name, price=price, category=category))
    db.session.commit()
    flash(f"Товар «{name}» добавлен", "success")
    return redirect(url_for("catalog", category_id=category.id))


# ==================== Ошибки ====================

ERRORS = {
    400: ("Некорректный запрос", "Форма устарела или запрос был неверным. Обновите страницу и попробуйте снова."),
    403: ("Доступ запрещён", "У вас нет прав для просмотра этой страницы."),
    404: ("Страница не найдена", "Такой страницы нет — возможно, она переехала или в адресе опечатка."),
    500: ("Что-то пошло не так", "На сервере произошла ошибка. Мы уже в курсе — попробуйте позже."),
}


def render_error(code):
    title, message = ERRORS[code]
    return render_template("error.html", code=code, title=title, message=message), code


@app.errorhandler(400)
def bad_request(_):
    return render_error(400)


@app.errorhandler(403)
def forbidden(_):
    return render_error(403)


@app.errorhandler(404)
def not_found(_):
    return render_error(404)


@app.errorhandler(500)
def server_error(_):
    db.session.rollback()
    return render_error(500)


app.register_blueprint(admin_bp)

if __name__ == "__main__":
    app.run(debug=True)

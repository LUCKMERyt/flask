"""Общие утилиты: CSRF-защита, права администратора, форматирование, безопасные запросы."""
import os
import secrets
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from urllib.parse import urlparse

from flask import abort, flash, redirect, request, session, url_for
from markupsafe import Markup
from sqlalchemy.exc import SQLAlchemyError

from models import db


# ---------------------------------------------------------------- .env
def load_env_file(path=".env"):
    """Мини-загрузчик .env (без внешних зависимостей). Уже заданные переменные не трогает."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


# ---------------------------------------------------------------- права
def admin_usernames():
    raw = os.environ.get("ADMIN_USERNAMES", "")
    return {name.strip().lower() for name in raw.split(",") if name.strip()}


def is_admin():
    """Если ADMIN_USERNAMES не задана — поведение прежнее (админка открыта).
    Если задана — доступ только у перечисленных пользователей."""
    admins = admin_usernames()
    if not admins:
        return True
    return (session.get("username") or "").lower() in admins


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_admin():
            flash("Для этого действия нужны права администратора.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


# ---------------------------------------------------------------- CSRF
def csrf_token():
    token = session.get("_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf"] = token
    return token


def csrf_input():
    return Markup('<input type="hidden" name="csrf_token" value="%s">' % csrf_token())


def check_csrf():
    sent = request.form.get("csrf_token") or request.headers.get("X-CSRFToken", "")
    token = session.get("_csrf", "")
    if not token or not secrets.compare_digest(sent.encode(), token.encode()):
        abort(400)


# ---------------------------------------------------------------- прочее
def safe_next(target, default):
    """Разрешаем редирект только на локальные пути (защита от open redirect)."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return default
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return default
    return target


def safe_query(fn, default=None):
    """Выполнить запрос к БД; при ошибке — откатить сессию и вернуть значение по умолчанию."""
    try:
        return fn()
    except SQLAlchemyError:
        db.session.rollback()
        return default


def like_pattern(text):
    """Экранирует спецсимволы LIKE (используйте с escape='\\\\')."""
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def rub(value):
    """12345.5 -> '12 345,50 ₽'"""
    if value is None:
        return "—"
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
    if amount == amount.to_integral_value():
        number = f"{int(amount):,}".replace(",", " ")
    else:
        number = f"{amount:,.2f}".replace(",", " ").replace(".", ",")
    return f"{number} ₽"


def dt(value, fmt="%d.%m.%Y %H:%M"):
    return value.strftime(fmt) if value else "—"


def ru_plural(n, one, few, many):
    n = abs(int(n))
    if 11 <= n % 100 <= 14:
        return many
    if n % 10 == 1:
        return one
    if 2 <= n % 10 <= 4:
        return few
    return many


def utcnow():
    return datetime.utcnow()

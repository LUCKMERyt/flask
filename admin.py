import csv
import io
from datetime import datetime, timedelta

from flask import (
    Blueprint, Response, flash, redirect, render_template, request, session, url_for,
)
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from models import db, Product, Category, User, PageView, Review
from utils import is_admin, like_pattern, safe_query

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

PER_PAGE = 15


@admin_bp.before_request
def require_admin():
    """Если задана переменная ADMIN_USERNAMES — пускаем только перечисленных пользователей."""
    if not is_admin():
        flash('Для входа в админ-панель нужны права администратора.', 'error')
        return redirect(url_for('login', next=request.path))


def daily_counts(model, column, days=7):
    """Количество записей по дням за последние `days` дней (включая сегодня)."""
    today = datetime.utcnow().date()
    start = today - timedelta(days=days - 1)
    rows = (
        db.session.query(func.date(column), func.count(model.id))
        .filter(func.date(column) >= start)
        .group_by(func.date(column))
        .all()
    )
    by_day = {str(day): count for day, count in rows}
    labels, values = [], []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        labels.append(day.strftime('%d.%m'))
        values.append(by_day.get(day.isoformat(), 0))
    return labels, values


# ==================== ДАШБОРД ====================

@admin_bp.route('/')
@admin_bp.route('/dashboard')
def dashboard():
    week_ago = datetime.utcnow() - timedelta(days=7)

    total_users = User.query.count()
    total_products = Product.query.count()
    total_categories = Category.query.count()

    users_last_week = User.query.filter(User.created_at >= week_ago).count()
    products_last_week = Product.query.filter(Product.added_at >= week_ago).count()

    # Реальная статистика посещений вместо прежней заглушки «выручка»
    views_week = safe_query(lambda: PageView.query.filter(PageView.visited_at >= week_ago).count(), 0)
    labels, visits_data = safe_query(lambda: daily_counts(PageView, PageView.visited_at), ([], []))
    _, registrations_data = safe_query(lambda: daily_counts(User, User.created_at), ([], []))

    top_pages = safe_query(
        lambda: db.session.query(PageView.page, func.count(PageView.id).label('cnt'))
        .filter(PageView.visited_at >= week_ago)
        .group_by(PageView.page)
        .order_by(func.count(PageView.id).desc())
        .limit(6).all(),
        [],
    )

    recent_products = Product.query.order_by(Product.id.desc()).limit(5).all()
    categories = Category.query.order_by(Category.name).all()
    recent_reviews = safe_query(lambda: Review.query.order_by(Review.id.desc()).limit(4).all(), [])
    reviews_total = safe_query(lambda: Review.query.count(), 0)
    avg_rating = safe_query(lambda: float(db.session.query(func.avg(Review.rating)).scalar() or 0), 0.0)

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_products=total_products,
        total_categories=total_categories,
        users_last_week=users_last_week,
        products_last_week=products_last_week,
        views_week=views_week,
        recent_products=recent_products,
        categories=categories,
        recent_reviews=recent_reviews,
        reviews_total=reviews_total,
        avg_rating=avg_rating,
        top_pages=top_pages,
        visits_labels=labels,
        visits_data=visits_data,
        registrations_data=registrations_data,
    )


# ==================== ТОВАРЫ (полный CRUD) ====================

def filtered_products():
    search = request.args.get('search', '').strip()
    category_id = request.args.get('category_id', type=int)
    sort = request.args.get('sort', 'new')

    query = Product.query
    if search:
        query = query.filter(Product.name.ilike(like_pattern(search), escape='\\'))
    if category_id:
        query = query.filter(Product.category_id == category_id)

    order = {
        'new': Product.id.desc(),
        'old': Product.id.asc(),
        'price_asc': Product.price.asc(),
        'price_desc': Product.price.desc(),
        'name': Product.name.asc(),
    }.get(sort, Product.id.desc())
    return query.order_by(order), search, category_id, sort


@admin_bp.route('/products')
def products_list():
    query, search, category_id, sort = filtered_products()
    page = request.args.get('page', 1, type=int)
    pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)
    categories = Category.query.order_by(Category.name).all()
    return render_template(
        'admin/products.html', products=pagination.items, pagination=pagination,
        categories=categories, search=search, category_id=category_id, sort=sort,
    )


@admin_bp.route('/products/export.csv')
def products_export():
    query, *_ = filtered_products()
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow(['ID', 'Название', 'Цена', 'Категория', 'Добавлен'])
    for p in query.all():
        writer.writerow([
            p.id, p.name, p.price, p.category.name if p.category else '',
            p.added_at.strftime('%Y-%m-%d %H:%M') if p.added_at else '',
        ])
    # utf-8-sig, чтобы Excel корректно открыл кириллицу
    data = '﻿' + buffer.getvalue()
    return Response(
        data, mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=products.csv'},
    )


@admin_bp.route('/products/add', methods=['POST'])
def product_add():
    name = request.form.get('name', '').strip()
    price = request.form.get('price', type=float)
    category_id = request.form.get('category_id', type=int)

    if not name or price is None or price < 0 or not category_id:
        flash('Ошибка: заполните все поля корректно', 'error')
        return redirect(url_for('admin.products_list'))
    if db.session.get(Category, category_id) is None:
        flash('Ошибка: такой категории не существует', 'error')
        return redirect(url_for('admin.products_list'))

    db.session.add(Product(name=name, price=price, category_id=category_id))
    db.session.commit()
    flash(f'Товар "{name}" успешно добавлен!', 'success')
    return redirect(url_for('admin.products_list'))


@admin_bp.route('/products/<int:id>/edit', methods=['POST'])
def product_edit(id):
    product = Product.query.get_or_404(id)
    name = request.form.get('name', '').strip()
    price = request.form.get('price', type=float)
    category_id = request.form.get('category_id', type=int)

    # Сначала проверяем данные — и только потом меняем объект
    if not name or price is None or price < 0 or not category_id:
        flash('Ошибка: некорректные данные', 'error')
        return redirect(url_for('admin.products_list'))
    if db.session.get(Category, category_id) is None:
        flash('Ошибка: такой категории не существует', 'error')
        return redirect(url_for('admin.products_list'))

    product.name = name
    product.price = price
    product.category_id = category_id
    db.session.commit()
    flash(f'Товар "{product.name}" обновлён', 'success')
    return redirect(url_for('admin.products_list'))


@admin_bp.route('/products/<int:id>/delete', methods=['POST'])
def product_delete(id):
    product = Product.query.get_or_404(id)
    name = product.name
    db.session.delete(product)
    db.session.commit()
    flash(f'Товар "{name}" удалён', 'success')
    return redirect(request.referrer or url_for('admin.products_list'))


# ==================== КАТЕГОРИИ (полный CRUD) ====================

@admin_bp.route('/categories')
def categories_list():
    search = request.args.get('search', '').strip()
    query = Category.query
    if search:
        query = query.filter(Category.name.ilike(like_pattern(search), escape='\\'))
    categories = query.order_by(Category.id.desc()).all()
    return render_template('admin/categories.html', categories=categories, search=search)


@admin_bp.route('/categories/add', methods=['POST'])
def category_add():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Ошибка: введите название категории', 'error')
        return redirect(url_for('admin.categories_list'))

    existing = Category.query.filter_by(name=name).first()
    if existing:
        flash(f'Категория "{name}" уже существует', 'error')
        return redirect(url_for('admin.categories_list'))

    db.session.add(Category(name=name))
    db.session.commit()
    flash(f'Категория "{name}" создана', 'success')
    return redirect(url_for('admin.categories_list'))


@admin_bp.route('/categories/<int:id>/edit', methods=['POST'])
def category_edit(id):
    category = Category.query.get_or_404(id)
    new_name = request.form.get('name', '').strip()

    if not new_name:
        flash('Ошибка: введите название', 'error')
        return redirect(url_for('admin.categories_list'))

    existing = Category.query.filter(Category.name == new_name, Category.id != id).first()
    if existing:
        flash(f'Категория "{new_name}" уже существует', 'error')
        return redirect(url_for('admin.categories_list'))

    old_name = category.name
    category.name = new_name
    db.session.commit()
    flash(f'Категория "{old_name}" переименована в "{new_name}"', 'success')
    return redirect(url_for('admin.categories_list'))


@admin_bp.route('/categories/<int:id>/delete', methods=['POST'])
def category_delete(id):
    category = Category.query.get_or_404(id)
    name = category.name
    db.session.delete(category)
    db.session.commit()
    flash(f'Категория "{name}" удалена', 'success')
    return redirect(url_for('admin.categories_list'))


# ==================== ПОЛЬЗОВАТЕЛИ ====================

@admin_bp.route('/users')
def users_list():
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    query = User.query
    if search:
        query = query.filter(User.username.ilike(like_pattern(search), escape='\\'))
    pagination = query.order_by(User.id.desc()).paginate(page=page, per_page=PER_PAGE, error_out=False)
    return render_template('admin/users.html', users=pagination.items, pagination=pagination, search=search)


@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
def user_delete(id):
    user = User.query.get_or_404(id)
    if session.get('user_id') == user.id:
        flash('Нельзя удалить самого себя, пока вы вошли под этим аккаунтом.', 'error')
        return redirect(url_for('admin.users_list'))
    name = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'Пользователь "{name}" удалён', 'success')
    return redirect(url_for('admin.users_list'))


# ==================== ОТЗЫВЫ ====================

@admin_bp.route('/reviews')
def reviews_list():
    page = request.args.get('page', 1, type=int)
    table_ready = True
    pagination = None
    try:
        pagination = Review.query.order_by(Review.id.desc()).paginate(
            page=page, per_page=PER_PAGE, error_out=False)
    except SQLAlchemyError:
        db.session.rollback()
        table_ready = False
    return render_template('admin/reviews.html', pagination=pagination, table_ready=table_ready)


@admin_bp.route('/reviews/<int:id>/delete', methods=['POST'])
def review_delete(id):
    review = Review.query.get_or_404(id)
    db.session.delete(review)
    db.session.commit()
    flash('Отзыв удалён', 'success')
    return redirect(request.referrer or url_for('admin.reviews_list'))

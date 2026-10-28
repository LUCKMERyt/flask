from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Product, Category, User
from datetime import datetime, timedelta
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ==================== ДАШБОРД ====================

@admin_bp.route('/')
@admin_bp.route('/dashboard')
def dashboard():
    today = datetime.now().date()
    last_week = today - timedelta(days=7)

    # Базовая статистика
    total_users = User.query.count()
    total_products = Product.query.count()
    total_categories = Category.query.count()

    # Тренды за неделю
    users_last_week = User.query.filter(func.date(User.created_at) >= last_week).count()
    products_last_week = Product.query.filter(func.date(Product.added_at) >= last_week).count()
    monthly_revenue = 0  # Заглушка, можно заменить на реальный подсчет

    # НОВАЯ ЛОГИКА: График регистраций (новых пользователей) за последние 7 дней
    registrations_data = []
    labels = []
    
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        labels.append(day.strftime('%d.%m'))  # Формат даты для оси X (например, "25.10")
        
        # Считаем пользователей, зарегистрированных именно в этот день
        count = User.query.filter(func.date(User.created_at) == day).count()
        registrations_data.append(count)

    # Данные для таблиц и форм
    recent_products = Product.query.order_by(Product.id.desc()).limit(5).all()
    categories = Category.query.all()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_products=total_products,
        total_categories=total_categories,
        users_last_week=users_last_week,
        products_last_week=products_last_week,
        monthly_revenue=monthly_revenue,
        recent_products=recent_products,
        categories=categories,
        visits_labels=labels,               # <-- Передаем даты в шаблон
        visits_data=registrations_data      # <-- Передаем количество регистраций в шаблон
    )

# ==================== ТОВАРЫ (полный CRUD) ====================

@admin_bp.route('/products')
def products_list():
    search = request.args.get('search', '')
    query = Product.query
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    products = query.order_by(Product.id.desc()).all()
    categories = Category.query.all()
    return render_template('admin/products.html', products=products, categories=categories, search=search)

@admin_bp.route('/products/add', methods=['POST'])
def product_add():
    name = request.form.get('name', '').strip()
    price = request.form.get('price', type=float)
    category_id = request.form.get('category_id', type=int)

    if not name or price is None or price < 0 or not category_id:
        flash('Ошибка: заполните все поля корректно', 'error')
        return redirect(url_for('admin.products_list'))

    new_product = Product(name=name, price=price, category_id=category_id)
    db.session.add(new_product)
    db.session.commit()
    flash(f'Товар "{name}" успешно добавлен!', 'success')
    return redirect(url_for('admin.products_list'))

@admin_bp.route('/products/<int:id>/edit', methods=['POST'])
def product_edit(id):
    product = Product.query.get_or_404(id)
    product.name = request.form.get('name', '').strip()
    product.price = request.form.get('price', type=float)
    product.category_id = request.form.get('category_id', type=int)

    if not product.name or product.price is None or product.price < 0:
        flash('Ошибка: некорректные данные', 'error')
        return redirect(url_for('admin.products_list'))

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
    return redirect(url_for('admin.products_list'))

# ==================== КАТЕГОРИИ (полный CRUD) ====================

@admin_bp.route('/categories')
def categories_list():
    search = request.args.get('search', '')
    query = Category.query
    if search:
        query = query.filter(Category.name.ilike(f'%{search}%'))
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
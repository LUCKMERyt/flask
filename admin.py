from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db, Product, Category, User, TestDB
from datetime import datetime, timedelta
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def get_trend(current, previous):
    """Вычисляет разницу и процент изменения"""
    diff = current - previous
    if previous == 0:
        percent = 100.0 if current > 0 else 0.0
    else:
        percent = round((diff / previous) * 100, 1)
    return diff, percent

# --- ДАШБОРД ---
@admin_bp.route('/')
@admin_bp.route('/dashboard')
def dashboard():
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)

    # Пользователи
    total_users = User.query.count()
    users_today = User.query.filter(func.date(User.created_at) == today).count()
    users_yesterday = User.query.filter(func.date(User.created_at) == yesterday).count()
    users_diff, users_pct = get_trend(users_today, users_yesterday)

    # Товары
    total_products = Product.query.count()
    products_week = Product.query.filter(func.date(Product.added_at) >= last_week).count()

    # Категории и TestDB
    total_categories = Category.query.count()
    total_test_records = TestDB.query.count()

    # Последние товары
    recent_products = Product.query.order_by(Product.id.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
        total_users=total_users,
        users_today=users_today,
        users_diff=users_diff,
        users_pct=users_pct,
        total_products=total_products,
        products_week=products_week,
        total_categories=total_categories,
        total_test_records=total_test_records,
        recent_products=recent_products
    )

# --- CRUD ДЛЯ ТОВАРОВ ---
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

    if not name or price is None or price < 0:
        flash('Ошибка: введите корректное название и цену', 'error')
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
    
    db.session.commit()
    flash(f'Товар "{product.name}" обновлен', 'success')
    return redirect(url_for('admin.products_list'))

@admin_bp.route('/products/<int:id>/delete', methods=['POST'])
def product_delete(id):
    product = Product.query.get_or_404(id)
    name = product.name
    db.session.delete(product)
    db.session.commit()
    flash(f'Товар "{name}" удален', 'success')
    return redirect(url_for('admin.products_list'))

# --- CRUD ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ---
@admin_bp.route('/users')
def users_list():
    search = request.args.get('search', '')
    query = User.query
    
    if search:
        query = query.filter(User.username.ilike(f'%{search}%'))
        
    users = query.order_by(User.id.desc()).all()
    return render_template('admin/users.html', users=users, search=search)

@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
def user_delete(id):
    user = User.query.get_or_404(id)
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'Пользователь "{username}" удален', 'success')
    return redirect(url_for('admin.users_list'))
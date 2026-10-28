from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Product, Category, User
from datetime import datetime, timedelta
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_bp.route('/dashboard')
def dashboard():
    today = datetime.now().date()
    last_week = today - timedelta(days=7)

    # Статистика
    total_users = User.query.count()
    total_products = Product.query.count()
    total_categories = Category.query.count()
    
    # Тренды (для примера: сравнение с прошлой неделей)
    users_last_week = User.query.filter(func.date(User.created_at) >= last_week).count()
    products_last_week = Product.query.filter(func.date(Product.added_at) >= last_week).count()
    
    # Заглушка для выручки (можно заменить на реальный подсчет, если есть модель заказов)
    monthly_revenue = 0 

    # Последние 5 товаров для таблицы
    recent_products = Product.query.order_by(Product.id.desc()).limit(5).all()
    
    # Категории нужны для выпадающего списка в модальном окне
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
        categories=categories
    )

@admin_bp.route('/products/add', methods=['POST'])
def product_add():
    name = request.form.get('name', '').strip()
    price = request.form.get('price', type=float)
    category_id = request.form.get('category_id', type=int)

    if not name or price is None or price < 0 or not category_id:
        flash('Ошибка: заполните все поля корректно', 'error')
        return redirect(url_for('admin.dashboard'))

    new_product = Product(name=name, price=price, category_id=category_id)
    db.session.add(new_product)
    db.session.commit()
    
    flash(f'Товар "{name}" успешно добавлен!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/products/<int:id>/delete', methods=['POST'])
def product_delete(id):
    product = Product.query.get_or_404(id)
    name = product.name
    db.session.delete(product)
    db.session.commit()
    flash(f'Товар "{name}" удален', 'success')
    return redirect(url_for('admin.dashboard'))
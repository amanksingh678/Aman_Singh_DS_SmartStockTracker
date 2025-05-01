from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from utils.db_manager import DatabaseManager
from utils.qr_handler import QRCodeHandler
import base64
from functools import wraps
import bcrypt
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Generate a secure secret key
db = DatabaseManager()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('signup'))
        
        # Check if user already exists
        if db.get_user_by_email(email):
            flash('Email already registered!', 'error')
            return redirect(url_for('signup'))
        
        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user
        if db.create_user(name, email, hashed_password):
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Error creating account. Please try again.', 'error')
            return redirect(url_for('signup'))
    
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember-me')
        
        user = db.get_user_by_email(email)
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            if remember:
                session.permanent = True
            return redirect(url_for('index'))
        
        flash('Invalid email or password!', 'error')
        return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    products = db.get_products()
    total_products = len(products)
    total_stock = products['quantity'].sum()
    total_value = (products['quantity'] * products['price']).sum()
    low_stock = len(db.get_low_stock_alerts())

    return render_template('index.html',
                         total_products=total_products,
                         total_stock=total_stock,
                         total_value=total_value,
                         low_stock=low_stock,
                         products=products.to_dict('records'))

@app.route('/inventory')
@login_required
def inventory():
    products = db.get_products()
    return render_template('inventory.html', products=products.to_dict('records'))

@app.route('/add_product', methods=['POST'])
@login_required
def add_product():
    try:
        name = request.form['name']
        sku_id = request.form['sku_id']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        min_threshold = int(request.form['min_threshold'])
        category = request.form.get('category', '')

        product_id = db.add_product(name, sku_id, quantity, price, min_threshold, category)
        return jsonify({'success': True, 'message': 'Product added successfully', 'product_id': product_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/product/<int:product_id>')
@login_required
def get_product(product_id):
    product = db.get_product(product_id)
    if product:
        return jsonify(product)
    return jsonify({'error': 'Product not found'}), 404

@app.route('/api/update-product/<int:product_id>', methods=['POST'])
@login_required
def update_product(product_id):
    try:
        updates = request.json
        if db.update_product(product_id, updates):
            return jsonify({'success': True, 'message': 'Product updated successfully'})
        return jsonify({'success': False, 'message': 'Product not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/delete-product/<int:product_id>', methods=['DELETE'])
@login_required
def delete_product(product_id):
    try:
        if db.delete_product(product_id):
            return jsonify({'success': True, 'message': 'Product deleted successfully'})
        return jsonify({'success': False, 'message': 'Product not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/qr-codes')
@login_required
def qr_codes():
    products = db.get_products()
    return render_template('qr_codes.html', products=products.to_dict('records'))

@app.route('/analytics')
@login_required
def analytics():
    products = db.get_products()
    transactions = db.get_transactions()
    return render_template('analytics.html',
                         products=products.to_dict('records'),
                         transactions=transactions.to_dict('records'))

@app.route('/api/generate-qr', methods=['POST'])
@login_required
def generate_qr():
    product_id = request.json.get('product_id')
    product = db.get_product(product_id)
    if product:
        product_data = {
            'id': int(product['id']),
            'name': product['name'],
            'sku_id': product['sku_id']
        }
        qr_code = QRCodeHandler.generate_qr_code(product_data)
        return jsonify({'qr_code': base64.b64encode(qr_code).decode()})
    return jsonify({'error': 'Product not found'}), 404

@app.route('/scanner')
@login_required
def scanner():
    return render_template('scanner.html')

@app.route('/api/update-inventory', methods=['POST'])
@login_required
def update_inventory():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity')
        transaction_type = data.get('type', 'Inbound')

        if not all([product_id, quantity]):
            return jsonify({'success': False, 'message': 'Missing required parameters'}), 400

        quantity_change = quantity if transaction_type == 'Inbound' else -quantity
        db.update_quantity(product_id, quantity_change, transaction_type)
        return jsonify({'success': True, 'message': 'Inventory updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    postal_code = db.Column(db.String(20))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add relationship to invoices
    invoices = db.relationship('Invoice', backref='customer', lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_type = db.Column(db.String(20), nullable=False)  # 'sale' or 'purchase'
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    discount_percentage = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, nullable=False)

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trend_days = db.Column(db.Integer, default=30)
    low_stock_threshold = db.Column(db.Integer, default=10)
    allow_date_edit = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    from sqlalchemy import func, desc
    from datetime import datetime, timedelta

    # Get settings
    settings = Settings.query.order_by(Settings.created_at.desc()).first()
    if not settings:
        settings = Settings()
        db.session.add(settings)
        db.session.commit()

    # Get current date and date N days ago
    today = datetime.utcnow().date()
    days_ago = today - timedelta(days=settings.trend_days)
    
    # Basic statistics
    total_items = Item.query.count()
    low_stock_items = Item.query.filter(Item.quantity < settings.low_stock_threshold).all()
    total_invoices = Invoice.query.count()
    
    # Sales statistics
    today_sales = db.session.query(func.sum(Invoice.total_amount))\
        .filter(Invoice.invoice_type == 'sale')\
        .filter(func.date(Invoice.date) == today)\
        .scalar() or 0
    
    # Monthly sales trend (last N days)
    daily_sales = db.session.query(
        func.date(Invoice.date).label('date'),
        func.sum(Invoice.total_amount).label('total')
    ).filter(
        Invoice.invoice_type == 'sale',
        Invoice.date >= days_ago
    ).group_by(
        func.date(Invoice.date)
    ).all()
    
    # Convert to list of dates and totals
    sales_dates = []
    sales_totals = []
    for sale in daily_sales:
        # Handle date as string since it comes from SQL date function
        date_str = str(sale.date)
        sales_dates.append(date_str)
        sales_totals.append(float(sale.total))
    
    # Top selling items (last N days)
    top_selling_items = db.session.query(
        Item.name,
        func.sum(InvoiceItem.quantity).label('total_quantity'),
        func.sum(InvoiceItem.quantity * InvoiceItem.price).label('total_revenue')
    ).join(InvoiceItem).join(Invoice).filter(
        Invoice.invoice_type == 'sale',
        Invoice.date >= days_ago
    ).group_by(Item.id).order_by(desc('total_quantity')).limit(5).all()
    
    # Recent activities
    recent_activities = []
    recent_invoices = Invoice.query.order_by(Invoice.date.desc()).limit(10).all()
    for invoice in recent_invoices:
        activity = {
            'id': invoice.id,
            'type': invoice.invoice_type,
            'date': invoice.date.strftime('%Y-%m-%d %H:%M') if invoice.date else '',
            'amount': invoice.total_amount
        }
        recent_activities.append(activity)

    # Calculate total inventory value
    total_inventory_value = db.session.query(
        func.sum(Item.quantity * Item.price)
    ).scalar() or 0
    
    # Get sales vs purchases comparison for chart
    sales_vs_purchases = db.session.query(
        Invoice.invoice_type,
        func.sum(Invoice.total_amount).label('total')
    ).filter(
        Invoice.date >= days_ago
    ).group_by(Invoice.invoice_type).all()
    
    sales_amount = 0
    purchases_amount = 0
    for invoice_type, total in sales_vs_purchases:
        if invoice_type == 'sale':
            sales_amount = float(total)
        else:
            purchases_amount = float(total)
    
    return render_template('dashboard.html',
                         settings=settings,
                         today_sales=today_sales,
                         total_items=total_items,
                         total_invoices=total_invoices,
                         total_inventory_value=total_inventory_value,
                         sales_dates=sales_dates,
                         sales_totals=sales_totals,
                         top_selling_items=top_selling_items,
                         recent_activities=recent_activities,
                         low_stock_items=low_stock_items,
                         sales_amount=sales_amount,
                         purchases_amount=purchases_amount)

@app.route('/items')
@login_required
def items():
    items_list = Item.query.all()
    return render_template('items.html', items=items_list)

@app.route('/items/json')
@login_required
def get_items_json():  
    items = Item.query.all()
    return jsonify([{
        'id': item.id,
        'name': item.name,
        'price': item.price,
        'quantity': item.quantity,
        'description': item.description
    } for item in items])

@app.route('/items/add', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        quantity = int(request.form.get('quantity'))
        
        item = Item(name=name, description=description, price=price, quantity=quantity)
        db.session.add(item)
        db.session.commit()
        flash('Item added successfully')
        return redirect(url_for('items'))
    return render_template('add_item.html')

@app.route('/invoices')
@login_required
def invoices():
    invoices_list = Invoice.query.order_by(Invoice.date.desc()).all()
    return render_template('invoices.html', invoices=invoices_list)

@app.route('/new_invoice/<type>', methods=['GET', 'POST'])
@login_required
def new_invoice(type):
    if type not in ['sale', 'purchase']:
        flash('Invalid invoice type')
        return redirect(url_for('dashboard'))

    settings = Settings.query.order_by(Settings.created_at.desc()).first()
    if not settings:
        settings = Settings()
        db.session.add(settings)
        db.session.commit()
    
    if request.method == 'POST':
        try:
            print("Received POST request for new invoice:", request.json)
            items_data = request.json.get('items', [])
            if not items_data:
                return jsonify({'success': False, 'error': 'No items added to invoice'})

            subtotal = sum(item['price'] * item['quantity'] for item in items_data)
            discount_percentage = float(request.json.get('discount_percentage', 0))
            discount_amount = subtotal * (discount_percentage / 100)
            total_amount = subtotal - discount_amount
            
            # Handle custom date if allowed
            invoice_date = datetime.utcnow()
            if settings.allow_date_edit and request.json.get('invoice_date'):
                try:
                    invoice_date = datetime.strptime(request.json.get('invoice_date'), '%Y-%m-%dT%H:%M')
                except ValueError:
                    print("Error parsing date:", request.json.get('invoice_date'))
            
            customer_id = request.json.get('customer_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer not selected'})
            
            invoice = Invoice(
                invoice_type=type,
                date=invoice_date,
                customer_id=customer_id,
                subtotal=subtotal,
                discount_percentage=discount_percentage,
                discount_amount=discount_amount,
                total_amount=total_amount
            )
            db.session.add(invoice)
            db.session.flush()
            
            for item_data in items_data:
                item = Item.query.get(item_data['item_id'])
                if not item:
                    return jsonify({'success': False, 'error': f'Item {item_data["id"]} not found'})
                
                if type == 'sale' and item.quantity < item_data['quantity']:
                    return jsonify({'success': False, 'error': f'Insufficient stock for {item.name}. Only {item.quantity} available.'})
                
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    item_id=item.id,
                    quantity=item_data['quantity'],
                    price=item_data['price']
                )
                db.session.add(invoice_item)
                
                if type == 'sale':
                    item.quantity -= item_data['quantity']
                else:
                    item.quantity += item_data['quantity']
            
            db.session.commit()
            print(f"Invoice {invoice.id} created successfully with date {invoice_date}")
            return jsonify({'success': True, 'redirect': url_for('invoices')})
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating invoice: {str(e)}")
            return jsonify({'success': False, 'error': str(e)})
    
    # GET request
    items = Item.query.all()
    customers = Customer.query.all()
    current_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M') if settings.allow_date_edit else datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    return render_template('new_invoice.html',
                         invoice_type=type,
                         items=items,
                         customers=customers,
                         settings=settings,
                         current_date=current_date)

@app.route('/invoice/view/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice_items = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
    items_details = []
    for invoice_item in invoice_items:
        item = Item.query.get(invoice_item.item_id)
        items_details.append({
            'name': item.name,
            'quantity': invoice_item.quantity,
            'price': invoice_item.price,
            'total': invoice_item.quantity * invoice_item.price
        })
    return render_template('view_invoice.html', invoice=invoice, items=items_details)

@app.route('/invoice/delete/<int:invoice_id>', methods=['POST'])
@login_required
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    # Delete related invoice items first
    InvoiceItem.query.filter_by(invoice_id=invoice_id).delete()
    db.session.delete(invoice)
    db.session.commit()
    flash('Invoice deleted successfully!', 'success')
    return redirect(url_for('invoices'))

@app.route('/item/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    if request.method == 'POST':
        item.name = request.form['name']
        item.description = request.form['description']
        item.price = float(request.form['price'])
        item.quantity = int(request.form['quantity'])
        db.session.commit()
        flash('Item updated successfully!', 'success')
        return redirect(url_for('items'))
    return render_template('edit_item.html', item=item)

@app.route('/item/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    # Check if item is used in any invoice
    if InvoiceItem.query.filter_by(item_id=item_id).first():
        flash('Cannot delete item as it is used in invoices!', 'error')
        return redirect(url_for('items'))
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('items'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    settings = Settings.query.order_by(Settings.created_at.desc()).first()
    if not settings:
        settings = Settings()
        db.session.add(settings)
        db.session.commit()
    
    if request.method == 'POST':
        settings.trend_days = int(request.form.get('trend_days', 30))
        settings.low_stock_threshold = int(request.form.get('low_stock_threshold', 10))
        settings.allow_date_edit = 'allow_date_edit' in request.form
        db.session.commit()
        flash('Settings updated successfully')
        return redirect(url_for('settings'))
    
    return render_template('settings.html', settings=settings)

@app.route('/customers')
@login_required
def customers():
    customers_list = Customer.query.order_by(Customer.created_at.desc()).all()
    return render_template('customers.html', customers=customers_list)

@app.route('/customer/new', methods=['GET', 'POST'])
@login_required
def new_customer():
    if request.method == 'POST':
        try:
            # Generate a unique customer code
            last_customer = Customer.query.order_by(Customer.id.desc()).first()
            next_id = (last_customer.id + 1) if last_customer else 1
            customer_code = f"CUST{next_id:04d}"
            
            customer = Customer(
                code=customer_code,
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                address=request.form.get('address'),
                city=request.form.get('city'),
                state=request.form.get('state'),
                postal_code=request.form.get('postal_code'),
                notes=request.form.get('notes')
            )
            db.session.add(customer)
            db.session.commit()
            flash('Customer added successfully!')
            return redirect(url_for('customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding customer: {str(e)}')
    
    return render_template('new_customer.html')

@app.route('/customer/edit/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        try:
            customer.first_name = request.form['first_name']
            customer.last_name = request.form['last_name']
            customer.email = request.form.get('email')
            customer.phone = request.form.get('phone')
            customer.address = request.form.get('address')
            customer.city = request.form.get('city')
            customer.state = request.form.get('state')
            customer.postal_code = request.form.get('postal_code')
            customer.notes = request.form.get('notes')
            
            db.session.commit()
            flash('Customer updated successfully!')
            return redirect(url_for('customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating customer: {str(e)}')
    
    return render_template('edit_customer.html', customer=customer)

@app.route('/customer/view/<int:customer_id>')
@login_required
def view_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    return render_template('view_customer.html', customer=customer)

@app.route('/customer/delete/<int:customer_id>', methods=['POST'])
@login_required
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    try:
        db.session.delete(customer)
        db.session.commit()
        flash('Customer deleted successfully!')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting customer: {str(e)}')
    return redirect(url_for('customers'))

@app.route('/customers/search')
@login_required
def search_customers():
    query = request.args.get('q', '')
    customers = Customer.query.filter(
        db.or_(
            Customer.code.ilike(f'%{query}%'),
            Customer.first_name.ilike(f'%{query}%'),
            Customer.last_name.ilike(f'%{query}%'),
            Customer.email.ilike(f'%{query}%'),
            Customer.phone.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    return jsonify([{
        'id': c.id,
        'code': c.code,
        'full_name': c.full_name,
        'email': c.email,
        'phone': c.phone
    } for c in customers])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=80, debug=True)

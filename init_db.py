from app import app, db, Item, Invoice, InvoiceItem, User, Settings, Customer
from datetime import datetime
from werkzeug.security import generate_password_hash

def init_db():
    with app.app_context():
        # Create tables
        db.create_all()

        # Create default user
        user = User(username='admin')
        user.set_password('admin')
        db.session.add(user)

        # Create sample items
        items = [
            Item(
                name='Sample Item 1',
                description='This is a sample item',
                price=15.99,
                quantity=100,
                created_at=datetime.utcnow()
            ),
            Item(
                name='Sample Item 2',
                description='This is another sample item',
                price=31.25,
                quantity=50,
                created_at=datetime.utcnow()
            )
        ]
        db.session.add_all(items)

        # Create default customer
        customer = Customer(
            code='CUST0001',
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='123-456-7890',
            address='123 Main St',
            city='Sample City',
            state='ST',
            postal_code='12345'
        )
        db.session.add(customer)
        db.session.flush()  # This will assign an ID to the customer

        # Create sample invoice
        invoice = Invoice(
            invoice_type='sale',
            date=datetime.utcnow(),
            customer_id=customer.id,  # Use the customer we just created
            subtotal=47.24,
            discount_percentage=10,
            discount_amount=4.72,
            total_amount=42.52
        )
        db.session.add(invoice)
        db.session.flush()

        # Create invoice items
        invoice_items = [
            InvoiceItem(
                invoice_id=invoice.id,
                item_id=items[0].id,
                quantity=1,
                price=items[0].price
            ),
            InvoiceItem(
                invoice_id=invoice.id,
                item_id=items[1].id,
                quantity=1,
                price=items[1].price
            )
        ]
        db.session.add_all(invoice_items)

        # Create default settings
        settings = Settings(allow_date_edit=True)
        db.session.add(settings)

        # Commit all changes
        db.session.commit()

        print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()

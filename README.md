# Shop Management System

A comprehensive web-based shop management system built with Python Flask, designed to help small to medium-sized businesses manage their inventory, customers, and invoices efficiently.

## 🚀 Features

- **Dashboard**: Get an overview of your business metrics and recent activities
- **Inventory Management**: 
  - Add, edit, and track items
  - Monitor stock levels
  - Manage product details and pricing
- **Customer Management**:
  - Store and manage customer information
  - View customer purchase history
  - Edit customer details
- **Invoice System**:
  - Create and manage invoices
  - Track payment status
  - Generate detailed invoice views
- **User Authentication**:
  - Secure login system
  - User session management

## 🛠️ Technologies Used

- **Backend**: Python Flask
- **Database**: SQLite
- **Frontend**: HTML, Bootstrap
- **Authentication**: Flask-Login

## ⚙️ Setup and Installation

1. Clone the repository:
```bash
git clone [your-repository-url]
cd [repository-name]
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python init_db.py
```

4. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 💻 Usage

1. Login to the system using your credentials
2. Navigate through different sections using the sidebar menu:
   - Dashboard for overview
   - Items for inventory management
   - Customers for customer management
   - Invoices for invoice creation and management
   - Settings for system configuration

## 🔐 Security Features

- Password hashing for user authentication
- Session management
- Protected routes requiring authentication

## 🤝 Contributing

Feel free to fork this repository and submit pull requests. You can also open issues for any bugs found or feature suggestions.

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

---
Created with ❤️ for small business owners

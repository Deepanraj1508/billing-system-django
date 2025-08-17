# Django Billing System

A comprehensive billing management system built with Django that handles product management, bill generation, tax calculations, denomination management, and customer purchase history.

## 🚀 Features

- **Product Management**: Create, read, update, and delete products with stock tracking
- **Product Search**: Real-time product search with autocomplete suggestions
- **Dynamic Billing**: Add multiple products to bills with automatic tax calculations
- **Denomination Management**: Track available cash denominations for change calculations
- **Change Breakdown**: Automatically calculate optimal change distribution
- **Email Invoices**: Send professional invoices to customers via email
- **Purchase History**: Track and view customer purchase history
- **Admin Panel**: Full Django admin integration
- **REST API**: Integration endpoints for automation

## 📋 Requirements

- Python 3.1+
- Django 5.2+
- SQLite (default) or MySQL

## 🛠️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Deepanraj1508/billing-system-django.git
cd billing-system-django
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Credentials Setup

Create a **.env file** in the project root directory and add the following environment variables:

```bash
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = '587'
DEFAULT_FROM_EMAIL = ''
```

### 5. Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

### 7. Seed Sample Data

```bash
python create_sample_data.py
```

### 8. Run Development Server

```bash
python manage.py runserver
```

### 8. Access the Application

- **Main Application**: http://127.0.0.1:8000/
- **Admin Panel**: http://127.0.0.1:8000/admin/

## 📊 System Architecture

### Project Flow Diagram

View the complete system flow: [Flow Diagram](https://github.com/Deepanraj1508/billing-system-django/blob/main/Flow%20Diagram.png)

### Database Schema

View the entity relationship diagram: [ER Diagram](https://github.com/Deepanraj1508/billing-system-django/blob/main/ER%20Diagram.png)

## ⚙️ Core Features

### Product Management

- CRUD operations with stock tracking
- Tax percentage configuration per product
- Inventory management with automatic stock updates

### Dynamic Billing System

- Multi-product bill creation
- Automatic tax calculations
- Real-time change calculation and denomination breakdown
- Customer information management

### Denomination Management

- Track available cash denominations
- Optimal change distribution using greedy algorithm
- Real-time denomination updates

### Email Integration

- Automated invoice generation
- Email delivery to customers
- Professional invoice templates

### Purchase History

- Customer purchase tracking
- Detailed transaction history
- Search and filter capabilities

## 📝 System Assumptions

1. **Currency**: All prices are in Indian Rupees (₹)
2. **Email Backend**: Console backend for development, SMTP for production
3. **Tax Calculation**: Individual tax percentages per product
4. **Stock Management**: Automatic stock decrementation on purchases
5. **Change Algorithm**: Greedy algorithm for optimal denomination breakdown
6. **Database**: SQLite for development, configurable for MySQL
7. **Authentication**: No user authentication (extendable as needed)

## 🧪 Testing

Run the test suite:

```bash
python manage.py test
```

# Django Billing System

A comprehensive billing management system built with Django that handles product management, bill generation, tax calculations, denomination management, and customer purchase history.

## Features

- **Product Management**: Create, read, update, and delete products with stock tracking
- **Dynamic Billing**: Add multiple products to bills with automatic tax calculations
- **Denomination Management**: Track available cash denominations for change calculations
- **Change Breakdown**: Automatically calculate optimal change distribution
- **Email Invoices**: Send professional invoices to customers via email
- **Purchase History**: Track and view customer purchase history
- **Responsive UI**: Modern Bootstrap-based interface
- **Admin Panel**: Full Django admin integration

## Requirements

- Python 3.1+
- Django 5.2+
- SQLite (default) or MySQL

## Installation and Setup

1. **Clone/Download the project files**

   ```bash
   https://github.com/Deepanraj1508/billing-system-django.git
   ```
2. **Create virtual environment**

   ```bash
   python -m venv venv

   # On Windows
   venv\Scripts\activate

   # On macOS/Linux
   source venv/bin/activate
   ```
3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```
4. **Project Structure**

   billing_system/
   ├── billing_project/
   │   ├── __init__.py
   │   ├── settings.py
   │   ├── urls.py
   │   └── wsgi.py
   ├── billing/
   │   ├── __init__.py
   │   ├── admin.py
   │   ├── apps.py
   │   ├── forms.py
   │   ├── models.py
   │   ├── urls.py
   │   ├── utils.py
   │   ├── views.py
   │   ├── migrations/
   ├── templates/
   │   ├── base.html
   │   └── billing/
   │       ├── billing.html
   │       ├── home.html
   │       ├── purchase_history.html
   │       ├── purchase_detail.html
   │       ├── product_list.html
   │       ├── product_form.html
   │       ├── product_confirm_delete.html
   │       ├── denomination_list.html
   │       ├── denomination_form.html
   │       ├── denomination_confirm_delete.html
   │       └── email_invoice.html
   ├── manage.py
   └── requirements.txt
5. **Run migrations**

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
6. **Create superuser**

   ```bash
   python manage.py createsuperuser
   ```
7. **Seed initial data**

   ```bash
   python create_sample_data.py
   ```
8. **Run the development server**

   ```bash
   python manage.py runserver
   ```
9. **Access the application**

   - Main Application: http://127.0.0.1:8000/
   - Admin Panel: http://127.0.0.1:8000/admin/

## Usage

### 1. Product Management

- Navigate to "Management > Products" to add/edit products
- Each product requires: Product ID, Name, Stock, Price, Tax percentage
- Stock is automatically updated when products are sold

### 2. Denomination Management

- Navigate to "Management > Denominations" to manage cash denominations
- Set available counts for each denomination (₹500, ₹100, ₹50, etc.)
- These are used for change calculations

### 3. Creating Bills

- Go to "Billing" page
- Enter customer email
- Add products using "Add New Product" button
- Select products and quantities
- Update denomination counts if needed
- Enter amount paid
- Click "Generate Bill" to process

### 4. Features of Bill Generation

- Automatic tax calculations per product
- Stock validation and updates
- Change calculation with optimal denomination breakdown
- Professional invoice generation
- Email delivery to customer
- Purchase record creation

### 5. Purchase History

- Enter customer email to view their purchase history
- Click on any purchase to view detailed breakdown
- See items purchased, payment details, and change breakdown

## Email Configuration

For production, update the email settings in `settings.py`:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'your-email@gmail.com'
```

For development, the system uses console backend (emails printed to console).

## Database Models

### Product

- `product_id`: Unique identifier
- `name`: Product name
- `available_stock`: Current stock count
- `price_per_unit`: Unit price
- `tax_percentage`: Tax rate

### Purchase

- `purchase_id`: UUID for each purchase
- `customer_email`: Customer email address
- `total_amount`: Pre-tax total
- `tax_amount`: Total tax amount
- `grand_total`: Final amount
- `amount_paid`: Amount received from customer
- `change_amount`: Change given

### PurchaseItem

- Links products to purchases with quantities and calculations

### Denomination

- `value`: Denomination value (₹500, ₹100, etc.)
- `count`: Available count in shop

### ChangeBreakdown

- Records how change was distributed for each purchase

## API Endpoints

- `/api/product/<product_id>/` - Get product information
- `/api/generate-bill/` - Process bill generation (POST)

## Assumptions Made

1. **Currency**: All prices are in Indian Rupees (₹)
2. **Email Backend**: Uses console backend for development (configure SMTP for production)
3. **Tax Calculation**: Tax is calculated per product based on individual tax percentages
4. **Stock Management**: Stock is automatically decremented on successful purchases
5. **Change Algorithm**: Uses greedy algorithm for optimal denomination breakdown
6. **Database**: SQLite for development (easily configurable for MySQL)
7. **Authentication**: No user authentication implemented (can be added as needed)

## Production Considerations

1. **Security**: Change `SECRET_KEY` and set `DEBUG = False`
2. **Database**: Use PostgreSQL or MySQL for production
3. **Email**: Configure proper SMTP settings
4. **Static Files**: Configure static file serving
5. **Error Handling**: Implement proper logging and error monitoring
6. **Backup**: Regular database backups
7. **SSL**: Use HTTPS in production

### Common Issues

1. **Migration Errors**: Delete db.sqlite3 and migrations, then remake migrations
2. **Template Errors**: Ensure templates directory is correctly configured
3. **Static Files**: Run `python manage.py collectstatic` for production
4. **Email Issues**: Check SMTP settings and credentials

### Running Tests

```bash
python manage.py test
```

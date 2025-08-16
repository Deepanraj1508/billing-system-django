from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from decimal import Decimal, ROUND_HALF_UP
import json
from .models import Product, Denomination, Purchase, PurchaseItem, ChangeBreakdown
from .forms import BillingForm, ProductForm, DenominationForm
from .utils import (
    calculate_exact_change_greedy, 
    update_shop_drawer_from_customer_payment,
    update_shop_drawer_in_database,
    get_shop_drawer_status,
    validate_customer_payment,
    calculate_optimal_change_denominations
)

def home(request):
    return render(request, 'billing/home.html')

def billing_page(request):
    form = BillingForm()
    products = Product.objects.all()
    denominations = Denomination.objects.all().order_by('-value')
    
    context = {
        'form': form,
        'products': products,
        'denominations': denominations,
    }
    return render(request, 'billing/billing.html', context)

def get_product_info(request, product_id):
    try:
        product = Product.objects.get(product_id=product_id)
        return JsonResponse({
            'success': True,
            'name': product.name,
            'price': float(product.price_per_unit),
            'tax': float(product.tax_percentage),
            'stock': product.available_stock
        })
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Product not found'
        })

@csrf_exempt
def generate_bill(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer_email = data.get('customer_email')
            amount_paid = Decimal(str(data.get('amount_paid', 0)))
            products_data = data.get('products', [])
            denominations_data = data.get('denominations', {})
            customer_payment_denominations = data.get('customer_payment_denominations', {})
            
            # Validate email
            if not customer_email:
                return JsonResponse({'success': False, 'error': 'Customer email is required'})
            
            # Calculate totals
            total_amount = Decimal('0.00')
            tax_amount = Decimal('0.00')
            purchase_items = []
            
            with transaction.atomic():
                # Create purchase record
                purchase = Purchase.objects.create(
                    customer_email=customer_email,
                    total_amount=Decimal('0.00'),  # Will update after calculations
                    tax_amount=Decimal('0.00'),
                    grand_total=Decimal('0.00'),
                    amount_paid=amount_paid
                )
                
                # Process each product
                for item in products_data:
                    product_id = item.get('product_id')
                    quantity = int(item.get('quantity', 0))
                    
                    if quantity <= 0:
                        continue
                        
                    try:
                        product = Product.objects.select_for_update().get(product_id=product_id)
                        
                        if product.available_stock < quantity:
                            return JsonResponse({
                                'success': False, 
                                'error': f'Insufficient stock for {product.name}. Available: {product.available_stock}'
                            })
                        
                        # Calculate item totals
                        item_subtotal = product.price_per_unit * quantity
                        item_tax = (item_subtotal * product.tax_percentage) / 100
                        
                        total_amount += item_subtotal
                        tax_amount += item_tax
                        
                        # Create purchase item
                        PurchaseItem.objects.create(
                            purchase=purchase,
                            product=product,
                            quantity=quantity,
                            unit_price=product.price_per_unit,
                            tax_percentage=product.tax_percentage,
                            subtotal=item_subtotal
                        )
                        
                        # Update product stock
                        product.available_stock -= quantity
                        product.save()
                        
                        purchase_items.append({
                            'name': product.name,
                            'product_id': product.product_id,
                            'quantity': quantity,
                            'unit_price': float(product.price_per_unit),
                            'tax_percentage': float(product.tax_percentage),
                            'subtotal': float(item_subtotal),
                            'tax_amount': float(item_tax)
                        })
                        
                    except Product.DoesNotExist:
                        return JsonResponse({'success': False, 'error': f'Product {product_id} not found'})
                
                # Calculate grand total and ROUND IT to nearest rupee
                grand_total = total_amount + tax_amount
                # Round to nearest rupee (whole number) - this ensures no decimal change amounts
                grand_total = grand_total.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                
                # Get available denominations from shop drawer
                available_denominations = list(Denomination.objects.all())
                
                # Handle customer payment denominations
                total_customer_payment = Decimal('0.00')
                if customer_payment_denominations:
                    # Calculate total from customer denominations
                    for denomination_value, count in customer_payment_denominations.items():
                        if count > 0:
                            total_customer_payment += Decimal(str(denomination_value)) * count
                    
                    # Update amount paid to match customer denominations
                    amount_paid = total_customer_payment
                    purchase.amount_paid = amount_paid
                else:
                    # If no customer denominations specified, use the amount_paid field
                    total_customer_payment = amount_paid
                
                # Validate customer payment
                if total_customer_payment < grand_total:
                    return JsonResponse({'success': False, 'error': 'Insufficient payment amount'})
                
                # Calculate exact change needed based on ROUNDED bill amount
                change_amount = total_customer_payment - grand_total
                # Ensure change amount is also rounded to avoid decimal issues
                change_amount = change_amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                
                # Update purchase totals with rounded amounts
                purchase.total_amount = total_amount
                purchase.tax_amount = tax_amount
                purchase.grand_total = grand_total  # Rounded amount
                purchase.change_amount = change_amount
                purchase.save()
                
                # IMPORTANT CHANGE 1: Only update shop drawer when bill is successfully generated
                # Update shop drawer with customer payment denominations ONLY after successful bill generation
                if customer_payment_denominations:
                    updated_denominations = update_shop_drawer_from_customer_payment(customer_payment_denominations)
                
                # Step 2: Update available denominations (shop drawer management)
                for denomination_value, count in denominations_data.items():
                    if count > 0:
                        denomination = Denomination.objects.get(value=Decimal(denomination_value))
                        denomination.count = int(count)
                        denomination.save()
                
                # Step 3: Calculate change breakdown using greedy algorithm based on ROUNDED amount
                change_breakdown = []
                total_change_given = Decimal('0.00')
                
                if change_amount > 0:
                    # Get updated shop drawer status after customer payment
                    updated_available_denominations = list(Denomination.objects.all())
                    
                    # Debug: Print change amount and available denominations
                    print(f"DEBUG: Change amount: {change_amount}, Type: {type(change_amount)}")
                    print(f"DEBUG: Available denominations: {[(d.value, d.count) for d in updated_available_denominations]}")
                    
                    # Calculate exact change using greedy algorithm based on ROUNDED change amount
                    change_breakdown, total_change_given = calculate_exact_change_greedy(
                        change_amount, 
                        updated_available_denominations
                    )
                    
                    # Debug: Print change breakdown
                    print(f"DEBUG: Change breakdown: {change_breakdown}")
                    print(f"DEBUG: Total change given: {total_change_given}")
                    
                    # Save change breakdown to database
                    for breakdown_item in change_breakdown:
                        if breakdown_item['count'] > 0:
                            ChangeBreakdown.objects.create(
                                purchase=purchase,
                                denomination_value=breakdown_item['value'],
                                count=breakdown_item['count']
                            )
                
                # Send email (asynchronously in production)
                send_invoice_email(purchase, purchase_items, change_breakdown)
                
                # Get updated denomination counts
                available_denominations_dict = {}
                for denomination in Denomination.objects.all():
                    available_denominations_dict[str(denomination.value)] = denomination.count
                
                # Get final shop drawer status after transaction
                final_drawer_status = get_shop_drawer_status()
                
                return JsonResponse({
                    'success': True,
                    'purchase_id': str(purchase.purchase_id),
                    'total_amount': float(total_amount),
                    'tax_amount': float(tax_amount),
                    'grand_total': float(grand_total),  # Rounded amount
                    'amount_paid': float(amount_paid),
                    'change_amount': float(change_amount),
                    'items': purchase_items,
                    'change_breakdown': change_breakdown,
                    'available_denominations': available_denominations_dict,
                    'customer_payment_denominations': customer_payment_denominations,
                    'total_customer_payment': float(total_customer_payment),
                    'total_change_given': float(total_change_given),
                    'shop_drawer_status': final_drawer_status,
                    'transaction_summary': {
                        'customer_paid': float(total_customer_payment),
                        'bill_amount': float(grand_total),  # Rounded amount
                        'change_given': float(change_amount),
                        'denominations_used_for_change': len(change_breakdown)
                    }
                })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def update_drawer_realtime(request):
    """Update shop drawer denominations in real-time as customer enters denominations
    NOTE: This function now only updates the display, NOT the database.
    Database updates happen only when the bill is successfully generated."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer_denominations = data.get('customer_denominations', {})
            
            # IMPORTANT CHANGE: Do NOT update database in real-time
            # Only calculate what the drawer would look like for display purposes
            # The actual database update happens only when generate_bill is called
            
            # Get current shop drawer status (unchanged)
            current_drawer_status = get_shop_drawer_status()
            
            # Calculate what the drawer would look like after customer payment (for display only)
            projected_drawer_status = {}
            for denomination_value, drawer_info in current_drawer_status.items():
                customer_count = int(customer_denominations.get(denomination_value, 0))
                projected_drawer_status[denomination_value] = {
                    'value': drawer_info['value'],
                    'count': drawer_info['count'] + customer_count,  # Projected count
                    'total_value': drawer_info['value'] * (drawer_info['count'] + customer_count)
                }
            
            return JsonResponse({
                'success': True,
                'message': 'Display updated (database will be updated when bill is generated)',
                'customer_denominations': customer_denominations,
                'current_drawer_status': current_drawer_status,  # Actual current status
                'projected_drawer_status': projected_drawer_status,  # What it would look like
                'note': 'Database will be updated only when bill is successfully generated'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def send_invoice_email(purchase, items, change_breakdown):
    subject = f'Invoice - Purchase {purchase.purchase_id}'
    html_message = render_to_string('billing/email_invoice.html', {
        'purchase': purchase,
        'items': items,
        'change_breakdown': change_breakdown
    })
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [purchase.customer_email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Email sending failed: {e}")

def purchase_history(request):
    email = request.GET.get('email', '')
    purchases = []
    
    if email:
        purchases = Purchase.objects.filter(customer_email=email).prefetch_related('items__product')
    
    context = {
        'email': email,
        'purchases': purchases,
    }
    return render(request, 'billing/purchase_history.html', context)

def purchase_detail(request, purchase_id):
    purchase = get_object_or_404(Purchase, purchase_id=purchase_id)
    return render(request, 'billing/purchase_detail.html', {'purchase': purchase})

# Product Management Views
def product_list(request):
    products = Product.objects.all()
    return render(request, 'billing/product_list.html', {'products': products})

def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product created successfully!')
            return redirect('product_list')
    else:
        form = ProductForm()
    
    return render(request, 'billing/product_form.html', {'form': form, 'title': 'Add Product'})

def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'billing/product_form.html', {'form': form, 'title': 'Edit Product'})

def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('product_list')
    
    return render(request, 'billing/product_confirm_delete.html', {'product': product})

# Denomination Management Views
def denomination_list(request):
    denominations = Denomination.objects.all().order_by('-value')
    return render(request, 'billing/denomination_list.html', {'denominations': denominations})

def denomination_create(request):
    if request.method == 'POST':
        form = DenominationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Denomination created successfully!')
            return redirect('denomination_list')
    else:
        form = DenominationForm()
    
    return render(request, 'billing/denomination_form.html', {'form': form, 'title': 'Add Denomination'})

def denomination_edit(request, pk):
    denomination = get_object_or_404(Denomination, pk=pk)
    
    if request.method == 'POST':
        form = DenominationForm(request.POST, instance=denomination)
        if form.is_valid():
            form.save()
            messages.success(request, 'Denomination updated successfully!')
            return redirect('denomination_list')
    else:
        form = DenominationForm(instance=denomination)
    
    return render(request, 'billing/denomination_form.html', {'form': form, 'title': 'Edit Denomination'})

def denomination_delete(request, pk):
    denomination = get_object_or_404(Denomination, pk=pk)
    
    if request.method == 'POST':
        denomination.delete()
        messages.success(request, 'Denomination deleted successfully!')
        return redirect('denomination_list')
    
    return render(request, 'billing/denomination_confirm_delete.html', {'denomination': denomination})

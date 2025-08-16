from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Q
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
    denominations = Denomination.objects.all().order_by('-value')
    
    context = {
        'form': form,
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

def search_products(request):
    """API endpoint for product search/autocomplete"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({
            'success': True,
            'products': []
        })
    
    # Search in product_id and name fields
    products = Product.objects.filter(
        Q(product_id__icontains=query) | 
        Q(name__icontains=query)
    ).filter(available_stock__gt=0).order_by('name')[:10]  # Limit to 10 results
    
    product_list = []
    for product in products:
        product_list.append({
            'id': product.product_id,
            'text': f"{product.product_id} - {product.name}",
            'name': product.name,
            'price': float(product.price_per_unit),
            'tax': float(product.tax_percentage),
            'stock': product.available_stock
        })
    
    return JsonResponse({
        'success': True,
        'products': product_list
    })

@csrf_exempt
def generate_bill(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer_email = data.get('customer_email')
            amount_paid = data.get('amount_paid', 0)
            products_data = data.get('products', [])
            denominations_data = data.get('denominations', {})
            customer_payment_denominations = data.get('customer_payment_denominations', {})
            
            print(f"DEBUG: Raw customer_payment_denominations: {customer_payment_denominations}")
            print(f"DEBUG: Type of customer_payment_denominations: {type(customer_payment_denominations)}")
            
            # ========== COMPREHENSIVE VALIDATION SECTION ==========
            
            # 1. Validate customer email
            if not customer_email:
                return JsonResponse({
                    'success': False, 
                    'error': 'Customer email is required. Please enter a valid email address.'
                })
            
            # Validate email format
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, customer_email):
                return JsonResponse({
                    'success': False, 
                    'error': 'Please enter a valid email address format (e.g., customer@example.com)'
                })
            
            # 2. Validate products data
            if not products_data:
                return JsonResponse({
                    'success': False, 
                    'error': 'No products selected. Please add at least one product to generate a bill.'
                })
            
            # 3. Validate amount paid
            try:
                amount_paid = Decimal(str(amount_paid))
                if amount_paid < 0:
                    return JsonResponse({
                        'success': False, 
                        'error': 'Amount paid cannot be negative. Please enter a valid amount.'
                    })
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False, 
                    'error': 'Invalid amount paid. Please enter a valid numeric amount.'
                })
            
            # 4. Validate customer payment denominations
            if customer_payment_denominations:
                for denomination_value, count in customer_payment_denominations.items():
                    try:
                        count = int(count)
                        if count < 0:
                            return JsonResponse({
                                'success': False, 
                                'error': f'Invalid denomination count for ₹{denomination_value}. Count cannot be negative.'
                            })
                    except (ValueError, TypeError):
                        return JsonResponse({
                            'success': False, 
                            'error': f'Invalid denomination count for ₹{denomination_value}. Please enter a valid number.'
                        })
            
            # 5. Validate shop drawer denominations
            if denominations_data:
                for denomination_value, count in denominations_data.items():
                    try:
                        count = int(count)
                        if count < 0:
                            return JsonResponse({
                                'success': False, 
                                'error': f'Invalid shop drawer denomination count for ₹{denomination_value}. Count cannot be negative.'
                            })
                    except (ValueError, TypeError):
                        return JsonResponse({
                            'success': False, 
                            'error': f'Invalid shop drawer denomination count for ₹{denomination_value}. Please enter a valid number.'
                        })
            
            # Calculate totals
            total_amount = Decimal('0.00')
            tax_amount = Decimal('0.00')
            purchase_items = []
            
            with transaction.atomic():
                print(f"DEBUG: Starting transaction for bill generation")
                # Create purchase record
                purchase = Purchase.objects.create(
                    customer_email=customer_email,
                    total_amount=Decimal('0.00'),  # Will update after calculations
                    tax_amount=Decimal('0.00'),
                    grand_total=Decimal('0.00'),
                    amount_paid=amount_paid
                )
                
                # First pass: Validate stock and collect product data
                products_to_process = []
                valid_products_count = 0
                
                for item in products_data:
                    product_id = item.get('product_id')
                    quantity = item.get('quantity', 0)
                    
                    # Validate product ID
                    if not product_id:
                        return JsonResponse({
                            'success': False, 
                            'error': 'Product ID is required for all products. Please select a valid product.'
                        })
                    
                    # Validate quantity
                    try:
                        quantity = int(quantity)
                        if quantity <= 0:
                            return JsonResponse({
                                'success': False, 
                                'error': f'Invalid quantity for product {product_id}. Quantity must be greater than 0.'
                            })
                        if quantity > 9999:  # Reasonable upper limit
                            return JsonResponse({
                                'success': False, 
                                'error': f'Quantity too high for product {product_id}. Maximum allowed quantity is 9999.'
                            })
                    except (ValueError, TypeError):
                        return JsonResponse({
                            'success': False, 
                            'error': f'Invalid quantity for product {product_id}. Please enter a valid number.'
                        })
                    
                    try:
                        product = Product.objects.select_for_update().get(product_id=product_id)
                        
                        # Validate stock availability
                        if product.available_stock < quantity:
                            return JsonResponse({
                                'success': False, 
                                'error': f'Insufficient stock for "{product.name}" (ID: {product_id}). Available: {product.available_stock}, Requested: {quantity}. Please reduce quantity or select another product.'
                            })
                        
                        # Validate product is active/available
                        if product.available_stock == 0:
                            return JsonResponse({
                                'success': False, 
                                'error': f'Product "{product.name}" (ID: {product_id}) is out of stock. Please select another product.'
                            })
                        
                        # Calculate item totals
                        item_subtotal = product.price_per_unit * quantity
                        item_tax = (item_subtotal * product.tax_percentage) / 100
                        
                        total_amount += item_subtotal
                        tax_amount += item_tax
                        valid_products_count += 1
                        
                        # Store product data for processing after validation
                        products_to_process.append({
                            'product': product,
                            'quantity': quantity,
                            'item_subtotal': item_subtotal,
                            'item_tax': item_tax,
                            'product_data': {
                                'name': product.name,
                                'product_id': product.product_id,
                                'quantity': quantity,
                                'unit_price': float(product.price_per_unit),
                                'tax_percentage': float(product.tax_percentage),
                                'subtotal': float(item_subtotal),
                                'tax_amount': float(item_tax)
                            }
                        })
                        
                    except Product.DoesNotExist:
                        return JsonResponse({
                            'success': False, 
                            'error': f'Product with ID "{product_id}" not found in the system. Please select a valid product from the list.'
                        })
                
                # Validate at least one valid product
                if valid_products_count == 0:
                    return JsonResponse({
                        'success': False, 
                        'error': 'No valid products selected. Please add at least one product with valid quantity to generate a bill.'
                    })
                
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
                            try:
                                denomination_decimal = Decimal(str(denomination_value))
                                count_int = int(count)
                                total_customer_payment += denomination_decimal * count_int
                            except (ValueError, TypeError):
                                return JsonResponse({
                                    'success': False, 
                                    'error': f'Invalid denomination value or count for ₹{denomination_value}. Please check your input.'
                                })
                    
                    # Update amount paid to match customer denominations
                    amount_paid = total_customer_payment
                    purchase.amount_paid = amount_paid
                else:
                    # If no customer denominations specified, use the amount_paid field
                    total_customer_payment = amount_paid
                
                # Validate customer payment BEFORE reducing stock
                if total_customer_payment < grand_total:
                    shortfall = grand_total - total_customer_payment
                    return JsonResponse({
                        'success': False, 
                        'error': f'Insufficient payment amount. Total bill amount: ₹{grand_total}, Amount paid: ₹{total_customer_payment}, Shortfall: ₹{shortfall}. Please provide the complete payment amount.'
                    })
                
                # Validate payment is not excessively high (reasonable limit)
                if total_customer_payment > grand_total * 10:  # 10x the bill amount
                    return JsonResponse({
                        'success': False, 
                        'error': f'Payment amount (₹{total_customer_payment}) is excessively high compared to bill amount (₹{grand_total}). Please verify the payment amount.'
                    })
                
                # Second pass: Process products and reduce stock only after ALL validations pass
                for product_info in products_to_process:
                    # Create purchase item
                    PurchaseItem.objects.create(
                        purchase=purchase,
                        product=product_info['product'],
                        quantity=product_info['quantity'],
                        unit_price=product_info['product'].price_per_unit,
                        tax_percentage=product_info['product'].tax_percentage,
                        subtotal=product_info['item_subtotal']
                    )
                    
                    # Update product stock - ONLY after ALL validations pass (including payment validation)
                    product_info['product'].available_stock -= product_info['quantity']
                    product_info['product'].save()
                    
                    purchase_items.append(product_info['product_data'])
                
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
                
                # Step 2: Update available denominations (shop drawer management) - do this BEFORE customer payment
                for denomination_value, count in denominations_data.items():
                    if count > 0:
                        try:
                            denomination = Denomination.objects.get(value=Decimal(denomination_value))
                            denomination.count = int(count)
                            denomination.save()
                        except Denomination.DoesNotExist:
                            return JsonResponse({
                                'success': False, 
                                'error': f'Denomination ₹{denomination_value} not found in the system. Please check your shop drawer configuration.'
                            })
                        except (ValueError, TypeError):
                            return JsonResponse({
                                'success': False, 
                                'error': f'Invalid denomination value or count for ₹{denomination_value}. Please enter valid numbers.'
                            })
                
                # IMPORTANT CHANGE 1: Update shop drawer with customer payment denominations AFTER shop drawer is set
                print(f"DEBUG: Customer payment denominations received: {customer_payment_denominations}")
                if customer_payment_denominations:
                    print(f"DEBUG: Updating shop drawer with customer denominations")
                    updated_denominations = update_shop_drawer_from_customer_payment(customer_payment_denominations)
                    print(f"DEBUG: Updated denominations result: {updated_denominations}")
                else:
                    print(f"DEBUG: No customer denominations to update")
                
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
                    
                    # Validate if exact change can be given
                    if total_change_given < change_amount:
                        return JsonResponse({
                            'success': False, 
                            'error': f'Cannot provide exact change of ₹{change_amount}. Available denominations are insufficient. Please provide payment in smaller denominations or contact the cashier.'
                        })
                    
                    # Now update the database by subtracting the change denominations
                    print(f"DEBUG: Updating database to subtract change denominations")
                    for breakdown_item in change_breakdown:
                        if breakdown_item['count'] > 0:
                            try:
                                denomination = Denomination.objects.get(value=breakdown_item['value'])
                                print(f"DEBUG: Subtracting {breakdown_item['count']} from denomination {breakdown_item['value']} (current: {denomination.count})")
                                denomination.count -= breakdown_item['count']
                                denomination.save()
                                print(f"DEBUG: Updated denomination {breakdown_item['value']} to count: {denomination.count}")
                            except Denomination.DoesNotExist:
                                return JsonResponse({
                                    'success': False, 
                                    'error': f'Denomination ₹{breakdown_item["value"]} not found in the system. Please check your shop drawer configuration.'
                                })
                    
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
                
                print(f"DEBUG: Final available denominations: {available_denominations_dict}")
                print(f"DEBUG: Customer payment denominations in response: {customer_payment_denominations}")
                
                # Get final shop drawer status after transaction
                final_drawer_status = get_shop_drawer_status()
                
                print(f"DEBUG: Transaction completed successfully, returning response")
                return JsonResponse({
                    'success': True,
                    'purchase_id': str(purchase.purchase_id),
                    'customer_email': customer_email,
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
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False, 
                'error': 'Invalid request data format. Please check your input and try again.'
            })
        except ValueError as e:
            return JsonResponse({
                'success': False, 
                'error': f'Invalid data format: {str(e)}. Please check your input values.'
            })
        except Exception as e:
            print(f"ERROR in generate_bill: {str(e)}")
            return JsonResponse({
                'success': False, 
                'error': 'An unexpected error occurred while processing your request. Please try again or contact support if the problem persists.'
            })
    
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
        purchases = Purchase.objects.filter(customer_email__icontains=email).prefetch_related('items__product').order_by('-created_at')
    else:
        purchases = Purchase.objects.all().prefetch_related('items__product').order_by('-created_at')
    
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

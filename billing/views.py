from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from decimal import Decimal
import json
from .models import Product, Denomination, Purchase, PurchaseItem, ChangeBreakdown
from .forms import BillingForm, ProductForm, DenominationForm
from .utils import calculate_change_breakdown

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
                
                # Calculate grand total
                grand_total = total_amount + tax_amount
                change_amount = amount_paid - grand_total
                
                if change_amount < 0:
                    return JsonResponse({'success': False, 'error': 'Insufficient payment amount'})
                
                # Update purchase totals
                purchase.total_amount = total_amount
                purchase.tax_amount = tax_amount
                purchase.grand_total = grand_total
                purchase.change_amount = change_amount
                purchase.save()
                
                # Update denominations
                for denomination_value, count in denominations_data.items():
                    if count > 0:
                        denomination = Denomination.objects.get(value=Decimal(denomination_value))
                        denomination.count = int(count)
                        denomination.save()
                
                # Calculate change breakdown
                change_breakdown = []
                if change_amount > 0:
                    change_breakdown = calculate_change_breakdown(change_amount)
                    
                    # Save change breakdown
                    for breakdown in change_breakdown:
                        if breakdown['count'] > 0:
                            ChangeBreakdown.objects.create(
                                purchase=purchase,
                                denomination_value=breakdown['value'],
                                count=breakdown['count']
                            )
                
                # Send email (asynchronously in production)
                send_invoice_email(purchase, purchase_items, change_breakdown)
                
                return JsonResponse({
                    'success': True,
                    'purchase_id': str(purchase.purchase_id),
                    'total_amount': float(total_amount),
                    'tax_amount': float(tax_amount),
                    'grand_total': float(grand_total),
                    'amount_paid': float(amount_paid),
                    'change_amount': float(change_amount),
                    'items': purchase_items,
                    'change_breakdown': change_breakdown
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

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

class Product(models.Model):
    product_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    available_stock = models.PositiveIntegerField()
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product_id} - {self.name}"

    class Meta:
        ordering = ['name']

class Denomination(models.Model):
    value = models.DecimalField(max_digits=10, decimal_places=2)
    count = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"₹{self.value} x {self.count}"
    
    class Meta:
        ordering = ['-value']

class Purchase(models.Model):
    purchase_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    customer_email = models.EmailField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Purchase {self.purchase_id} - {self.customer_email}"

    class Meta:
        ordering = ['-created_at']

class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

class ChangeBreakdown(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='change_breakdown')
    denomination_value = models.DecimalField(max_digits=10, decimal_places=2)
    count = models.PositiveIntegerField()

    def __str__(self):
        return f"₹{self.denomination_value} x {self.count}"
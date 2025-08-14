from django.contrib import admin
from .models import Product, Denomination, Purchase, PurchaseItem, ChangeBreakdown

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['product_id', 'name', 'available_stock', 'price_per_unit', 'tax_percentage']
    list_filter = ['tax_percentage', 'created_at']
    search_fields = ['product_id', 'name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Denomination)
class DenominationAdmin(admin.ModelAdmin):
    list_display = ['value', 'count']
    ordering = ['-value']

class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    readonly_fields = ['subtotal']
    extra = 0

class ChangeBreakdownInline(admin.TabularInline):
    model = ChangeBreakdown
    readonly_fields = ['denomination_value', 'count']
    extra = 0

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['purchase_id', 'customer_email', 'grand_total', 'created_at']
    list_filter = ['created_at']
    search_fields = ['customer_email', 'purchase_id']
    readonly_fields = ['purchase_id', 'created_at']
    inlines = [PurchaseItemInline, ChangeBreakdownInline]
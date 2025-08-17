import os
import django

# ---------------- Django setup ---------------- #
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'billing_system.settings')  # CHANGE THIS
django.setup()

from billing.models import Product, Denomination  # change 'billing' if your app name is different

# ---------------- Seed Functions ---------------- #
def seed_products():
    products = [
    {"name": "Ceiling Fan", "product_id": "P001", "available_stock": 50, "price_per_unit": 1500.0, "tax_percentage": 20},
    {"name": "LED Bulb", "product_id": "P002", "available_stock": 200, "price_per_unit": 250.0, "tax_percentage": 12},
    {"name": "Electric Iron", "product_id": "P003", "available_stock": 70, "price_per_unit": 1200.0, "tax_percentage": 18},
    {"name": "Refrigerator", "product_id": "P004", "available_stock": 30, "price_per_unit": 25000.0, "tax_percentage": 28},
    {"name": "Washing Machine", "product_id": "P005", "available_stock": 25, "price_per_unit": 18000.0, "tax_percentage": 28},
]
    for p in products:
        obj, created = Product.objects.get_or_create(product_id=p["product_id"], defaults=p)
        if not created:
            for key, value in p.items():
                setattr(obj, key, value)
            obj.save()
        print(f"{'Created' if created else 'Updated'} product {p['name']}")

def seed_denominations():
    values = [500, 50, 20, 10, 5, 2, 1]
    count_in_hand = 100
    for val in values:
        obj, created = Denomination.objects.get_or_create(value=val)
        obj.count = count_in_hand
        obj.save()
        print(f"Set denomination {val} to count {count_in_hand} (created={created})")

# ---------------- Run Seeder ---------------- #
if __name__ == "__main__":
    print("🚀 Starting database seeding...")
    seed_products()
    seed_denominations()
    print("✅ Seeding complete.")
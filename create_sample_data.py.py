import os
import django

# ---------------- Django setup ---------------- #
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'billing_system.settings')  # CHANGE THIS
django.setup()

from billing.models import Product, Denomination  # change 'billing' if your app name is different

# ---------------- Seed Functions ---------------- #
def seed_products():
    products = [
        {"name": "Sugar", "product_id": "P001", "available_stock": 200, "price_per_unit": 45.5, "tax_percentage": 5},
        {"name": "Rice", "product_id": "P002", "available_stock": 150, "price_per_unit": 60.0, "tax_percentage": 5},
        {"name": "Milk", "product_id": "P003", "available_stock": 100, "price_per_unit": 25.0, "tax_percentage": 12},
        {"name": "Tea Powder", "product_id": "P004", "available_stock": 80, "price_per_unit": 150.0, "tax_percentage": 18},
        {"name": "Cooking Oil", "product_id": "P005", "available_stock": 90, "price_per_unit": 120.0, "tax_percentage": 12},
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
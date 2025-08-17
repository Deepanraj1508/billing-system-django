from django.test import TestCase, Client
from decimal import Decimal
from billing.models import Product, Denomination, Purchase, PurchaseItem, ChangeBreakdown
from django.urls import reverse

# Create your tests here.

class BillingFullFlowTest(TestCase):
    def setUp(self):
        # Create products
        self.product1 = Product.objects.create(
            product_id="P001",
            name="Test Product 1",
            available_stock=10,
            price_per_unit=Decimal('100.00'),
            tax_percentage=Decimal('18.00')
        )
        self.product2 = Product.objects.create(
            product_id="P002",
            name="Test Product 2",
            available_stock=5,
            price_per_unit=Decimal('200.00'),
            tax_percentage=Decimal('5.00')
        )
        # Create denominations (including small ones for exact change)
        Denomination.objects.create(value=Decimal('500'), count=5)
        Denomination.objects.create(value=Decimal('50'), count=20)
        Denomination.objects.create(value=Decimal('20'), count=50)
        Denomination.objects.create(value=Decimal('10'), count=50)
        Denomination.objects.create(value=Decimal('5'), count=50)
        Denomination.objects.create(value=Decimal('2'), count=50)
        Denomination.objects.create(value=Decimal('1'), count=50)
        self.client = Client()

    def test_full_billing_flow(self):
        # Simulate a purchase
        url = reverse('generate_bill')
        data = {
            "customer_email": "customer@example.com",
            "amount_paid": 500.0,
            "products": [
                {"product_id": "P001", "quantity": 2},
                {"product_id": "P002", "quantity": 1}
            ],
            "denominations": {
                "500": 5,
                "50": 20,
                "20": 50,
                "10": 50,
                "5": 50,
                "2": 50,
                "1": 50
            },
            "customer_payment_denominations": {
                "500": 1
            }
        }
        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        resp_json = response.json()
        self.assertTrue(resp_json.get('success'))
        # Check purchase created
        purchase = Purchase.objects.get(purchase_id=resp_json['purchase_id'])
        self.assertEqual(purchase.customer_email, "customer@example.com")
        # Check purchase items
        items = PurchaseItem.objects.filter(purchase=purchase)
        self.assertEqual(items.count(), 2)
        # Check change breakdown
        change_breakdown = ChangeBreakdown.objects.filter(purchase=purchase)
        # The exact change breakdown will depend on the denominations and logic
        self.assertIsNotNone(change_breakdown)
        # Check denominations updated
        for denom_value, expected_count in resp_json['available_denominations'].items():
            denom = Denomination.objects.get(value=Decimal(denom_value))
            self.assertEqual(denom.count, expected_count)
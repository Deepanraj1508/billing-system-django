from django import forms
from .models import Product, Denomination

class BillingForm(forms.Form):
    customer_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'customer@example.com'})
    )
    amount_paid = forms.DecimalField(
        max_digits=12, 
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'})
    )

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['product_id', 'name', 'available_stock', 'price_per_unit', 'tax_percentage']
        widgets = {
            'product_id': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'available_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'price_per_unit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'tax_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }

class DenominationForm(forms.ModelForm):
    class Meta:
        model = Denomination
        fields = ['value', 'count']
        widgets = {
            'value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
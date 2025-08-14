from decimal import Decimal
from .models import Denomination

def calculate_change_breakdown(change_amount):
    """Calculate the optimal denomination breakdown for change amount"""
    denominations = Denomination.objects.all().order_by('-value')
    breakdown = []
    remaining = change_amount
    
    for denomination in denominations:
        if remaining >= denomination.value and denomination.count > 0:
            count_needed = int(remaining // denomination.value)
            count_available = denomination.count
            count_to_give = min(count_needed, count_available)
            
            if count_to_give > 0:
                breakdown.append({
                    'value': denomination.value,
                    'count': count_to_give,
                    'total': denomination.value * count_to_give
                })
                remaining -= denomination.value * count_to_give
                
                # Update denomination count
                denomination.count -= count_to_give
                denomination.save()
    
    # Check if we could provide exact change
    if remaining > 0:
        # In a real scenario, you might want to handle this differently
        # For now, we'll just note that exact change couldn't be provided
        breakdown.append({
            'value': remaining,
            'count': 1,
            'total': remaining,
            'note': 'Approximate change (exact denomination not available)'
        })
    
    return breakdown
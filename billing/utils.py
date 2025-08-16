from decimal import Decimal, ROUND_HALF_UP
from .models import Denomination

def update_shop_drawer_in_database(customer_denominations):
    """
    Update shop drawer denominations in database in real-time
    This function is called as customer enters denominations
    """
    updated_denominations = {}
    
    for denomination_value, count in customer_denominations.items():
        if count > 0:
            try:
                denomination = Denomination.objects.get(value=Decimal(denomination_value))
                # Add customer denominations to existing drawer
                denomination.count += count
                denomination.save()
                updated_denominations[denomination_value] = denomination.count
            except Denomination.DoesNotExist:
                # Create new denomination if it doesn't exist
                denomination = Denomination.objects.create(
                    value=Decimal(denomination_value),
                    count=count
                )
                updated_denominations[denomination_value] = count
    
    return updated_denominations

def calculate_exact_change_greedy(change_amount, available_denominations):
    """
    Calculate exact change using greedy algorithm with proper rounding
    Returns the optimal denomination breakdown for the exact change amount
    Only returns exact denominations, no partial amounts
    """
    if change_amount <= 0:
        return [], Decimal('0.00')
    
    # Ensure change amount is rounded to nearest rupee to avoid decimal denominations
    change_amount = change_amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    
    # Debug: Print input values
    print(f"DEBUG utils: Change amount after rounding: {change_amount}")
    print(f"DEBUG utils: Available denominations: {[(d.value, d.count) for d in available_denominations]}")
    
    # Filter out denominations with decimal values - only use whole number denominations for change
    whole_denominations = [d for d in available_denominations if d.value == d.value.quantize(Decimal('1'), rounding=ROUND_HALF_UP)]
    
    print(f"DEBUG utils: Whole denominations after filtering: {[(d.value, d.count) for d in whole_denominations]}")
    
    # Sort denominations by value (highest first) for greedy approach
    sorted_denominations = sorted(whole_denominations, key=lambda x: x.value, reverse=True)
    
    breakdown = []
    remaining = change_amount
    total_change_given = Decimal('0.00')
    
    for denomination in sorted_denominations:
        if remaining <= 0:
            break
            
        if denomination.count > 0:
            # Calculate how many of this denomination we can use
            count_needed = int(remaining // denomination.value)
            count_available = denomination.count
            count_to_give = min(count_needed, count_available)
            
            print(f"DEBUG utils: Processing denomination {denomination.value}, remaining: {remaining}, count_needed: {count_needed}, count_to_give: {count_to_give}")
            
            if count_to_give > 0:
                breakdown.append({
                    'value': denomination.value,
                    'count': count_to_give,
                    'total': denomination.value * count_to_give
                })
                
                remaining -= denomination.value * count_to_give
                total_change_given += denomination.value * count_to_give
                
                print(f"DEBUG utils: Added {count_to_give} x {denomination.value} = {denomination.value * count_to_give}, new remaining: {remaining}")
                
                # Update denomination count in shop drawer
                denomination.count -= count_to_give
                denomination.save()
    
    # If we couldn't provide exact change, we don't add partial denominations
    # The remaining amount will be handled by the business logic
    # This ensures only exact denominations are returned
    
    return breakdown, total_change_given

def update_shop_drawer_from_customer_payment(customer_denominations):
    """
    Update shop drawer denominations when customer pays with specific denominations
    This adds customer's payment to the shop's available denominations
    """
    updated_denominations = {}
    
    for denomination_value, count in customer_denominations.items():
        if count > 0:
            try:
                denomination = Denomination.objects.get(value=Decimal(denomination_value))
                denomination.count += count
                denomination.save()
                updated_denominations[denomination_value] = denomination.count
            except Denomination.DoesNotExist:
                # Create new denomination if it doesn't exist
                denomination = Denomination.objects.create(
                    value=Decimal(denomination_value),
                    count=count
                )
                updated_denominations[denomination_value] = count
    
    return updated_denominations

def get_shop_drawer_status():
    """
    Get current status of shop drawer denominations
    """
    denominations = Denomination.objects.all().order_by('-value')
    drawer_status = {}
    
    for denomination in denominations:
        drawer_status[str(denomination.value)] = {
            'value': denomination.value,
            'count': denomination.count,
            'total_value': denomination.value * denomination.count
        }
    
    return drawer_status

def validate_customer_payment(customer_denominations, required_amount):
    """
    Validate if customer denominations match the required amount
    """
    total_customer_payment = Decimal('0.00')
    
    for denomination_value, count in customer_denominations.items():
        if count > 0:
            total_customer_payment += Decimal(str(denomination_value)) * count
    
    return total_customer_payment >= required_amount, total_customer_payment

def calculate_optimal_change_denominations(change_amount, available_denominations):
    """
    Calculate the most optimal denomination combination for change
    Uses greedy algorithm to minimize the number of denominations given
    """
    if change_amount <= 0:
        return []
    
    # Sort denominations by value (highest first)
    sorted_denominations = sorted(available_denominations, key=lambda x: x.value, reverse=True)
    
    breakdown = []
    remaining = change_amount
    
    for denomination in sorted_denominations:
        if remaining <= 0:
            break
            
        if denomination.count > 0:
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
    
    return breakdown, remaining
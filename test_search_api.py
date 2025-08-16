import os
import django
import requests
import json

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'billing_system.settings')
django.setup()

def test_search_api():
    """Test the product search API"""
    base_url = "http://localhost:8000"
    
    # Test cases
    test_queries = [
        "sugar",      # Should find "Sugar"
        "rice",       # Should find "Rice"
        "P001",       # Should find by product ID
        "milk",       # Should find "Milk"
        "tea",        # Should find "Tea Powder"
        "cooking",    # Should find "Cooking Oil"
        "xyz",        # Should return empty results
    ]
    
    print("🧪 Testing Product Search API")
    print("=" * 50)
    
    for query in test_queries:
        try:
            response = requests.get(f"{base_url}/api/search-products/?q={query}")
            if response.status_code == 200:
                data = response.json()
                print(f"\n🔍 Search for '{query}':")
                print(f"   Status: {response.status_code}")
                print(f"   Success: {data.get('success', False)}")
                print(f"   Results: {len(data.get('products', []))}")
                
                for product in data.get('products', []):
                    print(f"   - {product['text']} (Price: ₹{product['price']}, Stock: {product['stock']})")
            else:
                print(f"\n❌ Search for '{query}' failed: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"\n❌ Could not connect to server. Make sure the server is running on {base_url}")
            break
        except Exception as e:
            print(f"\n❌ Error testing '{query}': {str(e)}")

if __name__ == "__main__":
    test_search_api()

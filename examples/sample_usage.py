# Sample usage examples for the Wallapop plugin.
#
# Run after `pip install -e .` (package importable as `wallapop`).

import json

from wallapop.tools import search_wallapop as wallapop_search
from wallapop.tools import get_item_details as wallapop_get_item

def example_basic_search():
    """Basic search example."""
    result = wallapop_search({"query": "product name"})
    data = json.loads(result)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def example_search_with_location():
    """Search with location filter."""
    result = wallapop_search({
        "query": "item",
        "location": "Madrid"
    })
    data = json.loads(result)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def example_coordinate_search():
    """Coordinate-based search (recommended for precise location)."""
    result = wallapop_search({
        "query": "item",
        "latitude": 40.4168,
        "longitude": -3.7038,
        "radius_km": 10
    })
    data = json.loads(result)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def example_search_with_category():
    """Search with category filter."""
    result = wallapop_search({
        "query": "watch",
        "category": "moda"  # Fashion category
    })
    data = json.loads(result)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def example_price_filter():
    """Search with price filter."""
    result = wallapop_search({
        "query": "laptop",
        "min_price": 100,
        "max_price": 500
    })
    data = json.loads(result)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def example_get_item_details():
    """Get detailed information about a specific item."""
    result = wallapop_get_item({"item_id": "12345"})
    data = json.loads(result)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def example_reloj_seiko_donostia():
    """Search for Seiko watches in Donostia (San Sebastián)."""
    result = wallapop_search({
        "query": "reloj seiko",
        "latitude": 42.9967,
        "longitude": -2.6764,
        "radius_km": 20,
        "category": "moda"
    })
    data = json.loads(result)
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # Run examples
    print("Basic Search:")
    example_basic_search()
    print("\n" + "="*50 + "\n")
    
    print("Coordinate Search:")
    example_coordinate_search()
    print("\n" + "="*50 + "\n")
    
    print("ReLOJ Seiko Donostia:")
    example_reloj_seiko_donostia()
"""Wallapop plugin schemas."""

import json

# Esquema para la herramienta de búsqueda
SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query - the item name or keywords to search for (e.g., 'iPhone 15', 'MacBook Pro')"
        },
        "location": {
            "type": "string",
            "description": "Location name or city for the search (e.g., 'Madrid', 'Barcelona', 'Spain')"
        },
        "latitude": {
            "type": "number",
            "description": "Latitude coordinate for location-based search"
        },
        "longitude": {
            "type": "number",
            "description": "Longitude coordinate for location-based search"
        },
        "city": {
            "type": "string",
            "description": "City name for localStorage location setup (e.g., 'Madrid', 'Barcelona')"
        },
        "province": {
            "type": "string",
            "description": "Province name for localStorage location setup (e.g., 'Madrid', 'Barcelona')"
        },
        "community": {
            "type": "string",
            "description": "Autonomous community name for localStorage setup (default: 'España')",
            "default": "España"
        },
        "radius_km": {
            "type": "integer",
            "description": "Search radius in kilometers (default: 20)",
            "default": 20
        },
        "min_price": {
            "type": "integer",
            "description": "Minimum price in euros"
        },
        "max_price": {
            "type": "integer",
            "description": "Maximum price in euros"
        },
        "state": {
            "type": "string",
            "enum": ["nuevo", "usado", "como nuevo", "reparable"],
            "description": "Item condition state"
        },
        "shipping_available": {
            "type": "boolean",
            "description": "Filter for items with shipping available"
        },
        "free_shipping": {
            "type": "boolean",
            "description": "Filter for items with free shipping only"
        },
        "category": {
            "type": "string",
            "description": "Category filter (e.g., 'movilidad', 'telefonia', 'ordenadores', 'hogar')"
        },
        "sort": {
            "type": "string",
            "enum": ["relevancia", "precio_ascendente", "precio_descendente", "mas_recientes", "menos_recientes"],
            "description": "Sort order for results",
            "default": "relevancia"
        },
        "page": {
            "type": "integer",
            "description": "Page number for pagination (default: 1)",
            "default": 1
        },
        "items_per_page": {
            "type": "integer",
            "description": "Number of results per page (default: 20, max: 50)",
            "default": 20
        }
    },
    "required": ["query"]
}

# Esquema para obtener detalles de un artículo
ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "item_id": {
            "type": "string",
            "description": "The item ID from a search result"
        },
        "url": {
            "type": "string",
            "description": "Direct URL to the item on Wallapop"
        }
    },
    "required": ["item_id"]
}

# Export schemas
schemas = type('schemas', (), {
    'SEARCH_SCHEMA': SEARCH_SCHEMA,
    'ITEM_SCHEMA': ITEM_SCHEMA
})()
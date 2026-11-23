"""Wallapop plugin tool schemas — what the LLM reads to decide when to call a tool.

Each schema is the full object passed to ctx.register_tool(schema=...):
a top-level ``name`` and ``description`` plus a JSON-schema under ``parameters``.
"""

SEARCH_SCHEMA = {
    "name": "wallapop_search",
    "description": (
        "Search the Spanish second-hand marketplace Wallapop (es.wallapop.com). "
        "Use it to find second-hand items with filters: a text query, a location "
        "(city name) or coordinates (latitude/longitude + radius), a price range, "
        "a condition, a category, shipping filters, sorting and pagination. "
        "Returns JSON with an items array (id, url, title, price, condition, location)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query - the item name or keywords to search for (e.g., 'iPhone 15', 'MacBook Pro')"
            },
            "location": {
                "type": "string",
                "description": (
                    "Location name, city, municipality, neighborhood, or 5-digit Spanish postal code "
                    "(e.g., 'Getafe', 'Madrid', '28013', 'Barrio de Gràcia, Barcelona', 'Donostia', '41001'). "
                    "The plugin automatically and accurately resolves exact coordinates. "
                    "DO NOT guess or invent GPS coordinates yourself; pass the place name or postal code here."
                )
            },
            "latitude": {
                "type": "number",
                "description": "Optional explicit GPS latitude override. Only supply if the human user provided exact numerical coordinates; otherwise leave blank and use 'location'."
            },
            "longitude": {
                "type": "number",
                "description": "Optional explicit GPS longitude override. Only supply if the human user provided exact numerical coordinates; otherwise leave blank and use 'location'."
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
                "description": "Legacy item condition state - prefer 'condition'"
            },
            "condition": {
                "type": "string",
                "enum": ["nuevo", "como nuevo", "good", "fair", "has_given_it_all"],
                "description": "Item condition filter. A single value, a comma-separated string, "
                               "or values you pass as a list of these."
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
                "description": "Category filter (e.g., 'movilidad', 'telefonia', 'ordenadores', 'hogar', 'moda')"
            },
            "sort": {
                "type": "string",
                "enum": ["relevancia", "price_low_to_high", "price_high_to_low", "mas_recientes", "newest", "mas_cercanos"],
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
}

ITEM_SCHEMA = {
    "name": "wallapop_get_item",
    "description": (
        "Get full details for a specific Wallapop item, by its id (from wallapop_search) "
        "or a direct item URL. Returns JSON with title, price, description, images, seller, "
        "location, shipping and status."
    ),
    "parameters": {
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
        }
    }
}

LOCATE_SCHEMA = {
    "name": "wallapop_locate",
    "description": (
        "Resolve a Spanish city, municipality, neighborhood, or postal code into precise coordinates "
        "and province metadata. Useful to verify location resolution before searching."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "Location name, municipality, neighborhood, or 5-digit Spanish postal code (e.g. 'Getafe', '28013', 'Triana')"
            }
        },
        "required": ["location"]
    }
}

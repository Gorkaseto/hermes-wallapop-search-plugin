---
name: Wallapop Plugin
id: wallapop
description: "Search Wallapop - Spanish second-hand marketplace"
version: 0.1.0
author: Hermes Agent
license: MIT
---

# Wallapop Plugin for Hermes Agent

A plugin that enables searching the Spanish second-hand marketplace Wallapop directly from Hermes Agent.

## Available Tools

### `wallapop_search`

Search Wallapop for items with various filters.

**Parameters:**
- `query` (string, required): Search query
- `location` (string, optional): Location name or city
- `latitude` (number, optional): Latitude for coordinate search
- `longitude` (number, optional): Longitude for coordinate search
- `city` (string, optional): City name for localStorage location setup - used when latitude/longitude provided for proper location-based search
- `province` (string, optional): Province name for localStorage location setup
- `community` (string, default: "España"): Autonomous community name for localStorage setup
- `radius_km` (integer, default: 20): Search radius in km
- `min_price` (integer, optional): Minimum price in euros (uses `min_sale_price` in Wallapop API)
- `max_price` (integer, optional): Maximum price in euros (uses `max_sale_price` in Wallapop API)
- `state` (string, optional): Legacy parameter - use `condition` instead
- `condition` (string|list, optional): State filter - supports single value or array of "nuevo" (new), "como nuevo" (same as as_good_as_new), "good", "fair", "has_given_it_all". Multiple values can be passed as array or comma-separated string.
- `shipping_available` (boolean, optional): Filter for items with shipping
- `free_shipping` (boolean, optional): Filter for items with free shipping only
- `category` (string, optional): Item category
- `sort` (string, default: "relevancia"): Sort order - "relevancia", "price_low_to_high", "price_high_to_low", "mas_recientes", "mas_cercanos"
- `page` (integer, default: 1): Page number
- `items_per_page` (integer, default: 20, max: 50): Results per page

**Returns:** JSON with search results containing items array with id, url, title, price, etc.

### `wallapop_get_item`

Get detailed information about a specific item.

**Parameters:**
- `item_id` (string, optional): The item ID
- `url` (string, optional): Direct URL to the item

**Returns:** JSON with full item details including description, images, seller info, etc.

## Usage Examples

### Basic search:
```
wallapop_search({"query": "product name"})
```

### Search in a specific city with price filter:
```
wallapop_search({"query": "item", "location": "CityName", "min_price": 50, "max_price": 500})
```

### Coordinate-based search (recommended for precise location):
```
wallapop_search({"query": "item", "latitude": X.XXXX, "longitude": Y.YYYY, "radius_km": 10})
```

### Search with category filter:
```
wallapop_search({"query": "item", "category": "moda"})
```

### Search for new items with free shipping:
```
wallapop_search({"query": "item", "condition": "nuevo", "free_shipping": true})
```

### Get item details:
```
wallapop_get_item({"item_id": "12345"})
```

## Available Categories

- `movilidad` - Vehicles
- `telefonia` - Phones
- `ordenadores` - Computers  
- `hogar` - Home
- `electrodomesticos` - Appliances
- `moda` - Fashion
- `deporte` - Sports
- `juguetes` - Toys
- `libros` - Books
- `musica` - Music
- `videojuegos` - Video games
- `belleza` - Beauty
- `mascotas` - Pets
- `salud` - Health
- `herramientas` - Tools
- `artesania` - Crafts

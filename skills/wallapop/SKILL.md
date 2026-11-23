---
name: Wallapop Plugin
id: wallapop
description: "Search Wallapop - Spanish second-hand marketplace"
version: 0.2.1
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
- `location` (string, recommended for location): City, municipality, neighborhood, or 5-digit postal code (e.g. "Getafe", "28013", "Barrio de Gràcia, Barcelona", "Sevilla"). The plugin resolves exact coordinates automatically. **Do not estimate or guess GPS coordinates.**
- `radius_km` (integer, default: 20): Search radius in km
- `latitude` / `longitude` (number, optional override): Only pass if the human user explicitly provided exact numerical GPS coordinates.
- `min_price` (integer, optional): Minimum price in euros
- `max_price` (integer, optional): Maximum price in euros
- `condition` (string|list, optional): "nuevo", "como nuevo", "good", "fair", "has_given_it_all"
- `shipping_available` (boolean, optional): Filter for items with shipping
- `free_shipping` (boolean, optional): Filter for items with free shipping only
- `category` (string, optional): Item category
- `sort` (string, default: "relevancia"): "relevancia", "price_low_to_high", "price_high_to_low", "mas_recientes", "mas_cercanos"
- `page` (integer, default: 1): Page number
- `items_per_page` (integer, default: 20, max: 50): Results per page

**Returns:** JSON with search results containing items array with id, url, title, price, etc.

### `wallapop_get_item`

Get detailed information about a specific item.

**Parameters:**
- `item_id` (string, optional): The item ID
- `url` (string, optional): Direct URL to the item

**Returns:** JSON with full item details including description, images, seller info, etc.

### `wallapop_locate`

Resolve a place name, town, neighborhood, or 5-digit Spanish postal code into exact coordinates.

**Parameters:**
- `location` (string, required): Place name or postal code (e.g. "28013", "Móstoles", "Triana, Sevilla")

**Returns:** JSON with resolved latitude, longitude, municipality, province, and label.

## Usage Examples

### Basic search:
```
wallapop_search({"query": "product name"})
```

### Search in a specific town or city (recommended):
```
wallapop_search({"query": "item", "location": "Getafe", "min_price": 50, "max_price": 500})
```

### Search by postal code:
```
wallapop_search({"query": "item", "location": "28013", "radius_km": 15})
```

### Resolve location coordinates:
```
wallapop_locate({"location": "Alcorcón"})
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

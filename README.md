# Wallapop Plugin for Hermes Agent

A Python plugin that enables searching the Spanish second-hand marketplace [Wallapop](https://wallapop.com) directly from Hermes Agent.

## ⚠️ Important Limitations About Location Filters

Wallapop **does not allow geographic filtering without authentication**. When you use:
- `location` parameter (e.g., "Madrid", "Barcelona")
- `latitude`/`longitude` parameters

The search returns **national results** without geographic filtering. This is a limitation imposed by Wallapop's API.

**Workarounds:**
- Search without location filters and manually review item locations
- Use keyword searches to narrow results (e.g., brand names, specific items)

## ⚠️ Critical Note About JavaScript

Wallapop's website renders search results **dynamically with JavaScript**. The basic HTTP scraper used by this plugin may not find all items. For full results, you have two options:

### Option 1: Install Playwright (Recommended)

```bash
pip install playwright beautifulsoup4 lxml requests
playwright install chromium
playwright install-deps chromium  # Linux system dependencies
```

### Option 2: Use Hermes' browser_exec Tool

If you have the `browser_exec` tool available in Hermes, it provides a full browser environment with JavaScript support.

## Installation

### From Hermes Agent

The plugin will automatically install its dependencies (`beautifulsoup4`, `lxml`, `requests`, `playwright`) when loaded.

### Manual Installation

```bash
pip install beautifulsoup4 lxml requests playwright
```

For playwright browsers:
```bash
playwright install chromium
```

## Usage

### With Hermes Agent

```python
# Basic search
wallapop_search({"query": "product name"})

# Search with location
wallapop_search({"query": "item", "location": "Madrid"})

# Coordinate-based search (recommended for precise location)
wallapop_search({"query": "item", "latitude": X.XXXX, "longitude": Y.YYYY, "radius_km": 10})

# Search with category
wallapop_search({"query": "item", "category": "moda"})

# Get item details
wallapop_get_item({"item_id": "12345"})
```

### Available Categories

| Category | Description | ID |
|----------|-------------|-----|
| movilidad | Vehicles | 1 |
| telefonia | Phones | 1-1 |
| ordenadores | Computers | 4 |
| hogar | Home | 8 |
| electrodomesticos | Appliances | 8 |
| moda | Fashion | 14 |
| deporte | Sports | 16 |
| juguetes | Toys | 18 |
| libros | Books | 20 |
| musica | Music | 21 |
| videojuegos | Video games | 22 |
| belleza | Beauty | 25 |
| mascotas | Pets | 26 |
| salud | Health | 27 |
| herramientas | Tools | 28 |
| artesania | Crafts | 33 |
| coches | Cars | 2 |
| motos | Motorcycles | 3 |

### Sort Options

- `relevancia` - By relevance (default)
- `price_low_to_high` - Price ascending
- `price_high_to_low` - Price descending
- `newest_first` - Newest first
- `closest` - Closest to location

### Condition Filters

- `nuevo` / `as_good_as_new` - New
- `good` - Good condition
- `fair` - Fair condition
- `has_given_it_all` - Reparable

## API Reference

### `wallapop_search(args)`

Search Wallapop for items.

**Parameters:**
- `query` (str, required): Search query
- `location` (str, optional): City or location name
- `latitude` (float, optional): Latitude for coordinate search
- `longitude` (float, optional): Longitude for coordinate search
- `city` (str, optional): City name for location setup
- `province` (str, optional): Province name for location setup
- `community` (str, default: "España"): Autonomous community
- `radius_km` (int, default: 20): Search radius in km
- `min_price` (int, optional): Minimum price
- `max_price` (int, optional): Maximum price
- `condition` (str|list, optional): Item condition filter
- `shipping_available` (bool, optional): Filter for shipping
- `free_shipping` (bool, optional): Filter for free shipping only
- `category` (str, optional): Item category
- `sort` (str, default: "relevancia"): Sort order
- `page` (int, default: 1): Page number
- `items_per_page` (int, default: 20, max: 50): Results per page

**Returns:** JSON string with search results

### `wallapop_get_item(args)`

Get detailed information about a specific item.

**Parameters:**
- `item_id` (str, optional): Item ID from search result
- `url` (str, optional): Direct URL to the item

**Returns:** JSON string with item details

## Project Structure

```
wallapop-plugin/
├── wallapop_plugin/
│   ├── __init__.py
│   ├── tools.py
│   └── api_client.py
├── tests/
│   └── test_tools.py
├── examples/
│   └── sample_usage.py
├── README.md
├── plugin.yaml
├── requirements.txt
├── pyproject.toml
└── LICENSE
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/hermes-agent/wallapop-plugin.git
cd wallapop-plugin

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Install playwright browsers
playwright install chromium
```

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black .
isort .
flake8 .
```

## Requirements

- Python 3.8+
- beautifulsoup4
- lxml
- requests
- playwright (optional, for JavaScript-rendered content)

## Limitations

- Wallapop may block automated requests. Use responsibly and respect robots.txt
- JavaScript-rendered content requires Playwright
- Location searches work best with coordinates rather than city names

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## Acknowledgments

- Wallapop API is not officially documented - this plugin scrapes the web interface
- Coordinates for Spanish cities obtained from OpenStreetMap/Nominatim
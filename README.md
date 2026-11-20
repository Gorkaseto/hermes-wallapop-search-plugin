# Wallapop Plugin for Hermes Agent

A Hermes Agent plugin that searches the Spanish second-hand marketplace
[Wallapop](https://es.wallapop.com) — list items with filters and read a single
item's details.

## Install from GitHub

Plugins are opt-in, so you install and then enable:

```bash
hermes plugins install Gorkaseto/hermes-wallapop-search-plugin
hermes plugins enable wallapop
```

`hermes plugins install` clones the repo into `~/.hermes/plugins/wallapop/`,
reads `plugin.yaml`, and installs the declared Python dependencies
(`requests`, `beautifulsoup4`, `lxml`). `hermes plugins enable wallapop` turns
it on (add `wallapop` under `plugins.enabled` in `~/.hermes/config.yaml`).

Check it loaded:

```bash
hermes plugins list          # shows "wallapop v1.0.0 (2 tools)"
hermes plugins doctor wallapop
```

## Usage

```python
# Basic search
wallapop_search({"query": "product name"})

# Search in a city with a price range
wallapop_search({"query": "item", "location": "Madrid", "min_price": 50, "max_price": 500})

# Coordinate-based search (recommended for precise location)
wallapop_search({"query": "item", "latitude": 40.4168, "longitude": -3.7038, "radius_km": 10})

# Search a category, new items with free shipping
wallapop_search({"query": "item", "category": "moda", "condition": "nuevo", "free_shipping": true})

# Get item details
wallapop_get_item({"item_id": "12345"})
```

### `wallapop_search(args)`

Search Wallapop. Returns a JSON string with an `items` array.

**Parameters:**
- `query` (str, required): Search query
- `location` (str): City or location name
- `latitude` / `longitude` (float): Coordinates for a location-based search
- `city` / `province` / `community` (str): Names for the localStorage location setup (default community: `España`)
- `radius_km` (int, default 20): Search radius in km
- `min_price` / `max_price` (int): Price range
- `condition` (str | list): `nuevo`, `como nuevo`, `good`, `fair`, `has_given_it_all` (a value, comma-separated string, or a list)
- `state` (str): Legacy condition — use `condition`
- `shipping_available` / `free_shipping` (bool): Shipping filters
- `category` (str): Category name (see table below)
- `sort` (str, default `relevancia`): `relevancia`, `price_low_to_high`, `price_high_to_low`, `mas_recientes`, `mas_cercanos`
- `page` (int, default 1), `items_per_page` (int, default 20, max 50)

### `wallapop_get_item(args)`

- `item_id` (str) — the id from a search result
- `url` (str) — a direct item URL (use one of the two)

Returns a JSON string with title, price, description, images, seller, location, shipping, status.

### Available categories

| Category | Description | Category | Description |
|----------|-------------|----------|-------------|
| movilidad | Vehicles | ordenadores | Computers |
| telefonia | Phones | hogar | Home |
| coches | Cars | electrodomesticos | Appliances |
| motos | Motorcycles | moda | Fashion |
| deporte | Sports | juguetes | Toys |
| libros | Books | musica | Music |
| videojuegos | Video games | belleza | Beauty |
| mascotas | Pets | salud | Health |
| herramientas | Tools | artesania | Crafts |

## Limitations

- **Location filters need authentication.** Wallapop returns national (unfiltered)
  results when you pass `location` / `latitude` / `longitude` without a signed-in
  browser session; coordinate searches work best with the Playwright path below.
  Workaround: search without a location filter and review item locations, or use
  keyword searches to narrow results.
- **JavaScript rendering.** Wallapop renders search results dynamically. The plain
  HTTP scraper may miss items. For full results install Playwright:

  ```bash
  pip install playwright
  playwright install chromium
  ```

- **Rate limits / blocking.** Wallapop may block automated requests. Use
  responsibly and respect robots.txt.

## Project layout

The repo root is the native Hermes plugin directory:

```
hermes-wallapop-search-plugin/
├── plugin.yaml           # manifest: name, version, provides_tools, python_dependencies
├── __init__.py           # register(ctx): wires schemas -> handlers, registers skills
├── schemas.py            # tool schemas the LLM reads (name, description, parameters)
├── tools.py              # tool handlers (search_wallapop, get_item_details)
├── api_client.py         # Playwright fetch + Wallapop URL building / parsing
├── skills/wallapop/
│   └── SKILL.md          # bundled skill registered by register(ctx)
├── tests/test_tools.py
├── examples/sample_usage.py
├── README.md
├── requirements.txt
├── pyproject.toml
└── LICENSE
```

## Development

```bash
git clone https://github.com/Gorkaseto/hermes-wallapop-search-plugin.git
cd hermes-wallapop-search-plugin
pip install -e ".[dev]"          # installs the modules as package `wallapop` + test tools

# Run tests from inside tests/ (that dir is the pytest rootdir; see tests/pytest.ini):
cd tests
pytest
```

The `pip install -e .` path installs the modules as an importable package
named `wallapop` (for tests/dev); the `hermes plugins install` path loads the
directory natively.

## License

MIT License — see [LICENSE](LICENSE).

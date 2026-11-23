# Wallapop Plugin for Hermes Agent

A comprehensive Hermes Agent plugin for searching and inspecting listings on the Spanish second-hand marketplace [Wallapop](https://es.wallapop.com).

Equipped with a **dedicated Playwright automation pipeline**, **dynamic geocoding for Spain**, and **multi-environment runtime discovery**, this plugin operates reliably without being blocked by CloudFront WAF or SPA rendering limitations.

---

## Key Features

- **Dedicated Playwright Pipeline:** Uses headless Chromium with stealth anti-detection flags (`--disable-blink-features=AutomationControlled`, `--no-sandbox`) to bypass CloudFront WAF and antibot challenges.
- **Dynamic SPA Interception:** Intercepts internal Next.js `api/v3/search/section` endpoints, extracting rich, clean structured JSON listings with high-resolution image URLs, seller info, and accurate price data.
- **Dynamic Geocoding Engine (`location.py`):** Automatically converts cities, municipalities, neighborhoods, and 5-digit Spanish postal codes (e.g. `28013`, `Getafe`, `Barrio de Gràcia, Barcelona`) into exact GPS coordinates. Includes bounding box validation for Spain (Peninsula, Balearic, Canary Islands, Ceuta, and Melilla).
- **Dual-Tier Zero-Touch Setup:**
  1. *Background Provisioning:* Chromium binaries download silently in a daemon thread upon plugin activation (`register(ctx)`), readying the browser before the first query.
  2. *Just-in-Time Fallback:* If a search is issued before background setup finishes, the client verifies and provisions the binary immediately.
- **Multi-Environment Runtime Bridging:** Seamlessly bridges Hermes Agent host processes and managed toolchain interpreters (`~/.hermes/tools/python-3.14...`). Dynamically registers `site-packages` into `sys.path` and includes transparent subprocess delegation if Playwright is installed in a separate Python environment.
- **Debian / PEP 668 & `uv` Support:** Automatically uses `uv` if present and applies `--break-system-packages` where required to comply with modern Linux environments.

---

## Installation & Setup

### Install in Hermes Agent

```bash
hermes plugins install Gorkaseto/hermes-wallapop-search-plugin
hermes plugins enable wallapop
```

Hermes downloads the plugin into `~/.hermes/plugins/wallapop/`, reads `plugin.yaml`, installs declared dependencies (`playwright`), and enables the tools.

Verify the installation:
```bash
hermes plugins list          # shows "wallapop v0.2.2 (3 tools)"
hermes plugins doctor wallapop
```

---

## Available Tools

The plugin registers **3 tools** in Hermes:

### 1. `wallapop_search(args)`
Search Wallapop listings with extensive filters.

**Parameters:**
- `query` (str, required): Keywords to search for.
- `location` (str, recommended): City, municipality, or 5-digit postal code (e.g., `"Madrid"`, `"41001"`, `"Sabadell"`). Coordinates are resolved dynamically.
- `radius_km` (int, default: 20): Search radius in kilometers.
- `latitude` / `longitude` (float, optional override): Only pass if the user provides exact GPS coordinates directly.
- `min_price` / `max_price` (int, optional): Price limits in euros.
- `condition` (str | list, optional): Item condition:
  - `nuevo` (`new`)
  - `como nuevo` (`as_good_as_new`)
  - `good` (`good` / `buen estado`)
  - `fair` (`fair` / `aceptable`)
  - `has_given_it_all` (`lo ha dado todo` / `para piezas`)
- `shipping_available` (bool, optional): Filter for items with shipping allowed.
- `free_shipping` (bool, optional): Filter for free shipping only.
- `category` (str, optional): Category slug or name (see table below).
- `sort` (str, default: `"relevancia"`): Sort criteria (`relevancia`, `price_low_to_high`, `price_high_to_low`, `mas_recientes` / `newest`, `mas_cercanos`).
- `page` (int, default: 1): Pagination page number.
- `items_per_page` (int, default: 20, max: 50): Number of results per page.

**Example Tool Call:**
```json
{
  "query": "portatil thinkpad",
  "location": "Valencia",
  "min_price": 150,
  "max_price": 500,
  "condition": "como nuevo",
  "sort": "price_low_to_high"
}
```

---

### 2. `wallapop_get_item(args)`
Fetch complete listing details, seller metadata, and full-resolution images.

**Parameters:**
- `item_id` (str, optional): Numerical item ID.
- `url` (str, optional): Full URL of the listing (e.g. `https://es.wallapop.com/item/...`).

**Example Tool Call:**
```json
{
  "url": "https://es.wallapop.com/item/nintendo-switch-oled-1320804068"
}
```

---

### 3. `wallapop_locate(args)`
Dedicated geocoding utility to inspect coordinates and location metadata for any Spanish place name or postal code.

**Parameters:**
- `location` (str, required): Place name or 5-digit postal code (e.g. `"08001"`, `"Getafe"`, `"Triana, Sevilla"`).

**Example Tool Call:**
```json
{
  "location": "28013"
}
```

**Output:**
```json
{
  "latitude": 40.419,
  "longitude": -3.7077,
  "city": "Madrid",
  "province": "Madrid",
  "community": "España",
  "postal_code": "28013",
  "label": "28013, Madrid, ESP",
  "source": "photon"
}
```

---

## Sorting Options (`sort`)

The plugin automatically maps user and LLM queries to the exact values required by Wallapop:

| Schema Value | Accepted Aliases | Wallapop `order_by` | Description |
| :--- | :--- | :--- | :--- |
| **`relevancia`** *(default)* | `relevance`, `most_relevance` | `most_relevance` | Wallapop algorithmic relevance |
| **`price_low_to_high`** | `precio_ascendente` | `price_low_to_high` | Lowest price first |
| **`price_high_to_low`** | `precio_descendente` | `price_high_to_low` | Highest price first |
| **`mas_recientes`** / **`newest`** | `newest_first` | `newest` | Most recently posted / renewed listings |
| **`mas_cercanos`** | `closest` | `closest` | Closest physical distance (requires location) |

---

## Supported Categories

| Category Slug | Name / Description | Category Slug | Name / Description |
| :--- | :--- | :--- | :--- |
| `ordenadores` | Informática / PCs / Portátiles | `hogar` | Muebles / Hogar / Decoración |
| `telefonia` | Móviles / Accesorios | `electrodomesticos` | Electrodomésticos |
| `videojuegos` | Consolas / Juegos | `moda` | Ropa / Calzado / Accesorios |
| `movilidad` | Patinetes / Bicis eléctricas | `deporte` | Ocio / Deportes / Bicicletas |
| `coches` | Automóviles | `motos` | Motocicletas |
| `motor-y-accesorios` | Piezas / Accesorios de motor | `juguetes` | Juguetes / Juegos de mesa / Bebés |
| `libros` | Libros / Cómics / Revistas | `musica` | Instrumentos / Vinilos / CDs |
| `audio` / `tv` | Imagen y Sonido | `belleza` | Cosmética / Belleza / Cuidado |
| `herramientas` | Bricolaje / Herramientas | `inmobiliaria` | Pisos / Casas / Alquiler |

---

## Project Structure

```text
hermes-wallapop-search-plugin/
├── plugin.yaml              # Hermes plugin manifest & python_dependencies
├── __init__.py              # register(ctx): registers tools, skills & bg preparation
├── schemas.py               # JSON Schemas for LLM function calling
├── tools.py                 # Tool handler wrappers (search, get_item, locate)
├── location.py              # Dynamic geocoding engine with Spain bounding box checks
├── api_client.py            # Playwright scraper, API interceptor & subprocess bridge
├── skills/
│   └── wallapop/
│       └── SKILL.md         # Bundled agent skill registered with Hermes
├── tests/
│   ├── pytest.ini           # Pytest configuration
│   └── test_tools.py        # 24 unit tests covering all tools and handlers
├── pyproject.toml           # Packaging metadata
├── requirements.txt         # Production dependencies
└── README.md
```

---

## Development & Testing

Clone the repository and install in editable mode:

```bash
git clone https://github.com/Gorkaseto/hermes-wallapop-search-plugin.git
cd hermes-wallapop-search-plugin
pip install -e ".[dev]"
```

Run unit tests:
```bash
pytest tests
```

Execute a direct standalone test query via CLI:
```bash
python api_client.py search '{"query": "nintendo switch", "location": "Madrid", "items_per_page": 2}'
```

---

## License

MIT License — see [LICENSE](LICENSE).

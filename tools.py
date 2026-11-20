"""Wallapop plugin tools - scraping and search functionality.

This plugin declares its Python dependencies (requests, beautifulsoup4, lxml)
in plugin.yaml; Hermes installs them before the plugin is enabled, so the
imports below are expected to be available. playwright is optional and used for
JavaScript-rendered content; see api_client.py.
"""

import json
import re
import logging
import sys
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

import requests
from bs4 import BeautifulSoup

# Import playwright if available
_playwright_available = False
_playwright_working = False

try:
    from playwright.sync_api import sync_playwright
    _playwright_available = True
    
    # Test if playwright actually works
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, timeout=10000)
            browser.close()
            _playwright_working = True
    except:
        pass
except ImportError:
    pass

def _build_search_url(query: str, location: Optional[str] = None, 
                       latitude: Optional[float] = None, 
                       longitude: Optional[float] = None,
                       radius_km: int = 20,
                       min_price: Optional[int] = None,
                       max_price: Optional[int] = None,
                       state: Optional[str] = None,
                       shipping_available: Optional[bool] = None,
                       free_shipping: Optional[bool] = None,
                       category: Optional[str] = None,
                       sort: str = "relevancia",
                       page: int = 1,
                       items_per_page: int = 20) -> str:
    """Build Wallapop search URL with filters."""
    
    base_url = "https://es.wallapop.com/search"
    
    params = [f"query={requests.utils.quote(query)}"]
    
    # Location - either place name or coordinates
    if latitude is not None and longitude is not None:
        params.append(f"latitude={latitude}")
        params.append(f"longitude={longitude}")
        params.append(f"radius={radius_km}")
    elif location:
        params.append(f"location_name={requests.utils.quote(location)}")
    
    # Price range
    if min_price is not None:
        params.append(f"min_price={min_price}")
    if max_price is not None:
        params.append(f"max_price={max_price}")
    
    # State
    if state:
        state_map = {
            "nuevo": "new",
            "usado": "used", 
            "como nuevo": "new",
            "reparable": "repairable"
        }
        if state.lower() in state_map:
            params.append(f"state={state_map[state.lower()]}")
    
    # Shipping
    if free_shipping:
        params.append("shipping=free")
    elif shipping_available is not None:
        params.append(f"shipping={'available' if shipping_available else 'none'}")
    
    # Category (using Wallapop category IDs)
    if category:
        category_ids = {
            "movilidad": "1",
            "telefonia": "1-1",
            "ordenadores": "4",
            "hogar": "8",
            "electrodomesticos": "8",
            "moda": "14",
            "deporte": "16",
            "juguetes": "18",
            "libros": "20",
            "musica": "21",
            "videojuegos": "22",
            "belleza": "25",
            "mascotas": "26",
            "salud": "27",
            "herramientas": "28",
            "artesania": "33",
            "coches": "2",
            "motos": "3"
        }
        if category.lower() in category_ids:
            params.append(f"category_ids={category_ids[category.lower()]}")
    
    # Sort
    sort_map = {
        "relevancia": "relevance",
        "precio_ascendente": "price_asc",
        "precio_descendente": "price_desc",
        "mas_recientes": "newest_first",
        "menos_recientes": "oldest_first"
    }
    if sort.lower() in sort_map:
        params.append(f"sort={sort_map[sort.lower()]}")
    
    # Pagination
    params.append(f"offset={(page - 1) * items_per_page}")
    params.append(f"count={items_per_page}")
    
    return f"{base_url}?{'&'.join(params)}"

def _fetch_with_browser_exec(url: str) -> str:
    """
    Fetch page using Hermes browser_exec tool (JavaScript supported).
    This function should be called via Hermes' browser_exec which provides
    a real browser environment with JavaScript rendering.
    """
    # This will be called via the browser_exec tool
    import asyncio
    from playwright.async_api import async_playwright
    
    async def fetch():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
            })
            await page.goto(url, wait_until='networkidle', timeout=30000)
            html = await page.content()
            await browser.close()
            return html
    
    try:
        return asyncio.run(fetch())
    except Exception as e:
        logger.error(f"Browser exec error: {e}")
        return ""

def _fetch_with_requests(url: str) -> str:
    """Fetch page using requests (may miss JS-rendered content)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://es.wallapop.com/",
    }
    
    session = requests.Session()
    
    try:
        response = session.get(
            url, 
            headers=headers, 
            timeout=30,
            allow_redirects=True
        )
        response.encoding = 'utf-8'
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching page: {e}")
        return ""

def _fetch_with_playwright(url: str) -> str:
    """Fetch page using playwright (requires browser binaries)."""
    if not _playwright_available:
        return ""
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
            })
            page.goto(url, wait_until='networkidle', timeout=30000)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        logger.error(f"Playwright error: {e}")
        return ""

def _extract_items_from_html(html: str) -> List[Dict[str, Any]]:
    """Extract item data from Wallapop HTML using regex patterns."""
    items = []
    
    # Pattern for item cards - Wallapop uses various class names
    item_pattern = r'<a[^>]*href="(/a/(\d+)/[^"]*)"[^>]*>(.*?)</a>'
    
    for match in re.finditer(item_pattern, html, re.DOTALL | re.IGNORECASE):
        full_url = match.group(1)
        item_id = match.group(2)
        content = match.group(3)
        
        if not item_id:
            continue
        
        # Try to extract title from the link content
        title_match = re.search(r'<[^>]+>([^<]+)</[^>]+>', content)
        title = title_match.group(1).strip() if title_match else ""
        
        # Clean title - remove HTML tags and extra whitespace
        title = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', title)).strip()
        
        if not title:
            # Try alternative title pattern
            title_match = re.search(r'"title"\s*:\s*"([^"]+)"', content)
            title = title_match.group(1) if title_match else "Sin título"
        
        items.append({
            "id": item_id,
            "url": f"https://es.wallapop.com{full_url}",
            "title": title,
        })
    
    # Remove duplicates
    seen_ids = set()
    unique_items = []
    for item in items:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            unique_items.append(item)
    
    return unique_items[:50]  # Limit to 50 items

def _parse_search_results(html: str, url: str) -> Dict[str, Any]:
    """Parse search results from Wallapop HTML page."""
    
    # First, check if we got an error page
    if "No results found" in html or "No hay resultados" in html or "nada por aquí" in html.lower():
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "has_more": False,
            "message": "No results found"
        }
    
    # Extract items
    items = _extract_items_from_html(html)
    
    # Try to get total count
    total_match = re.search(r'"total"\s*:\s*(\d+)', html)
    total = int(total_match.group(1)) if total_match else len(items)
    
    # Try to get additional item details from JSON data
    if 'requests' in sys.modules:
        soup = BeautifulSoup(html, 'lxml')
        
        # Look for JSON-LD or data scripts
        for script in soup.find_all('script', type='application/json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    # Check for search results in data
                    for key in ['searchResults', 'items', 'listings']:
                        if key in data:
                            for item_data in data[key]:
                                if isinstance(item_data, dict):
                                    item_id = str(item_data.get('id', ''))
                                    if item_id and not any(i['id'] == item_id for i in items):
                                        item = {
                                            "id": item_id,
                                            "url": item_data.get('url', f"https://es.wallapop.com/a/{item_id}"),
                                            "title": item_data.get('title', item_data.get('name', '')),
                                            "price": item_data.get('price'),
                                            "currency": item_data.get('currency', 'EUR'),
                                            "condition": "nuevo" if item_data.get('is_new') else "usado",
                                            "images": item_data.get('images', [])[:5],
                                            "location": {
                                                "city": item_data.get('city', ''),
                                                "region": item_data.get('region', '')
                                            },
                                            "shipping": {
                                                "available": item_data.get('shipping_available', False),
                                                "free": item_data.get('free_shipping', False)
                                            },
                                        }
                                        if isinstance(item['url'], str) and not item['url'].startswith('http'):
                                            item['url'] = f"https://es.wallapop.com{item['url']}"
                                        items.append(item)
            except (json.JSONDecodeError, TypeError):
                continue
    
    return {
        "items": items,
        "total": total,
        "page": 1,
        "has_more": len(items) > 0,
        "search_url": url
    }

def search_wallapop(args: dict, **kwargs) -> str:
    """
    Search Wallapop with given filters.
    
    Args:
        query: Search query string (required)
        location: Location name or city (e.g., 'Madrid', 'Barcelona')
        latitude: Latitude for coordinate-based search
        longitude: Longitude for coordinate-based search
        radius_km: Search radius in kilometers (default: 20)
        min_price: Minimum price in euros
        max_price: Maximum price in euros
        state: Legacy item condition (nuevo, usado, como nuevo, reparable) - use condition
        condition: Item condition (nuevo, como nuevo, good, fair, has_given_it_all); single value, comma-separated string, or list
        shipping_available: Filter for items with shipping available
        free_shipping: Filter for items with free shipping only
        category: Item category (movilidad, telefonia, ordenadores, hogar, etc.)
        sort: Sort order (relevancia, precio_ascendente, precio_descendente, mas_recientes, menos_recientes)
        page: Page number for pagination (default: 1)
        items_per_page: Number of results per page (default: 20, max: 50)

    Returns:
        JSON string with search results
    """
    try:
        # Import API client
        from .api_client import search_wallapop_api
        
        # Extract parameters
        query = args.get('query', '')
        location = args.get('location')
        latitude = args.get('latitude')
        longitude = args.get('longitude')
        radius_km = args.get('radius_km', 20)
        min_price = args.get('min_price')
        max_price = args.get('max_price')
        state = args.get('state')
        condition = args.get('condition')
        shipping_available = args.get('shipping_available')
        free_shipping = args.get('free_shipping')
        category = args.get('category')
        sort = args.get('sort', 'relevancia')
        page = args.get('page', 1)
        items_per_page = min(args.get('items_per_page', 20), 50)
        
        if not query:
            return json.dumps({"error": "Query parameter is required"})
        
        # Add price filters to query
        if min_price is not None or max_price is not None:
            price_modifier = f" {min_price}-{max_price}" if min_price and max_price else f" {min_price or ''}{max_price or ''}"
            query = f"{query}{price_modifier}".strip()
        
        # Add state filter
        if state:
            state_modifier = "nuevo" if state.lower() == "nuevo" else "usado" if state.lower() == "usado" else ""
            if state_modifier:
                query = f"{query} {state_modifier}"
        
        logger.info(f"Fetching Wallapop search: {query} in {location or 'all locations'} (lat={latitude}, lng={longitude})")
        
        # Extract additional location parameters
        city = args.get('city')
        province = args.get('province')
        community = args.get('community', 'España')
        
        # Use API client with all parameters including location details
        results = search_wallapop_api(
            query=query,
            location=location,
            items_per_page=items_per_page,
            latitude=latitude,
            longitude=longitude,
            city=city,
            province=province,
            community=community,
            radius_km=radius_km,
            min_price=min_price,
            max_price=max_price,
            state=state,
            condition=condition,
            shipping_available=shipping_available,
            free_shipping=free_shipping,
            sort=sort,
            page=page
        )
        
        return json.dumps(results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.exception("Error in search_wallapop")
        return json.dumps({"error": str(e), "type": "search_error"})

def get_item_details(args: dict, **kwargs) -> str:
    """
    Get detailed information about a specific item.
    
    Args:
        item_id: The item ID from a search result
        url: Direct URL to the item
    
    Returns:
        JSON string with item details
    """
    try:
        # Import API client
        from .api_client import get_item_details_api
        
        item_id = args.get('item_id')
        url = args.get('url')
        
        if not item_id and not url:
            return json.dumps({"error": "Either item_id or url is required"})
        
        if not url:
            url = f"https://es.wallapop.com/a/{item_id}"
        
        logger.info(f"Fetching item details: {url}")
        
        # Use API client
        details = get_item_details_api(item_id=item_id, url=url)
        
        if 'error' in details:
            return json.dumps(details, ensure_ascii=False, indent=2)
        
        return json.dumps(details, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.exception("Error in get_item_details")
        return json.dumps({"error": str(e), "type": "detail_error"})
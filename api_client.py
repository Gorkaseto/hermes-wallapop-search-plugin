"""Wallapop API client for direct API access using Playwright."""

import json
import re
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Check if playwright is available
_PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

def _geocode_location(location: str) -> tuple:
    """Get coordinates for a location name using OpenStreetMap."""
    try:
        import urllib.request
        import urllib.parse
        
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(location)}&limit=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data:
                return data[0].get('lat'), data[0].get('lon')
    except Exception as e:
        logger.warning(f"Geocoding failed: {e}")
    
    return None, None

def _set_location_in_localstorage(page, lat: float, lng: float, label: str, city: str, province: str, community: str):
    """Set Wallapop location via localStorage following the required sequence.
    
    Args:
        page: Playwright page object
        lat: Latitude coordinate
        lng: Longitude coordinate  
        label: Full location label (e.g., "Madrid, Madrid, ESP")
        city: City name
        province: Province name
        community: Autonomous community name
    
    Returns:
        bool: True if location was set successfully
    """
    try:
        # Execute the localStorage setup script as specified
        script = f'''
        const lat = {lat};
        const lng = {lng};
        const label = "{label}";
        
        localStorage.setItem("searchLatitude", String(lat));
        localStorage.setItem("searchLongitude", String(lng));
        localStorage.setItem("searchLocationName", label);
        localStorage.setItem("searchLocation", JSON.stringify({{ latitude: String(lat), longitude: String(lng), label }}));
        localStorage.setItem("savedSearchLocation", JSON.stringify({{
            label, title: "{city}", subtitle: "{community}, ESP",
            latitude: lat, longitude: lng, city: "{city}"
        }}));
        true;
        '''
        result = page.evaluate(script)
        return result == True or result == "true"
    except Exception as e:
        logger.error(f"Failed to set location in localStorage: {e}")
        return False

def _verify_location_setup(page, expected_lat: float, expected_lng: float) -> dict:
    """Verify that the location was correctly set in localStorage.
    
    Returns:
        dict with 'success' bool and 'values' dict
    """
    try:
        lat_value = page.evaluate('localStorage.getItem("searchLatitude")')
        lng_value = page.evaluate('localStorage.getItem("searchLongitude")')
        label_value = page.evaluate('localStorage.getItem("searchLocationName")')
        
        lat_ok = lat_value == str(expected_lat)
        lng_ok = lng_value == str(expected_lng)
        
        return {
            'success': lat_ok and lng_ok,
            'values': {
                'searchLatitude': lat_value,
                'searchLongitude': lng_value,
                'searchLocationName': label_value,
                'expected_lat': str(expected_lat),
                'expected_lng': str(expected_lng)
            }
        }
    except Exception as e:
        return {
            'success': False,
            'values': {'error': str(e)}
        }

def _fetch_with_playwright(url: str, location: str = None, 
                           latitude: float = None, longitude: float = None,
                           city: str = None, province: str = None, 
                           community: str = "España",
                           need_reload: bool = True) -> str:
    """Fetch page using Playwright for JavaScript rendering.
    
    If location is provided, sets it via Wallapop's location endpoint.
    Location is set in localStorage before the page is fully loaded.
    
    Args:
        url: The URL to fetch (search results URL)
        location: Location name (optional, for backwards compatibility)
        latitude: Latitude for coordinate-based search
        longitude: Longitude for coordinate-based search
        city: City name (for localStorage setup)
        province: Province name (for localStorage setup)
        community: Autonomous community name (for localStorage setup)
        need_reload: Whether to reload after setting location (default True)
    
    Returns:
        HTML content of the page, or empty string on error
    """
    if not _PLAYWRIGHT_AVAILABLE:
        return ""
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, timeout=60000)
            context = browser.new_context()
            page = context.new_page()
            
            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
            })
            
            # First navigate to Wallapop homepage to initialize
            page.goto("https://es.wallapop.com", wait_until='networkidle', timeout=30000)
            
            # Set location if coordinates are provided (mandatory for location-based search)
            if latitude is not None and longitude is not None:
                label = f"{city}, {province}, ESP" if city and province else location
                
                # Set location in localStorage
                success = _set_location_in_localstorage(
                    page, latitude, longitude, label, 
                    city or "Ciudad", province or "Provincia", community
                )
                
                if not success:
                    logger.warning("Could not set location in localStorage, proceeding with search anyway")
                else:
                    # Verify location was set correctly
                    verification = _verify_location_setup(page, latitude, longitude)
                    if verification['success']:
                        logger.info(f"Location successfully set: {verification['values']}")
                    else:
                        logger.warning(f"Location verification failed: {verification['values']}")
                    
                    # Reload page to apply location changes
                    if need_reload:
                        logger.info("Reloading page to apply location changes")
                        page.reload(wait_until='networkidle', timeout=30000)
            
            # Now navigate to the search URL
            page.goto(url, wait_until='networkidle', timeout=60000)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        logger.error(f"Playwright error: {e}")
        return ""

def search_wallapop_api(query: str = None, location: str = None, items_per_page: int = 15,
                       latitude: float = None, longitude: float = None, city: str = None,
                       province: str = None, community: str = "España",
                       radius_km: int = None, min_price: int = None, max_price: int = None, 
                       state: str = None, shipping_available: bool = None, 
                       free_shipping: bool = None, category: str = None, 
                       sort: str = None, page: int = 1,
                       time_filter: str = None, condition: str = None) -> Dict[str, Any]:
    """Search Wallapop using their web interface and extract data from HTML.
    
    This function establishes location via localStorage before searching,
    following the required sequence for location-based searches.
    
    Args:
        query: Search keywords
        location: Location name (optional, for backwards compatibility)
        items_per_page: Number of results per page (default: 15)
        latitude: Latitude for coordinate-based search
        longitude: Longitude for coordinate-based search
        city: City name (for localStorage setup)
        province: Province name (for localStorage setup)
        community: Autonomous community name (default: "España")
        radius_km: Search radius in kilometers
        min_price: Minimum price filter
        max_price: Maximum price filter
        state: Item condition
        shipping_available: Filter for shipping availability
        free_shipping: Filter for free shipping only
        category: Item category
        sort: Sort order
        page: Page number for pagination
        time_filter: Time filter
        condition: Condition filter
    
    Returns:
        Dict with search results
    """
    
    # Build the search URL using Wallapop's actual parameters
    params = []
    
    # Keywords (main search term)
    if query:
        params.append(f"keywords={quote(query)}")
    
    # Location - use city name
    if location:
        pass  # Location is handled via localStorage in _fetch_with_playwright
    
    # Distance filter
    if radius_km:
        params.append(f"distance_in_km={radius_km}")
    
    # Time filter (today, this_week, etc.)
    if time_filter:
        params.append(f"time_filter={time_filter}")
    
    # Condition (new, used)
    if condition:
        params.append(f"condition={condition}")
    
    # Price range
    if min_price is not None:
        params.append(f"min_sale_price={min_price}")
    if max_price is not None:
        params.append(f"max_sale_price={max_price}")
    
    # Estado (legacy parameter, use 'condition' instead)
    if state:
        state_map = {
            "nuevo": "new",
            "como nuevo": "new"
        }
        if state.lower() in state_map:
            params.append(f"condition={state_map[state.lower()]}")
    
    # Estado (condition) - soporta múltiples valores concatenados con comas
    if condition:
        # Mapa completo de tags de estado
        condition_map = {
            "nuevo": "new",
            "como nuevo": "as_good_as_new",
            "good": "good",
            "fair": "fair",
            "has_given_it_all": "has_given_it_all"
        }
        
        conditions = []
        
        # Si condition es una lista, concatenar valores
        if isinstance(condition, list):
            for c in condition:
                c_lower = c.lower().replace('_', ' ')
                if c_lower in condition_map:
                    conditions.append(condition_map[c_lower])
        # Si condition es una cadena con comas, procesarla
        elif ',' in str(condition):
            for c in str(condition).split(','):
                c_lower = c.lower().strip().replace('_', ' ')
                if c_lower in condition_map:
                    conditions.append(condition_map[c_lower])
        # Si condition es un valor simple
        elif isinstance(condition, str):
            c_lower = condition.lower().replace('_', ' ')
            if c_lower in condition_map:
                conditions.append(condition_map[c_lower])
        
        if conditions:
            params.append(f"condition={','.join(conditions)}")
    
    # Shipping
    if free_shipping:
        params.append("shipping=free")
    elif shipping_available is not None:
        params.append(f"shipping={'available' if shipping_available else 'none'}")
    
    # Order by
    order_map = {
        "relevancia": "most_relevance",
        "price_low_to_high": "price_low_to_high",
        "price_high_to_low": "price_high_to_low",
        "mas_recientes": "newest_first",
        "mas_cercanos": "closest"
    }
    if sort and sort.lower() in order_map:
        params.append(f"order_by={order_map[sort.lower()]}")
    
    # Pagination
    params.append(f"offset={(page - 1) * items_per_page}")
    params.append(f"count={items_per_page}")
    
    # Build URL
    query_string = '&'.join(params)
    url = f"https://es.wallapop.com/search?{query_string}"
    
    logger.info(f"Fetching Wallapop: {url} (location: {location or 'national'}, lat={latitude}, lng={longitude})")
    
    # Use Playwright to fetch the page with location set in localStorage
    html = _fetch_with_playwright(
        url, 
        location=location,
        latitude=latitude,
        longitude=longitude,
        city=city,
        province=province,
        community=community
    )
    
    if not html:
        return {'items': [], 'total': 0, 'page': 1, 'has_more': False, 'message': 'No response'}
    
    # Check if we got actual content
    if len(html) < 10000:
        return {'items': [], 'total': 0, 'page': 1, 'has_more': False, 'message': 'Page too small - may be blocked'}
    
    # Extract items from HTML
    items = []
    
    # Look for __NEXT_DATA__ first
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>', html)
    if match:
        try:
            data = json.loads(match.group(1))
            page_props = data.get('props', {}).get('pageProps', {})
            
            # Try different keys for results
            for key in ['searchResults', 'listings', 'items', 'products', 'results']:
                if key in page_props:
                    items_data = page_props[key]
                    if isinstance(items_data, dict) and 'items' in items_data:
                        items_data = items_data['items']
                    
                    if isinstance(items_data, list):
                        for item_data in items_data[:items_per_page]:
                            if isinstance(item_data, dict):
                                item = {
                                    'id': str(item_data.get('id', '')),
                                    'url': item_data.get('url', f"https://es.wallapop.com/a/{item_data.get('id', '')}"),
                                    'title': item_data.get('title', item_data.get('name', '')),
                                    'price': item_data.get('price'),
                                    'currency': item_data.get('currency', 'EUR'),
                                    'condition': 'nuevo' if item_data.get('is_new') else 'usado',
                                    'images': item_data.get('images', [])[:5],
                                    'location': {
                                        'city': item_data.get('city', ''),
                                        'region': item_data.get('region', '')
                                    },
                                    'shipping': {
                                        'available': item_data.get('shipping_available', False),
                                        'free': item_data.get('free_shipping', False)
                                    },
                                }
                                items.append(item)
                    break
        except (json.JSONDecodeError, TypeError):
            pass
    
    # If no items from __NEXT_DATA__, try to extract from HTML
    if not items:
        # Wallapop uses /item/ URLs for search results
        # Pattern: href="/item/ITEM-NAME-ID" with aria-label or title
        item_pattern = r'<a[^>]*href="(/item/([^"]+))"[^>]*aria-label="([^"]+)"[^>]*>'
        
        for match in re.finditer(item_pattern, html, re.DOTALL | re.IGNORECASE):
            item_path = match.group(1)
            item_slug = match.group(2)
            title = match.group(3)
            
            # Extract ID from slug (last part after hyphen)
            slug_parts = item_slug.split('-')
            item_id = slug_parts[-1] if slug_parts else ''
            
            if item_id:
                items.append({
                    'id': item_id,
                    'url': f"https://es.wallapop.com{item_path}",
                    'title': title,
                })
    
    # Try to get total count
    total = len(items)
    total_match = re.search(r'"total"\s*:\s*(\d+)', html)
    if total_match:
        total = int(total_match.group(1))
    
    return {
        'items': items[:items_per_page],
        'total': total,
        'page': 1,
        'has_more': len(items) > 0,
        'search_url': url
    }

def get_item_details_api(item_id: str, url: str = None) -> Dict[str, Any]:
    """Get item details from Wallapop."""
    
    if not url:
        url = f"https://es.wallapop.com/item/{item_id}"
    
    html = _fetch_with_playwright(url)
    
    if not html:
        return {'error': 'No response'}
    
    # Try to extract from __NEXT_DATA__
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>', html)
    if match:
        try:
            data = json.loads(match.group(1))
            page_props = data.get('props', {}).get('pageProps', {})
            
            for key in ['item', 'listing', 'product']:
                if key in page_props and isinstance(page_props[key], dict):
                    item_data = page_props[key]
                    return {
                        'id': str(item_data.get('id', item_id)),
                        'url': url,
                        'title': item_data.get('title', item_data.get('name', '')),
                        'price': item_data.get('price'),
                        'currency': item_data.get('currency', 'EUR'),
                        'description': item_data.get('description', '')[:1000],
                        'condition': item_data.get('condition', 'usado'),
                        'images': item_data.get('images', []),
                        'seller': {
                            'name': item_data.get('seller_name', ''),
                            'verified': item_data.get('seller_verified', False)
                        },
                        'location': {
                            'city': item_data.get('city', ''),
                            'region': item_data.get('region', '')
                        },
                        'shipping': {
                            'available': item_data.get('shipping_available', False),
                            'free': item_data.get('free_shipping', False)
                        },
                        'status': item_data.get('status', 'disponible'),
                    }
        except (json.JSONDecodeError, TypeError):
            pass
    
    return {'error': 'Could not parse item details'}
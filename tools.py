"""Wallapop plugin tools - scraping and search functionality for Hermes Agent.

Provides the tool handlers:
- `search_wallapop`: Search Wallapop items with full filtering support.
- `get_item_details`: Fetch full details of a specific Wallapop listing.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from . import api_client

logger = logging.getLogger(__name__)


def _build_search_url(
    query: str,
    location: Optional[str] = None,
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
    items_per_page: int = 20,
) -> str:
    """Build Wallapop search URL with query parameters."""
    base_url = "https://es.wallapop.com/search"
    params = [f"query={quote(query)}"]

    if latitude is not None and longitude is not None:
        params.append(f"latitude={latitude}")
        params.append(f"longitude={longitude}")
        params.append(f"radius={radius_km}")
    elif location:
        params.append(f"location_name={quote(location)}")

    if min_price is not None:
        params.append(f"min_price={min_price}")
    if max_price is not None:
        params.append(f"max_price={max_price}")

    if state:
        state_map = {
            "nuevo": "new",
            "usado": "used",
            "como nuevo": "new",
            "reparable": "repairable",
        }
        if state.lower() in state_map:
            params.append(f"state={state_map[state.lower()]}")

    if free_shipping:
        params.append("shipping=free")
    elif shipping_available is not None:
        params.append(f"shipping={'available' if shipping_available else 'none'}")

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
            "motos": "3",
        }
        if category.lower() in category_ids:
            params.append(f"category_ids={category_ids[category.lower()]}")

    sort_map = {
        "relevancia": "relevance",
        "precio_ascendente": "price_asc",
        "precio_descendente": "price_desc",
        "mas_recientes": "newest_first",
        "menos_recientes": "oldest_first",
    }
    if sort.lower() in sort_map:
        params.append(f"sort={sort_map[sort.lower()]}")

    params.append(f"offset={(max(page, 1) - 1) * items_per_page}")
    params.append(f"count={items_per_page}")

    return f"{base_url}?{'&'.join(params)}"


def _parse_input_args(args: Any) -> Dict[str, Any]:
    """Parse tool input arguments ensuring a dict return."""
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {"query": args}
    return {}


def search_wallapop(args: Any, **kwargs) -> str:
    """
    Search Wallapop with given filters.

    Args:
        args: Dict containing search parameters:
            - query (str, required): Search query keywords
            - location (str, optional): City or location name
            - latitude (float, optional): Latitude coordinate
            - longitude (float, optional): Longitude coordinate
            - radius_km (int, default 20): Search radius
            - min_price (int, optional): Minimum price
            - max_price (int, optional): Maximum price
            - condition (str|list, optional): Item condition (nuevo, como nuevo, good, fair, has_given_it_all)
            - state (str, optional): Legacy item condition
            - shipping_available (bool, optional): Filter for items with shipping
            - free_shipping (bool, optional): Filter for free shipping only
            - category (str, optional): Item category
            - sort (str, default 'relevancia'): Sort order
            - page (int, default 1): Page number
            - items_per_page (int, default 20, max 50): Results per page

    Returns:
        JSON string with search results
    """
    try:
        parsed_args = _parse_input_args(args)

        query = parsed_args.get("query", "")
        if not query or not str(query).strip():
            return json.dumps({"error": "Query parameter is required"}, ensure_ascii=False)

        location = parsed_args.get("location")
        latitude = parsed_args.get("latitude")
        longitude = parsed_args.get("longitude")
        radius_km = parsed_args.get("radius_km", 20)
        min_price = parsed_args.get("min_price")
        max_price = parsed_args.get("max_price")
        state = parsed_args.get("state")
        condition = parsed_args.get("condition")
        shipping_available = parsed_args.get("shipping_available")
        free_shipping = parsed_args.get("free_shipping")
        category = parsed_args.get("category")
        sort = parsed_args.get("sort", "relevancia")
        page = parsed_args.get("page", 1)
        items_per_page = min(parsed_args.get("items_per_page", 20), 50)
        city = parsed_args.get("city")
        province = parsed_args.get("province")
        community = parsed_args.get("community", "España")

        logger.info(
            f"Searching Wallapop: query='{query}', location={location or 'national'} "
            f"(coords={latitude}, {longitude})"
        )

        results = api_client.search_wallapop_api(
            query=str(query).strip(),
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
            category=category,
            sort=sort,
            page=page,
        )

        return json.dumps(results, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.exception("Error in search_wallapop")
        return json.dumps({"error": str(e), "type": "search_error"}, ensure_ascii=False)


def get_item_details(args: Any, **kwargs) -> str:
    """
    Get detailed information about a specific Wallapop item.

    Args:
        args: Dict containing:
            - item_id (str, optional): The item ID from a search result
            - url (str, optional): Direct URL to the item

    Returns:
        JSON string with item details
    """
    try:
        parsed_args = _parse_input_args(args)

        item_id = parsed_args.get("item_id")
        url = parsed_args.get("url")

        if not item_id and not url:
            return json.dumps({"error": "Either item_id or url is required"}, ensure_ascii=False)

        logger.info(f"Fetching item details: id={item_id}, url={url}")

        details = api_client.get_item_details_api(item_id=item_id, url=url)
        return json.dumps(details, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.exception("Error in get_item_details")
        return json.dumps({"error": str(e), "type": "detail_error"}, ensure_ascii=False)

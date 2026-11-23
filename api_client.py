"""Wallapop Playwright client for Hermes Agent.

Dedicated Playwright pipeline:
- Bypasses CloudFront WAF and antibot protections.
- Renders client-side Next.js SPA listings dynamically.
- Intercepts `api/v3/search/section` for rich structured data.
- Automatically installs Playwright and Chromium if missing.
"""

import json
import logging
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

logger = logging.getLogger(__name__)

try:
    from .location import resolve_location, is_valid_spain_coords
except (ImportError, ValueError):
    from location import resolve_location, is_valid_spain_coords

# Backward-compatible wrapper
def resolve_coordinates(
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Tuple[Optional[float], Optional[float]]:
    """Resolve latitude and longitude coordinates."""
    info = resolve_location(location=location, latitude=latitude, longitude=longitude)
    return info.get("latitude"), info.get("longitude")

# Category IDs mapping
CATEGORY_MAP: Dict[str, str] = {
    "movilidad": "1",
    "patinetes": "1",
    "coches": "2",
    "motor": "2",
    "motos": "3",
    "motor-y-accesorios": "12463",
    "motor y accesorios": "12463",
    "telefonia": "16",
    "telefonos": "16",
    "móviles": "16",
    "moviles": "16",
    "ordenadores": "4",
    "informatica": "4",
    "informática": "4",
    "electronica": "5",
    "electrónica": "5",
    "audio": "5",
    "tv": "5",
    "hogar": "8",
    "electrodomesticos": "8",
    "electrodomésticos": "8",
    "decoracion": "8",
    "decoración": "8",
    "moda": "14",
    "ropa": "14",
    "calzado": "14",
    "deporte": "16",
    "ocio": "16",
    "juguetes": "18",
    "bebes": "18",
    "bebés": "18",
    "libros": "20",
    "peliculas": "20",
    "películas": "20",
    "musica": "21",
    "música": "21",
    "instrumentos": "21",
    "videojuegos": "22",
    "consolas": "22",
    "belleza": "25",
    "mascotas": "26",
    "salud": "27",
    "herramientas": "28",
    "artesania": "33",
    "artesanía": "33",
    "inmobiliaria": "12",
}

# Condition values mapping
CONDITION_MAP: Dict[str, str] = {
    "nuevo": "new",
    "new": "new",
    "como nuevo": "as_good_as_new",
    "como_nuevo": "as_good_as_new",
    "as_good_as_new": "as_good_as_new",
    "good": "good",
    "buen estado": "good",
    "bueno": "good",
    "fair": "fair",
    "aceptable": "fair",
    "has_given_it_all": "has_given_it_all",
    "lo ha dado todo": "has_given_it_all",
    "lo_ha_dado_todo": "has_given_it_all",
    "para piezas": "has_given_it_all",
    "usado": "used",
    "used": "used",
}

# Sort order mapping
ORDER_MAP: Dict[str, str] = {
    "relevancia": "most_relevance",
    "relevance": "most_relevance",
    "most_relevance": "most_relevance",
    "price_low_to_high": "price_low_to_high",
    "precio_ascendente": "price_low_to_high",
    "price_high_to_low": "price_high_to_low",
    "precio_descendente": "price_high_to_low",
    "mas_recientes": "newest_first",
    "newest_first": "newest_first",
    "mas_cercanos": "closest",
    "closest": "closest",
}


def _find_and_register_hermes_site_packages() -> bool:
    """Discover site-packages from Hermes tools/environments and add to sys.path if playwright is there."""
    import glob
    import os
    import sys

    try:
        import playwright
        return True
    except ImportError:
        pass

    search_patterns = [
        os.path.expanduser("~/.hermes/tools/**/site-packages"),
        os.path.expanduser("~/.hermes/installs/**/site-packages"),
        os.path.expanduser("~/.hermes/environments/**/site-packages"),
        os.path.expanduser("~/.hermes/**/lib/python*/site-packages"),
        os.path.expanduser("~/.hermes/**/site-packages"),
    ]
    for pat in search_patterns:
        try:
            for sp in glob.glob(pat, recursive=True):
                if os.path.isdir(sp) and sp not in sys.path:
                    pw_dir = os.path.join(sp, "playwright")
                    if os.path.isdir(pw_dir):
                        logger.info(f"Discovered Playwright site-packages in Hermes: {sp}")
                        sys.path.insert(0, sp)
                        try:
                            import playwright
                            return True
                        except Exception as e:
                            logger.debug(f"Found playwright in {sp} but import failed: {e}")
        except Exception:
            pass
    return False


def get_playwright_python_executable() -> Optional[str]:
    """Find a Python interpreter that has Playwright installed and working."""
    import glob
    import os
    import shutil
    import subprocess
    import sys

    # 1. Check if current interpreter has it
    try:
        import playwright
        return sys.executable
    except ImportError:
        if _find_and_register_hermes_site_packages():
            return sys.executable

    # 2. Search for external Python executables in Hermes directories
    candidates: List[str] = []
    hermes_patterns = [
        os.path.expanduser("~/.hermes/tools/**/bin/python*"),
        os.path.expanduser("~/.hermes/tools/**/python*"),
        os.path.expanduser("~/.hermes/installs/**/bin/python*"),
        os.path.expanduser("~/.hermes/installs/**/python*"),
    ]
    for pat in hermes_patterns:
        try:
            for p in glob.glob(pat, recursive=True):
                if os.path.isfile(p) and (os.access(p, os.X_OK) or p.endswith(".exe")):
                    real = os.path.realpath(p)
                    if real not in candidates and not real.endswith("-config"):
                        candidates.append(real)
        except Exception:
            pass

    for name in ["python3", "python"]:
        found = shutil.which(name)
        if found and found not in candidates:
            candidates.append(found)

    for cand in candidates:
        try:
            res = subprocess.run(
                [cand, "-c", "import playwright; print('PLAYWRIGHT_OK')"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "PLAYWRIGHT_OK" in res.stdout:
                logger.info(f"Found working Playwright in Python interpreter: {cand}")
                return cand
        except Exception:
            continue

    return None


def is_chromium_installed() -> bool:
    """Check if Chromium browser binary is present in ms-playwright directory."""
    import glob
    import os

    search_dirs = [
        os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright"),
        os.path.expanduser("~/.cache/ms-playwright"),
        os.path.expanduser("~/Library/Caches/ms-playwright"),
    ]
    custom_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if custom_path:
        search_dirs.insert(0, custom_path)

    for d in search_dirs:
        if os.path.isdir(d):
            matches = glob.glob(os.path.join(d, "chromium*"))
            if matches:
                return True
    return False


def ensure_playwright_installed() -> bool:
    """Ensure that the playwright package and chromium browser binaries are installed."""
    import shutil
    import subprocess
    import sys

    # 1. Discover existing site-packages if playwright is already installed in Hermes
    _find_and_register_hermes_site_packages()

    # 2. Check if playwright python package is installed in current interpreter or Hermes interpreter
    py_exec = get_playwright_python_executable() or sys.executable

    has_pkg = False
    try:
        import playwright
        has_pkg = True
    except ImportError:
        pass

    if not has_pkg:
        try:
            res = subprocess.run(
                [py_exec, "-c", "import playwright; print('OK')"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "OK" in res.stdout:
                has_pkg = True
        except Exception:
            pass

    if not has_pkg:
        logger.info(f"Playwright python package not found. Installing via {py_exec}...")
        installed = False
        uv_bin = shutil.which("uv")
        if uv_bin:
            try:
                subprocess.check_call([uv_bin, "pip", "install", "--python", py_exec, "playwright>=1.40,<2"])
                installed = True
            except Exception:
                pass

        if not installed:
            try:
                subprocess.check_call(
                    [py_exec, "-m", "pip", "install", "--break-system-packages", "playwright>=1.40,<2"]
                )
                installed = True
            except Exception:
                try:
                    subprocess.check_call(
                        [py_exec, "-m", "pip", "install", "playwright>=1.40,<2"]
                    )
                    installed = True
                except Exception as e:
                    logger.error(f"Failed to install playwright package: {e}")
                    return False

        _find_and_register_hermes_site_packages()

    # 3. Check if chromium binary is installed
    if not is_chromium_installed():
        logger.info("Chromium binary not found. Running 'playwright install chromium'...")
        target_py = get_playwright_python_executable() or py_exec
        try:
            subprocess.check_call(
                [target_py, "-m", "playwright", "install", "chromium"]
            )
        except Exception:
            pw_cmd = shutil.which("playwright")
            if pw_cmd:
                try:
                    subprocess.check_call([pw_cmd, "install", "chromium"])
                except Exception as e:
                    logger.error(f"Failed to install chromium binary: {e}")
                    return False
            else:
                return False

    return True


def _run_search_via_subprocess(target_py: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Execute search_wallapop_api via another Python interpreter that has Playwright."""
    import os
    import subprocess

    this_file = os.path.abspath(__file__)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(this_file) + os.pathsep + env.get("PYTHONPATH", "")

    try:
        res = subprocess.run(
            [target_py, this_file, "search", json.dumps(kwargs)],
            capture_output=True,
            text=True,
            env=env,
            timeout=40,
        )
        if res.returncode == 0 and res.stdout.strip():
            lines = res.stdout.strip().split("\n")
            for line in reversed(lines):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    return json.loads(line)
            return json.loads(res.stdout)
        else:
            err = res.stderr or res.stdout or f"Process exited with code {res.returncode}"
            logger.error(f"External Playwright process failed: {err}")
            return {"error": f"External Playwright search failed: {err}", "items": [], "total": 0}
    except Exception as e:
        logger.error(f"Failed to execute external Playwright search: {e}")
        return {"error": str(e), "items": [], "total": 0}


def _run_item_via_subprocess(target_py: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Execute get_item_details_api via another Python interpreter that has Playwright."""
    import os
    import subprocess

    this_file = os.path.abspath(__file__)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(this_file) + os.pathsep + env.get("PYTHONPATH", "")

    try:
        res = subprocess.run(
            [target_py, this_file, "item", json.dumps(kwargs)],
            capture_output=True,
            text=True,
            env=env,
            timeout=40,
        )
        if res.returncode == 0 and res.stdout.strip():
            lines = res.stdout.strip().split("\n")
            for line in reversed(lines):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    return json.loads(line)
            return json.loads(res.stdout)
        else:
            err = res.stderr or res.stdout or f"Process exited with code {res.returncode}"
            logger.error(f"External Playwright process failed: {err}")
            return {"error": f"External Playwright get_item failed: {err}"}
    except Exception as e:
        logger.error(f"Failed to execute external Playwright get_item: {e}")
        return {"error": str(e)}


def _normalize_condition(condition: Any, state: Optional[str] = None) -> Optional[str]:
    """Normalize condition/state filter to Wallapop condition values."""
    raw_val = condition if condition is not None else state
    if not raw_val:
        return None

    values: List[str] = []
    if isinstance(raw_val, list):
        items = raw_val
    elif "," in str(raw_val):
        items = str(raw_val).split(",")
    else:
        items = [str(raw_val)]

    for item in items:
        clean = str(item).strip().lower().replace("-", " ").replace("_", " ")
        if clean in CONDITION_MAP:
            mapped = CONDITION_MAP[clean]
            if mapped not in values:
                values.append(mapped)

    return ",".join(values) if values else None


def _format_search_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Format an item dictionary into a consistent search result schema."""
    item_id = str(raw.get("id") or "")
    web_slug = raw.get("web_slug") or raw.get("webSlug") or raw.get("slug") or ""
    if web_slug:
        url = f"https://es.wallapop.com/item/{web_slug}"
    elif item_id:
        url = f"https://es.wallapop.com/item/{item_id}"
    else:
        url = raw.get("url") or ""

    # Title
    raw_title = raw.get("title") or raw.get("name") or ""
    if isinstance(raw_title, dict):
        title = raw_title.get("original") or raw_title.get("translated") or ""
    else:
        title = str(raw_title)

    # Description
    raw_desc = raw.get("description") or ""
    if isinstance(raw_desc, dict):
        description = raw_desc.get("original") or raw_desc.get("translated") or ""
    else:
        description = str(raw_desc)

    # Normalize images
    raw_images = raw.get("images") or []
    images: List[str] = []
    if isinstance(raw_images, list):
        for img in raw_images:
            if isinstance(img, str):
                images.append(img)
            elif isinstance(img, dict):
                urls = img.get("urls") or {}
                src = (
                    urls.get("big")
                    or urls.get("medium")
                    or urls.get("small")
                    or img.get("original")
                    or img.get("url")
                    or img.get("medium")
                    or img.get("originalUrl")
                    or ""
                )
                if src:
                    images.append(src)
    elif isinstance(raw_images, dict):
        urls = raw_images.get("urls") or {}
        src = (
            urls.get("big")
            or urls.get("medium")
            or urls.get("small")
            or raw_images.get("original")
            or raw_images.get("url")
            or ""
        )
        if src:
            images.append(src)

    # Location
    loc_data = raw.get("location") or {}
    if isinstance(loc_data, dict):
        city = loc_data.get("city") or raw.get("city") or ""
        postal_code = loc_data.get("postal_code") or loc_data.get("postalCode") or loc_data.get("zip") or ""
        region = loc_data.get("region") or loc_data.get("region2") or ""
    else:
        city = str(loc_data)
        postal_code = ""
        region = ""

    # Shipping
    shipping_data = raw.get("shipping") or {}
    if isinstance(shipping_data, dict):
        shipping_available = (
            shipping_data.get("user_allows_shipping")
            or shipping_data.get("item_is_shippable")
            or shipping_data.get("isItemShippable")
            or shipping_data.get("isShippingAllowedByUser")
            or shipping_data.get("available")
            or False
        )
        shipping_cost = shipping_data.get("cost")
        free_shipping = shipping_data.get("free", False) or shipping_cost == 0
    else:
        shipping_available = bool(raw.get("shipping_available"))
        shipping_cost = None
        free_shipping = bool(raw.get("free_shipping"))

    # Seller
    user_data = raw.get("user") or raw.get("seller") or raw.get("itemSeller") or {}
    seller = {
        "id": str(user_data.get("id") or raw.get("userId") or ""),
        "name": user_data.get("micro_name") or user_data.get("microName") or user_data.get("name") or "",
        "verified": bool(user_data.get("verification", {}).get("phone") or user_data.get("verified")),
    }

    # Price
    price_val = raw.get("price")
    if isinstance(price_val, dict):
        if "cash" in price_val and isinstance(price_val["cash"], dict):
            price = price_val["cash"].get("amount") or price_val["cash"].get("value")
            currency = price_val["cash"].get("currency", "EUR")
        else:
            price = price_val.get("amount") or price_val.get("value")
            currency = price_val.get("currency", "EUR")
    else:
        price = price_val
        currency = raw.get("currency", "EUR")

    # Condition
    raw_cond = raw.get("condition")
    if isinstance(raw_cond, dict):
        condition = raw_cond.get("text") or raw_cond.get("title") or raw_cond.get("value") or "usado"
    elif raw_cond:
        condition = str(raw_cond)
    elif raw.get("characteristics"):
        condition = str(raw.get("characteristics"))
    else:
        condition = "nuevo" if raw.get("is_new") else "usado"

    return {
        "id": item_id,
        "url": url,
        "title": title,
        "price": price,
        "currency": currency,
        "description": description[:1000],
        "condition": condition,
        "images": images[:10],
        "location": {
            "city": city,
            "region": region,
            "postal_code": postal_code,
        },
        "shipping": {
            "available": shipping_available,
            "free": free_shipping,
        },
        "seller": seller,
    }


def search_wallapop_api(
    query: Optional[str] = None,
    location: Optional[str] = None,
    items_per_page: int = 20,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    city: Optional[str] = None,
    province: Optional[str] = None,
    community: str = "España",
    radius_km: Optional[int] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    state: Optional[str] = None,
    shipping_available: Optional[bool] = None,
    free_shipping: Optional[bool] = None,
    category: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = 1,
    time_filter: Optional[str] = None,
    condition: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Search Wallapop items using Playwright pipeline.
    """
    if not query:
        return {"error": "Query parameter is required", "items": [], "total": 0}

    # Ensure Playwright and Chromium are ready
    if not ensure_playwright_installed():
        return {
            "error": "Playwright/Chromium could not be initialized or installed",
            "items": [],
            "total": 0,
        }

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        target_py = get_playwright_python_executable()
        import os
        if target_py and os.path.realpath(target_py) != os.path.realpath(sys.executable):
            logger.info(f"Delegating Wallapop search to Python interpreter: {target_py}")
            return _run_search_via_subprocess(target_py, {
                "query": query,
                "location": location,
                "items_per_page": items_per_page,
                "latitude": latitude,
                "longitude": longitude,
                "city": city,
                "province": province,
                "community": community,
                "radius_km": radius_km,
                "min_price": min_price,
                "max_price": max_price,
                "state": state,
                "shipping_available": shipping_available,
                "free_shipping": free_shipping,
                "category": category,
                "sort": sort,
                "page": page,
                "time_filter": time_filter,
                "condition": condition,
            })
        return {
            "error": "Playwright module could not be imported in Python environment",
            "items": [],
            "total": 0,
        }

    # Resolve reliable coordinates and metadata
    loc_info = resolve_location(
        location=location or city,
        latitude=latitude,
        longitude=longitude,
        city=city,
        province=province,
        community=community,
    )
    resolved_lat = loc_info.get("latitude")
    resolved_lng = loc_info.get("longitude")
    resolved_label = loc_info.get("label") or "España"
    resolved_city = loc_info.get("city") or "Ciudad"
    resolved_province = loc_info.get("province") or "España"
    resolved_community = loc_info.get("community") or "España"

    # Build web parameters
    web_params: Dict[str, Any] = {
        "keywords": query,
    }

    if resolved_lat is not None and resolved_lng is not None:
        web_params["latitude"] = str(resolved_lat)
        web_params["longitude"] = str(resolved_lng)
        if radius_km:
            web_params["distance_in_km"] = str(radius_km)

    if min_price is not None:
        web_params["min_sale_price"] = str(min_price)
    if max_price is not None:
        web_params["max_sale_price"] = str(max_price)

    if category:
        cat_key = category.lower().strip()
        cat_id = CATEGORY_MAP.get(cat_key, cat_key)
        web_params["category_ids"] = cat_id

    cond_val = _normalize_condition(condition, state)
    if cond_val:
        web_params["condition"] = cond_val

    if free_shipping:
        web_params["shipping"] = "free"
    elif shipping_available is not None:
        web_params["shipping"] = "available" if shipping_available else "none"

    if sort:
        sort_clean = sort.lower().strip()
        web_params["order_by"] = ORDER_MAP.get(sort_clean, sort_clean)

    offset = (max(page, 1) - 1) * items_per_page
    web_params["offset"] = str(offset)
    web_params["count"] = str(items_per_page)

    search_url = f"https://es.wallapop.com/search?{requests_quote_params(web_params)}"

    intercepted_items: List[Dict[str, Any]] = []

    def handle_response(response):
        try:
            resp_url = response.url
            if "api/v3/search/section" in resp_url:
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    data = response.json()
                    sec = data.get("data", {}).get("section", {})
                    items = sec.get("items", [])
                    if isinstance(items, list) and items:
                        for it in items:
                            if isinstance(it, dict):
                                intercepted_items.append(_format_search_item(it))
        except Exception:
            pass

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                timeout=25000,
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="es-ES",
                viewport={"width": 1280, "height": 800},
            )
            page_obj = context.new_page()
            page_obj.on("response", handle_response)

            # Establish session cookies
            page_obj.goto("https://es.wallapop.com", wait_until="domcontentloaded", timeout=20000)

            # Apply location setup in localStorage if coordinates given
            if resolved_lat is not None and resolved_lng is not None:
                page_obj.evaluate(f"""
                    localStorage.setItem("searchLatitude", "{resolved_lat}");
                    localStorage.setItem("searchLongitude", "{resolved_lng}");
                    localStorage.setItem("searchLocationName", "{resolved_label}");
                    localStorage.setItem("savedSearchLocation", JSON.stringify({{
                        label: "{resolved_label}", title: "{resolved_city}", subtitle: "{resolved_province}, ESP",
                        latitude: {resolved_lat}, longitude: {resolved_lng}, city: "{resolved_city}"
                    }}));
                """)

            page_obj.goto(search_url, wait_until="domcontentloaded", timeout=25000)
            page_obj.wait_for_timeout(3000)

            if intercepted_items:
                browser.close()
                return {
                    "items": intercepted_items[:items_per_page],
                    "total": len(intercepted_items),
                    "page": page,
                    "has_more": len(intercepted_items) >= items_per_page,
                    "location_resolved": loc_info,
                    "search_url": search_url,
                }

            # DOM extraction fallback
            dom_items = page_obj.evaluate("""() => {
                const results = [];
                const links = document.querySelectorAll('a[href*="/item/"]');
                const seen = new Set();
                for (const link of links) {
                    const href = link.getAttribute('href');
                    if (!href || seen.has(href)) continue;
                    seen.add(href);
                    
                    const card = link.closest('article') || link.parentElement || link;
                    const text = card.innerText || '';
                    const img = card.querySelector('img');
                    const imgSrc = img ? (img.getAttribute('src') || img.getAttribute('data-src')) : null;
                    const priceMatch = text.match(/([0-9.,]+)\\s*€/);
                    const price = priceMatch ? priceMatch[1] : null;
                    const title = link.getAttribute('aria-label') || link.getAttribute('title') || (text.split('\\n')[0]);
                    
                    results.push({
                        url: 'https://es.wallapop.com' + href,
                        id: href.split('-').pop() || '',
                        title: title ? title.trim() : '',
                        price: price,
                        images: imgSrc ? [imgSrc] : []
                    });
                }
                return results;
            }""")

            browser.close()

            items = [_format_search_item(d) for d in dom_items]
            return {
                "items": items[:items_per_page],
                "total": len(items),
                "page": page,
                "has_more": len(items) >= items_per_page,
                "location_resolved": loc_info,
                "search_url": search_url,
            }

    except Exception as e:
        logger.error(f"Playwright search failed: {e}")
        return {
            "error": str(e),
            "items": [],
            "total": 0,
            "search_url": search_url,
        }


def get_item_details_api(item_id: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
    """Get full item details by item ID or URL using Playwright."""
    if not item_id and not url:
        return {"error": "Either item_id or url is required"}

    if not ensure_playwright_installed():
        return {"error": "Playwright/Chromium could not be initialized or installed"}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        target_py = get_playwright_python_executable()
        import os
        if target_py and os.path.realpath(target_py) != os.path.realpath(sys.executable):
            logger.info(f"Delegating Wallapop get_item to Python interpreter: {target_py}")
            return _run_item_via_subprocess(target_py, {
                "item_id": item_id,
                "url": url,
            })
        return {"error": "Playwright module could not be imported in Python environment"}

    clean_id = str(item_id).strip() if item_id else ""
    if not clean_id and url:
        m = re.search(r"/(?:item|a)/([a-zA-Z0-9_-]+)", url)
        if m:
            slug = m.group(1)
            parts = slug.split("-")
            clean_id = parts[-1] if parts else slug

    item_url = url or f"https://es.wallapop.com/item/{clean_id}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                timeout=25000,
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="es-ES",
            )
            page = context.new_page()
            page.goto("https://es.wallapop.com", wait_until="domcontentloaded", timeout=15000)
            page.goto(item_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(2000)

            item_details = page.evaluate("""() => {
                const nextScript = document.getElementById('__NEXT_DATA__');
                if (nextScript) {
                    try {
                        const data = JSON.parse(nextScript.innerText);
                        const props = data.props && data.props.pageProps ? data.props.pageProps : {};
                        for (const key of ['item', 'listing', 'product']) {
                            if (props[key]) {
                                const it = Object.assign({}, props[key]);
                                if (props.itemSeller) it.user = props.itemSeller;
                                return it;
                            }
                        }
                    } catch(e) {}
                }
                
                // DOM extraction fallback
                const titleEl = document.querySelector('h1') || document.querySelector('[class*="item-detail_ItemDetail__title"]');
                const priceEl = document.querySelector('[class*="item-detail_ItemDetail__price"]') || document.querySelector('[class*="price"]');
                const descEl = document.querySelector('[class*="item-detail_ItemDetail__description"]') || document.querySelector('p');
                const imgs = Array.from(document.querySelectorAll('img')).map(i => i.src).filter(s => s && s.includes('wallapop.com/images'));
                
                return {
                    title: titleEl ? titleEl.innerText : '',
                    price: priceEl ? priceEl.innerText : null,
                    description: descEl ? descEl.innerText : '',
                    images: imgs
                };
            }""")
            browser.close()

            if item_details and (item_details.get("title") or item_details.get("price") or item_details.get("id")):
                res = _format_search_item(item_details)
                res["id"] = clean_id or res.get("id", "")
                res["url"] = item_url
                res["status"] = item_details.get("status", "disponible")
                return res

    except Exception as e:
        logger.error(f"Playwright get_item_details failed: {e}")
        return {"error": str(e), "item_id": clean_id, "url": item_url}

    return {
        "error": "Could not retrieve item details",
        "item_id": clean_id,
        "url": item_url,
    }


def requests_quote_params(params: Dict[str, Any]) -> str:
    """Helper to encode params dictionary to URL query string."""
    parts = []
    for k, v in params.items():
        if v is not None:
            parts.append(f"{quote(str(k))}={quote(str(v))}")
    return "&".join(parts)


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        mode = sys.argv[1]
        args_payload = json.loads(sys.argv[2])
        if mode == "search":
            result = search_wallapop_api(**args_payload)
        elif mode == "item":
            result = get_item_details_api(**args_payload)
        else:
            result = {"error": f"Unknown mode: {mode}"}
        print(json.dumps(result, ensure_ascii=False))

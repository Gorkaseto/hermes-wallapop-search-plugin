"""Dynamic geocoding and location resolution engine for Wallapop Spain.

Pure online geocoding pipeline (no hardcoded offline catalogs):
1. Coordinates validation (rejects invalid/hallucinated LLM coordinates outside Spain).
2. Fast geocoding via Photon (OpenStreetMap data) with countrycode=es.
   Resolves cities, towns, neighborhoods, and 5-digit postal codes dynamically.
3. Nominatim fallback with countrycodes=es.
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote
import urllib.request

logger = logging.getLogger(__name__)

# Bounding box for Spain (Canary Islands, Balearic Islands, Ceuta, Melilla, Península)
SPAIN_LAT_MIN, SPAIN_LAT_MAX = 27.5, 44.2
SPAIN_LNG_MIN, SPAIN_LNG_MAX = -18.5, 4.5

# Default national center coordinates when no location is provided
DEFAULT_NATIONAL_LOCATION: Dict[str, Any] = {
    "latitude": 40.4168,
    "longitude": -3.7038,
    "city": "Madrid",
    "province": "Madrid",
    "community": "España",
    "postal_code": "",
    "label": "Madrid, Madrid, ESP",
    "source": "default_national",
}


def is_valid_spain_coords(lat: Optional[float], lng: Optional[float]) -> bool:
    """Validate that coordinates fall within the geographical territory of Spain."""
    if lat is None or lng is None:
        return False
    try:
        f_lat = float(lat)
        f_lng = float(lng)
        return SPAIN_LAT_MIN <= f_lat <= SPAIN_LAT_MAX and SPAIN_LNG_MIN <= f_lng <= SPAIN_LNG_MAX
    except (ValueError, TypeError):
        return False


def geocode_photon(query: str) -> Optional[Dict[str, Any]]:
    """
    Fast online geocoder via Photon by Komoot (OpenStreetMap data).
    Resolves municipalities, postal codes, neighborhoods, and streets dynamically.
    """
    try:
        url = f"https://photon.komoot.io/api/?q={quote(query)}&countrycode=es&limit=1"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "HermesWallapopLocation/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            features = data.get("features", [])
            if features:
                f = features[0]
                coords = f.get("geometry", {}).get("coordinates", [])
                if len(coords) >= 2:
                    lng, lat = coords[0], coords[1]
                    if is_valid_spain_coords(lat, lng):
                        props = f.get("properties", {})
                        city = props.get("city") or props.get("name") or query
                        state = props.get("state") or props.get("county") or "España"
                        postcode = props.get("postcode") or ""
                        return {
                            "latitude": float(lat),
                            "longitude": float(lng),
                            "city": str(city),
                            "province": str(state),
                            "community": "España",
                            "postal_code": str(postcode),
                            "label": f"{city}, {state}, ESP",
                            "source": "photon",
                        }
    except Exception as e:
        logger.debug(f"Photon geocoding failed for '{query}': {e}")
    return None


def geocode_nominatim(query: str) -> Optional[Dict[str, Any]]:
    """Online geocoding fallback via OpenStreetMap Nominatim."""
    try:
        url = (
            "https://nominatim.openstreetmap.org/search?format=json&q="
            f"{quote(query)}&countrycodes=es&limit=1"
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "HermesWallapopLocation/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and len(data) > 0:
                item = data[0]
                lat = float(item.get("lat"))
                lng = float(item.get("lon"))
                if is_valid_spain_coords(lat, lng):
                    name = item.get("display_name", "").split(",")[0] or query
                    return {
                        "latitude": lat,
                        "longitude": lng,
                        "city": name,
                        "province": "España",
                        "community": "España",
                        "postal_code": "",
                        "label": f"{name}, España",
                        "source": "nominatim",
                    }
    except Exception as e:
        logger.debug(f"Nominatim geocoding failed for '{query}': {e}")
    return None


def resolve_location(
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    city: Optional[str] = None,
    province: Optional[str] = None,
    community: str = "España",
) -> Dict[str, Any]:
    """
    Resolve reliable coordinates and location metadata for Wallapop searches.

    Resolution order:
    1. Check if explicit lat/lng was provided AND is valid within Spain.
       (If invalid/hallucinated by LLM, ignores them and proceeds to geocode location text).
    2. Dynamic geocoding via Photon API (OpenStreetMap) with countrycode=es.
    3. Dynamic geocoding fallback via Nominatim API.
    4. National default fallback (Madrid).
    """
    # 1. Validate explicit coordinates if supplied
    if latitude is not None and longitude is not None:
        if is_valid_spain_coords(latitude, longitude):
            c_name = city or location or "Ubicación seleccionada"
            p_name = province or "España"
            return {
                "latitude": float(latitude),
                "longitude": float(longitude),
                "city": c_name,
                "province": p_name,
                "community": community or "España",
                "postal_code": "",
                "label": f"{c_name}, {p_name}, ESP",
                "source": "coordinates_override",
            }
        else:
            logger.warning(
                f"Supplied coordinates ({latitude}, {longitude}) are outside Spain. "
                "Rejecting potentially hallucinated coordinates and resolving from location text instead."
            )

    search_query = location or city or ""
    if not search_query.strip():
        return dict(DEFAULT_NATIONAL_LOCATION)

    clean_query = search_query.strip()

    # 2. Dynamic geocoding via Photon
    res = geocode_photon(clean_query)
    if res:
        return res

    # 3. Dynamic geocoding via Nominatim
    res = geocode_nominatim(clean_query)
    if res:
        return res

    # 4. Fallback if geocoding fails or is offline
    logger.warning(f"Could not resolve coordinates for '{clean_query}'. Using default national coordinates.")
    return {
        "latitude": 40.4168,
        "longitude": -3.7038,
        "city": clean_query,
        "province": province or "España",
        "community": community or "España",
        "postal_code": "",
        "label": f"{clean_query}, ESP",
        "source": "fallback",
    }

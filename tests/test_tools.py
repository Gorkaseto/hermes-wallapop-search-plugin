# Tests for the Wallapop plugin for Hermes Agent.
#
# Run after `pip install -e .` (the package is importable as `wallapop`):
#   pytest tests/

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


class TestSearchWallapop:
    """Tests for the search_wallapop handler."""

    def test_search_requires_query(self):
        from wallapop.tools import search_wallapop
        data = json.loads(search_wallapop({}))
        assert "error" in data
        assert "Query parameter is required" in data["error"]

    def test_search_with_empty_string_query(self):
        from wallapop.tools import search_wallapop
        data = json.loads(search_wallapop({"query": "   "}))
        assert "error" in data
        assert "Query parameter is required" in data["error"]

    @patch("wallapop.api_client.search_wallapop_api")
    def test_search_with_query(self, mock_api):
        from wallapop.tools import search_wallapop
        mock_api.return_value = {"items": [{"id": "123", "title": "Test Item"}], "total": 1}
        data = json.loads(search_wallapop({"query": "test"}))
        assert "items" in data
        assert len(data["items"]) == 1

    @patch("wallapop.api_client.search_wallapop_api")
    def test_search_with_json_string_arg(self, mock_api):
        from wallapop.tools import search_wallapop
        mock_api.return_value = {"items": [{"id": "456", "title": "Bicicleta"}], "total": 1}
        data = json.loads(search_wallapop(json.dumps({"query": "bicicleta"})))
        assert "items" in data
        assert len(data["items"]) == 1

    @patch("wallapop.api_client.search_wallapop_api")
    def test_search_with_filters(self, mock_api):
        from wallapop.tools import search_wallapop
        mock_api.return_value = {"items": [], "total": 0}
        search_wallapop({
            "query": "iPhone",
            "min_price": 100,
            "max_price": 400,
            "category": "telefonia",
            "condition": "como nuevo",
            "location": "Valencia",
        })
        mock_api.assert_called_once()
        kwargs = mock_api.call_args.kwargs
        assert kwargs["query"] == "iPhone"
        assert kwargs["min_price"] == 100
        assert kwargs["max_price"] == 400
        assert kwargs["category"] == "telefonia"
        assert kwargs["condition"] == "como nuevo"
        assert kwargs["location"] == "Valencia"


class TestGetItemDetails:
    """Tests for the get_item_details handler."""

    def test_get_item_requires_id_or_url(self):
        from wallapop.tools import get_item_details
        data = json.loads(get_item_details({}))
        assert "error" in data
        assert "Either item_id or url is required" in data["error"]

    @patch("wallapop.api_client.get_item_details_api")
    def test_get_item_by_id(self, mock_api):
        from wallapop.tools import get_item_details
        mock_api.return_value = {
            "id": "item123",
            "title": "Vintage Lamp",
            "price": 25.0,
            "currency": "EUR",
        }
        data = json.loads(get_item_details({"item_id": "item123"}))
        assert data["id"] == "item123"
        assert data["title"] == "Vintage Lamp"

    @patch("wallapop.api_client.get_item_details_api")
    def test_get_item_by_url(self, mock_api):
        from wallapop.tools import get_item_details
        mock_api.return_value = {
            "id": "lamp123",
            "url": "https://es.wallapop.com/item/vintage-lamp-lamp123",
            "title": "Vintage Lamp",
        }
        data = json.loads(get_item_details({"url": "https://es.wallapop.com/item/vintage-lamp-lamp123"}))
        assert data["id"] == "lamp123"


class TestBuildSearchURL:
    """Tests for the _build_search_url helper."""

    def test_build_url_basic(self):
        from wallapop.tools import _build_search_url
        url = _build_search_url("test query")
        assert "test+query" in url or "test%20query" in url
        assert "wallapop.com/search" in url

    def test_build_url_with_location(self):
        from wallapop.tools import _build_search_url
        url = _build_search_url("test", location="Madrid")
        assert "location_name=Madrid" in url

    def test_build_url_with_coordinates(self):
        from wallapop.tools import _build_search_url
        url = _build_search_url("test", latitude=40.0, longitude=-3.0)
        assert "latitude=40.0" in url
        assert "longitude=-3.0" in url


class TestCoordinatesAndMapping:
    """Tests for coordinate resolution and normalization."""

    def test_direct_coords_precedence(self):
        from wallapop.location import resolve_location
        res = resolve_location(location="Madrid", latitude=41.5, longitude=2.0)
        assert res["latitude"] == 41.5
        assert res["longitude"] == 2.0
        assert res["source"] == "coordinates_override"

    @patch("wallapop.location.geocode_photon")
    def test_invalid_llm_coords_rejection(self, mock_photon):
        from wallapop.location import resolve_location
        mock_photon.return_value = {
            "latitude": 41.6488,
            "longitude": -0.8891,
            "city": "Zaragoza",
            "province": "Aragón",
            "community": "España",
            "postal_code": "50001",
            "label": "Zaragoza, Aragón, ESP",
            "source": "photon",
        }
        # 10.0, 50.0 is not in Spain; should reject and call geocoder
        res = resolve_location(location="Zaragoza", latitude=10.0, longitude=50.0)
        assert res["latitude"] == pytest.approx(41.6488, rel=1e-3)
        assert res["source"] == "photon"

    @patch("wallapop.location.geocode_photon")
    def test_dynamic_geocoding_resolution(self, mock_photon):
        from wallapop.location import resolve_location
        mock_photon.return_value = {
            "latitude": 40.3071,
            "longitude": -3.7332,
            "city": "Getafe",
            "province": "Comunidad de Madrid",
            "community": "España",
            "postal_code": "28901",
            "label": "Getafe, Comunidad de Madrid, ESP",
            "source": "photon",
        }
        res = resolve_location("Getafe")
        assert res["latitude"] == pytest.approx(40.3071, rel=1e-3)
        assert res["city"] == "Getafe"
        assert res["source"] == "photon"

    def test_empty_location_national_default(self):
        from wallapop.location import resolve_location
        res = resolve_location()
        assert res["city"] == "Madrid"
        assert res["source"] == "default_national"

    def test_condition_normalization(self):
        from wallapop.api_client import _normalize_condition
        assert _normalize_condition("nuevo") == "new"
        assert _normalize_condition(["como nuevo", "good"]) == "as_good_as_new,good"
        assert _normalize_condition("lo ha dado todo") == "has_given_it_all"


class TestLocateLocationTool:
    """Tests for the wallapop_locate tool."""

    def test_locate_requires_location(self):
        from wallapop.tools import locate_location
        data = json.loads(locate_location({}))
        assert "error" in data

    @patch("wallapop.location.geocode_photon")
    def test_locate_valid_place(self, mock_photon):
        from wallapop.tools import locate_location
        mock_photon.return_value = {
            "latitude": 40.3458,
            "longitude": -3.8249,
            "city": "Alcorcón",
            "province": "Madrid",
            "community": "España",
            "postal_code": "28921",
            "label": "Alcorcón, Madrid, ESP",
            "source": "photon",
        }
        data = json.loads(locate_location({"location": "Alcorcón"}))
        assert "latitude" in data
        assert "longitude" in data
        assert data["city"] == "Alcorcón"


class TestPluginRegistration:
    """Tests for plugin register(ctx) in Hermes Agent."""

    def test_register_wires_tools_and_skills(self):
        import wallapop
        mock_ctx = MagicMock()

        wallapop.register(mock_ctx)

        assert mock_ctx.register_tool.call_count == 3
        tool_names = [call.kwargs.get("name") for call in mock_ctx.register_tool.call_args_list]
        assert "wallapop_search" in tool_names
        assert "wallapop_get_item" in tool_names
        assert "wallapop_locate" in tool_names

        # Verify skill registration
        assert mock_ctx.register_skill.call_count >= 1
        skill_names = [call.args[0] for call in mock_ctx.register_skill.call_args_list]
        assert "wallapop" in skill_names


class TestPlaywrightPipeline:
    """Tests for the Playwright-only pipeline configuration."""

    def test_ensure_playwright_installed_when_present(self):
        from wallapop.api_client import ensure_playwright_installed
        # In current environment playwright is installed and works
        assert ensure_playwright_installed() is True

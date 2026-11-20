# Tests for the Wallapop plugin.
#
# Run after `pip install -e .` (the package is importable as `wallapop`):
#   pytest tests/

import pytest
import json
from unittest.mock import patch


class TestSearchWallapop:
    """Tests for the search_wallapop handler."""

    def test_search_requires_query(self):
        from wallapop.tools import search_wallapop
        data = json.loads(search_wallapop({}))
        assert "error" in data
        assert "Query parameter is required" in data["error"]

    @patch("wallapop.api_client.search_wallapop_api")
    def test_search_with_query(self, mock_api):
        from wallapop.tools import search_wallapop
        mock_api.return_value = {"items": [{"id": "123", "title": "Test Item"}], "total": 1}
        data = json.loads(search_wallapop({"query": "test"}))
        assert "items" in data
        assert len(data["items"]) == 1


class TestGetItemDetails:
    """Tests for the get_item_details handler."""

    def test_get_item_requires_id_or_url(self):
        from wallapop.tools import get_item_details
        data = json.loads(get_item_details({}))
        assert "error" in data


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

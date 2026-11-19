# Tests for Wallapop Plugin

import pytest
import json
from unittest.mock import patch, MagicMock


class TestSearchWallapop:
    """Tests for wallapop_search function."""
    
    def test_search_requires_query(self):
        """Test that search requires a query parameter."""
        from tools import search_wallapop
        result = search_wallapop({})
        data = json.loads(result)
        assert "error" in data
        assert "Query parameter is required" in data["error"]
    
    @patch('tools.search_wallapop_api')
    def test_search_with_query(self, mock_api):
        """Test basic search with query."""
        from tools import search_wallapop
        
        mock_api.return_value = {
            "items": [{"id": "123", "title": "Test Item"}],
            "total": 1
        }
        
        result = search_wallapop({"query": "test"})
        data = json.loads(result)
        
        assert "items" in data
        assert len(data["items"]) == 1


class TestGetItemDetails:
    """Tests for get_item_details function."""
    
    def test_get_item_requires_id_or_url(self):
        """Test that get_item requires item_id or url."""
        from tools import get_item_details
        result = get_item_details({})
        data = json.loads(result)
        assert "error" in data


class TestBuildSearchURL:
    """Tests for _build_search_url function."""
    
    def test_build_url_basic(self):
        """Test basic URL construction."""
        from tools import _build_search_url
        url = _build_search_url("test query")
        assert "test+query" in url or "test%20query" in url
        assert "wallapop.com/search" in url
    
    def test_build_url_with_location(self):
        """Test URL construction with location."""
        from tools import _build_search_url
        url = _build_search_url("test", location="Madrid")
        assert "location_name=Madrid" in url
    
    def test_build_url_with_coordinates(self):
        """Test URL construction with coordinates."""
        from tools import _build_search_url
        url = _build_search_url("test", latitude=40.0, longitude=-3.0)
        assert "latitude=40.0" in url
        assert "longitude=-3.0" in url
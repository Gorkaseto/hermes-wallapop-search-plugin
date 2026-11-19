"""Wallapop plugin for Hermes Agent."""

import json
import logging

from . import schemas, tools

logger = logging.getLogger(__name__)

# Plugin metadata
PLUGIN_ID = "wallapop"
PLUGIN_NAME = "Wallapop Search Plugin"
PLUGIN_VERSION = "1.0.0"


def register(ctx):
    """Register plugin tools with Hermes."""
    
    # Register tools
    ctx.register_tool(
        name="wallapop_search",
        toolset="wallapop",
        schema=schemas.SEARCH_SCHEMA,
        handler=tools.search_wallapop
    )
    
    ctx.register_tool(
        name="wallapop_get_item",
        toolset="wallapop",
        schema=schemas.ITEM_SCHEMA,
        handler=tools.get_item_details
    )
    
    logger.info(f"Registered {PLUGIN_NAME} v{PLUGIN_VERSION}")


# Optional: cleanup function if needed
def unregister(ctx):
    """Unregister plugin tools (optional)."""
    logger.info(f"Unregistered {PLUGIN_NAME}")
"""Wallapop plugin for Hermes Agent - registration (wiring schemas to handlers)."""

import logging
from pathlib import Path
import threading

from . import schemas, tools

logger = logging.getLogger(__name__)

# Plugin metadata
PLUGIN_ID = "wallapop"
PLUGIN_NAME = "Wallapop Search Plugin"
PLUGIN_VERSION = "1.0.0"


def _background_prepare_playwright():
    """Silently ensure Playwright browser binaries are ready in the background upon activation."""
    try:
        from .api_client import ensure_playwright_installed, is_chromium_installed
        if not is_chromium_installed():
            logger.info("Wallapop plugin: Chromium binary missing. Starting background download...")
            ensure_playwright_installed()
    except Exception as e:
        logger.debug(f"Background Playwright setup check: {e}")


def register(ctx):
    """Register plugin tools and bundled skills with Hermes."""

    ctx.register_tool(
        name="wallapop_search",
        toolset="wallapop",
        schema=schemas.SEARCH_SCHEMA,
        handler=tools.search_wallapop,
    )

    ctx.register_tool(
        name="wallapop_get_item",
        toolset="wallapop",
        schema=schemas.ITEM_SCHEMA,
        handler=tools.get_item_details,
    )

    ctx.register_tool(
        name="wallapop_locate",
        toolset="wallapop",
        schema=schemas.LOCATE_SCHEMA,
        handler=tools.locate_location,
    )

    # Bundle skills shipped in skills/<name>/SKILL.md
    skills_dir = Path(__file__).parent / "skills"
    if skills_dir.exists():
        for child in sorted(skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.exists():
                ctx.register_skill(child.name, skill_md)

    # Trigger background check/download of browser binaries so it's ready before first tool call
    threading.Thread(target=_background_prepare_playwright, daemon=True).start()

    logger.info(f"Registered {PLUGIN_NAME} v{PLUGIN_VERSION}")


def unregister(ctx):
    """Unregister plugin tools (optional)."""
    logger.info(f"Unregistered {PLUGIN_NAME}")

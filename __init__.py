"""Wallapop plugin for Hermes Agent - registration (wiring schemas to handlers)."""

import logging
from pathlib import Path

from . import schemas, tools

logger = logging.getLogger(__name__)

# Plugin metadata
PLUGIN_ID = "wallapop"
PLUGIN_NAME = "Wallapop Search Plugin"
PLUGIN_VERSION = "1.0.0"


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

    # Bundle skills shipped in skills/<name>/SKILL.md
    skills_dir = Path(__file__).parent / "skills"
    if skills_dir.exists():
        for child in sorted(skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.exists():
                ctx.register_skill(child.name, skill_md)

    logger.info(f"Registered {PLUGIN_NAME} v{PLUGIN_VERSION}")


def unregister(ctx):
    """Unregister plugin tools (optional)."""
    logger.info(f"Unregistered {PLUGIN_NAME}")

# Wallapop Hermes Plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)

A Python plugin for [Hermes Agent](https://hermes-agent.nousresearch.com/) that enables searching the Spanish second-hand marketplace [Wallapop](https://wallapop.com).

## Features

- Search Wallapop with various filters (location, price, condition, category, sorting)
- Get detailed information about specific items
- Coordinate-based location search
- Automatic dependency installation

## Installation

```bash
git clone https://github.com/hermes-agent/wallapop-plugin.git
cd wallapop-plugin
pip install -e .
```

## Usage

```python
# Basic search
wallapop_search({"query": "product name"})

# Search with coordinates
wallapop_search({"query": "item", "latitude": X.XXXX, "longitude": Y.YYYY, "radius_km": 10})

# Get item details
wallapop_get_item({"item_id": "12345"})
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License
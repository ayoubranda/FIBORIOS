"""
Compatibility shim — replaced by backend/services/data_service.py.

Import from backend.services.data_service going forward.
MetaTrader 5 is no longer a dependency.
"""
from backend.services.data_service import (  # noqa: F401
    MarketDataProvider,
    TradingViewProvider,
    get_provider,
    SUPPORTED_SYMBOLS,
)

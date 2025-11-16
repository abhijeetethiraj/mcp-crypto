"""
Test suite for the Cryptocurrency MCP Server.
Run with: pytest test_main.py -v
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import ccxt.async_support as ccxt
from main import CryptoMCPServer, price_cache


@pytest.fixture
def server():
    """Fixture to create a fresh server instance for each test."""
    return CryptoMCPServer()


@pytest.fixture
def mock_ticker():
    """Fixture for mock ticker data."""
    return {
        "symbol": "BTC/USDT",
        "last": 45000.00,
        "bid": 44999.50,
        "ask": 45000.50,
        "high": 46000.00,
        "low": 44000.00,
        "baseVolume": 1234.56,
        "change": 1000.00,
        "percentage": 2.27,
        "timestamp": 1704067200000,
        "datetime": "2024-01-01T00:00:00.000Z"
    }


@pytest.fixture
def mock_ohlcv():
    """Fixture for mock OHLCV data."""
    return [
        [1704067200000, 45000, 45500, 44500, 45200, 100.5],
        [1704070800000, 45200, 45800, 45000, 45600, 120.3],
        [1704074400000, 45600, 46000, 45400, 45800, 110.7]
    ]


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the cache before each test."""
    price_cache.clear()
    yield
    price_cache.clear()


class TestGetCurrentPrice:
    """Tests for the get_current_price tool."""
    
    @pytest.mark.asyncio
    async def test_valid_symbol(self, server, mock_ticker):
        """Test fetching current price with a valid symbol."""
        with patch.object(server.exchange, 'fetch_ticker', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_ticker
            
            result = await server.get_current_price("BTC/USDT")
            
            assert "BTC/USDT" in result
            assert "45000" in result
            assert "price" in result
            mock_fetch.assert_called_once_with("BTC/USDT")
    
    @pytest.mark.asyncio
    async def test_invalid_symbol(self, server):
        """Test fetching current price with an invalid symbol."""
        with patch.object(server.exchange, 'fetch_ticker', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ccxt.BadSymbol("Invalid symbol")
            
            result = await server.get_current_price("INVALID/SYMBOL")
            
            assert "Error" in result
            assert "Invalid symbol" in result
    
    @pytest.mark.asyncio
    async def test_missing_symbol(self, server):
        """Test fetching current price without a symbol."""
        result = await server.get_current_price(None)
        
        assert "Error" in result
        assert "required" in result.lower()
    
    @pytest.mark.asyncio
    async def test_caching(self, server, mock_ticker):
        """Test that prices are cached correctly."""
        with patch.object(server.exchange, 'fetch_ticker', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_ticker
            
            # First call - should hit the API
            result1 = await server.get_current_price("BTC/USDT")
            assert "45000" in result1
            assert mock_fetch.call_count == 1
            
            # Second call - should use cache
            result2 = await server.get_current_price("BTC/USDT")
            assert "45000" in result2
            assert mock_fetch.call_count == 1  # Still 1, no new API call
            
            # Results should be identical
            assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_cache_expiry(self, server, mock_ticker):
        """Test that cache expires after the configured duration."""
        with patch.object(server.exchange, 'fetch_ticker', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_ticker
            
            # First call
            result1 = await server.get_current_price("BTC/USDT")
            assert mock_fetch.call_count == 1
            
            # Manually expire the cache
            price_cache["BTC/USDT"]["timestamp"] = datetime.now() - timedelta(seconds=61)
            
            # Second call - should hit the API again
            result2 = await server.get_current_price("BTC/USDT")
            assert mock_fetch.call_count == 2
    
    @pytest.mark.asyncio
    async def test_symbol_normalization(self, server, mock_ticker):
        """Test that symbols are normalized to uppercase."""
        with patch.object(server.exchange, 'fetch_ticker', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_ticker
            
            result = await server.get_current_price("btc/usdt")
            
            # Should be normalized to uppercase
            mock_fetch.assert_called_once_with("BTC/USDT")
            assert "BTC/USDT" in result
    
    @pytest.mark.asyncio
    async def test_network_error(self, server):
        """Test handling of network errors."""
        with patch.object(server.exchange, 'fetch_ticker', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ccxt.NetworkError("Connection timeout")
            
            result = await server.get_current_price("BTC/USDT")
            
            assert "Network error" in result
            assert "timeout" in result.lower()


class TestGetHistoricalPrice:
    """Tests for the get_historical_price tool."""
    
    @pytest.mark.asyncio
    async def test_valid_request(self, server, mock_ohlcv):
        """Test fetching historical data with valid parameters."""
        with patch.object(server.exchange, 'fetch_ohlcv', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_ohlcv
            
            result = await server.get_historical_price("BTC/USDT", "1h", 3)
            
            assert "BTC/USDT" in result
            assert "1h" in result
            assert "candles" in result
            assert "45000" in result
            mock_fetch.assert_called_once_with(symbol="BTC/USDT", timeframe="1h", limit=3)
    
    @pytest.mark.asyncio
    async def test_default_parameters(self, server, mock_ohlcv):
        """Test that default parameters are applied correctly."""
        with patch.object(server.exchange, 'fetch_ohlcv', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_ohlcv
            
            result = await server.get_historical_price("ETH/USDT")
            
            mock_fetch.assert_called_once_with(symbol="ETH/USDT", timeframe="1h", limit=10)
    
    @pytest.mark.asyncio
    async def test_invalid_symbol(self, server):
        """Test fetching historical data with an invalid symbol."""
        with patch.object(server.exchange, 'fetch_ohlcv', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ccxt.BadSymbol("Invalid symbol")
            
            result = await server.get_historical_price("INVALID/PAIR")
            
            assert "Error" in result
            assert "Invalid symbol" in result
    
    @pytest.mark.asyncio
    async def test_missing_symbol(self, server):
        """Test fetching historical data without a symbol."""
        result = await server.get_historical_price(None)
        
        assert "Error" in result
        assert "required" in result.lower()
    
    @pytest.mark.asyncio
    async def test_limit_validation(self, server):
        """Test that limit parameter is validated."""
        # Test limit too low
        result1 = await server.get_historical_price("BTC/USDT", "1h", 0)
        assert "Error" in result1
        assert "between 1 and 500" in result1
        
        # Test limit too high
        result2 = await server.get_historical_price("BTC/USDT", "1h", 501)
        assert "Error" in result2
        assert "between 1 and 500" in result2
    
    @pytest.mark.asyncio
    async def test_ohlcv_data_structure(self, server, mock_ohlcv):
        """Test that OHLCV data is properly formatted."""
        with patch.object(server.exchange, 'fetch_ohlcv', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_ohlcv
            
            result = await server.get_historical_price("BTC/USDT", "1h", 3)
            
            # Check for required fields
            assert "open" in result
            assert "high" in result
            assert "low" in result
            assert "close" in result
            assert "volume" in result
            assert "datetime" in result
    
    @pytest.mark.asyncio
    async def test_network_error(self, server):
        """Test handling of network errors."""
        with patch.object(server.exchange, 'fetch_ohlcv', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ccxt.NetworkError("Connection failed")
            
            result = await server.get_historical_price("BTC/USDT")
            
            assert "Network error" in result
            assert "failed" in result.lower()


class TestCacheManagement:
    """Tests for cache management functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_isolation(self, server, mock_ticker):
        """Test that cache entries for different symbols are isolated."""
        with patch.object(server.exchange, 'fetch_ticker', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_ticker
            
            # Fetch BTC
            await server.get_current_price("BTC/USDT")
            
            # Fetch ETH - should make a new API call
            mock_fetch.return_value = {**mock_ticker, "symbol": "ETH/USDT", "last": 3000.00}
            await server.get_current_price("ETH/USDT")
            
            assert mock_fetch.call_count == 2
            assert "BTC/USDT" in price_cache
            assert "ETH/USDT" in price_cache


class TestServerCleanup:
    """Tests for server cleanup functionality."""
    
    @pytest.mark.asyncio
    async def test_cleanup(self, server):
        """Test that cleanup closes the exchange connection."""
        with patch.object(server.exchange, 'close', new_callable=AsyncMock) as mock_close:
            await server.cleanup()
            mock_close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
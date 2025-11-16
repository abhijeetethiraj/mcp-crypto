#!/usr/bin/env python3
"""
Cryptocurrency MCP Server
Provides tools to fetch real-time and historical cryptocurrency data using CCXT.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import ccxt.async_support as ccxt
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_DURATION_SECONDS = 60
price_cache: Dict[str, Dict[str, Any]] = {}


class CryptoMCPServer:
    """MCP Server for cryptocurrency data."""
    
    def __init__(self):
        self.server = Server("crypto-mcp-server")
        self.exchange = ccxt.binance()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up request handlers for the MCP server."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="get_current_price",
                    description="Get the current real-time price of a cryptocurrency pair. "
                                "Results are cached for 60 seconds. "
                                "Example symbols: BTC/USDT, ETH/USDT, SOL/USDT",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol (e.g., BTC/USDT, ETH/USDT)"
                            }
                        },
                        "required": ["symbol"]
                    }
                ),
                Tool(
                    name="get_historical_price",
                    description="Get historical OHLCV (Open, High, Low, Close, Volume) data "
                                "for a cryptocurrency pair. Returns the most recent candles. "
                                "Example symbols: BTC/USDT, ETH/USDT, SOL/USDT",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol (e.g., BTC/USDT, ETH/USDT)"
                            },
                            "timeframe": {
                                "type": "string",
                                "description": "Timeframe for candles (e.g., 1m, 5m, 1h, 1d)",
                                "default": "1h"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of candles to retrieve (max 500)",
                                "default": 10
                            }
                        },
                        "required": ["symbol"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Handle tool calls."""
            try:
                if name == "get_current_price":
                    result = await self.get_current_price(arguments.get("symbol"))
                    return [TextContent(type="text", text=result)]
                
                elif name == "get_historical_price":
                    result = await self.get_historical_price(
                        symbol=arguments.get("symbol"),
                        timeframe=arguments.get("timeframe", "1h"),
                        limit=arguments.get("limit", 10)
                    )
                    return [TextContent(type="text", text=result)]
                
                else:
                    raise ValueError(f"Unknown tool: {name}")
            
            except Exception as e:
                error_msg = f"Error executing {name}: {str(e)}"
                logger.error(error_msg)
                return [TextContent(type="text", text=error_msg)]
    
    async def get_current_price(self, symbol: Optional[str]) -> str:
        """
        Get current price for a cryptocurrency pair with caching.
        
        Args:
            symbol: Trading pair symbol (e.g., BTC/USDT)
        
        Returns:
            JSON string with price data or error message
        """
        if not symbol:
            return "Error: Symbol is required"
        
        # Normalize symbol
        symbol = symbol.upper().strip()
        
        # Check cache
        if symbol in price_cache:
            cached_data = price_cache[symbol]
            cache_time = cached_data["timestamp"]
            if datetime.now() - cache_time < timedelta(seconds=CACHE_DURATION_SECONDS):
                logger.info(f"Cache hit for {symbol}")
                return cached_data["data"]
        
        try:
            # Fetch ticker data
            ticker = await self.exchange.fetch_ticker(symbol)
            
            # Format response
            result = {
                "symbol": symbol,
                "price": ticker["last"],
                "bid": ticker["bid"],
                "ask": ticker["ask"],
                "high_24h": ticker["high"],
                "low_24h": ticker["low"],
                "volume_24h": ticker["baseVolume"],
                "change_24h": ticker["change"],
                "change_percent_24h": ticker["percentage"],
                "timestamp": ticker["timestamp"],
                "datetime": ticker["datetime"]
            }
            
            result_str = self._format_dict(result)
            
            # Update cache
            price_cache[symbol] = {
                "data": result_str,
                "timestamp": datetime.now()
            }
            
            logger.info(f"Fetched current price for {symbol}")
            return result_str
        
        except ccxt.BadSymbol:
            error_msg = f"Error: Invalid symbol '{symbol}'. Please use format like BTC/USDT, ETH/USDT"
            logger.warning(error_msg)
            return error_msg
        
        except ccxt.NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(error_msg)
            return error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error fetching price for {symbol}: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    async def get_historical_price(
        self, 
        symbol: Optional[str],
        timeframe: str = "1h",
        limit: int = 10
    ) -> str:
        """
        Get historical OHLCV data for a cryptocurrency pair.
        
        Args:
            symbol: Trading pair symbol (e.g., BTC/USDT)
            timeframe: Candle timeframe (e.g., 1m, 5m, 1h, 1d)
            limit: Number of candles to retrieve
        
        Returns:
            JSON string with historical data or error message
        """
        if not symbol:
            return "Error: Symbol is required"
        
        # Normalize symbol
        symbol = symbol.upper().strip()
        
        # Validate limit
        if limit < 1 or limit > 500:
            return "Error: Limit must be between 1 and 500"
        
        try:
            # Fetch OHLCV data
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit
            )
            
            # Format response
            candles = []
            for candle in ohlcv:
                candles.append({
                    "timestamp": candle[0],
                    "datetime": datetime.fromtimestamp(candle[0] / 1000).isoformat(),
                    "open": candle[1],
                    "high": candle[2],
                    "low": candle[3],
                    "close": candle[4],
                    "volume": candle[5]
                })
            
            result = {
                "symbol": symbol,
                "timeframe": timeframe,
                "count": len(candles),
                "candles": candles
            }
            
            logger.info(f"Fetched {len(candles)} candles for {symbol} ({timeframe})")
            return self._format_dict(result)
        
        except ccxt.BadSymbol:
            error_msg = f"Error: Invalid symbol '{symbol}'. Please use format like BTC/USDT, ETH/USDT"
            logger.warning(error_msg)
            return error_msg
        
        except ccxt.NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(error_msg)
            return error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error fetching historical data for {symbol}: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    @staticmethod
    def _format_dict(data: dict) -> str:
        """Format dictionary as a readable string."""
        import json
        return json.dumps(data, indent=2)
    
    async def cleanup(self):
        """Clean up resources."""
        await self.exchange.close()
        logger.info("Exchange connection closed")
    
    async def run(self):
        """Run the MCP server."""
        try:
            async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
                logger.info("Crypto MCP Server started")
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        finally:
            await self.cleanup()


async def main():
    """Entry point for the server."""
    server = CryptoMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
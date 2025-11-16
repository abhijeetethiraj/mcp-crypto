# Crypto Data MCP Server

This project is a submission for the HarshNidhi Ventures Full Stack Development internship assignment.

It is a Python-based MCP (Model Context Protocol) server designed to provide real-time and historical cryptocurrency data to a connected LLM. The server uses the `ccxt` library to fetch live data from the Binance exchange.

---

## 🚀 Core Features

- **MCP Server:** Built using the official `mcp-server-sdk` to act as a tool for an LLM.
- **Real-time Data Tool:** Includes a `get_current_price(symbol)` tool that fetches the latest price, bid/ask, and 24h stats for a trading pair.
- **Historical Data Tool:** Includes a `get_historical_price(symbol, timeframe, limit)` tool to fetch historical OHLCV (Open, High, Low, Close, Volume) data.
- **Smart Caching:** The `get_current_price` tool caches results for 60 seconds to improve performance and avoid API rate-limit issues.
- **Robust Error Handling:** Gracefully handles invalid symbols, network errors, and bad input parameters, returning user-friendly error messages.
- **High Test Coverage:** Includes a comprehensive test suite (`test_main.py`) with **16 passing tests** that mock all external API calls for safe and reliable testing.

---

## 🛠️ Technologies Used

- **Python 3.11+** (with `asyncio`)
- **mcp-server-sdk:** For the core MCP server functionality.
- **ccxt:** For connecting to and fetching data from the Binance exchange.
- **pytest** & **pytest-asyncio:** For asynchronous unit testing.
- **unittest.mock:** For mocking external API calls during tests.

---

## ⚙️ Setup and Installation

To run this project, you will need Python 3 installed.

**1. Clone the repository (or download the source):**

```bash
# This step is for the reviewer
git clone [Your-GitHub-Repo-Link-Here]
cd [your-project-folder-name]
```

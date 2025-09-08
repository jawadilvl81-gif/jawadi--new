# Crypto Signals Telegram Bot

A Telegram bot that provides crypto trading signals with entry, TP1-TP5, SL, and charts, based on TradingView analysis. It also posts daily crypto news and a daily trade to a specified Telegram channel.

## Features
- Generates trading signals for any crypto pair (e.g., /trade BTCUSDT).
- Provides Entry, TP1-TP5, SL, and small advice with each signal.
- Creates candlestick charts with entry, TP, and SL annotations.
- Posts daily crypto news scraped from Cointelegraph with sentiment analysis.
- Posts a daily trade for a random popular coin.
- Monitors open trades and notifies users when TP or SL is hit.
- Includes Binance referral link and channel link in responses.

## Setup Instructions
1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt

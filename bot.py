# Telegram Crypto Signals Bot
# This script creates a Telegram bot that provides crypto trading signals based on TradingView analysis.
# It uses tradingview_ta for signals, ccxt for price data, plotly for chart generation with annotations.
# Daily news scraping from Cointelegraph and posting to channel.
# Daily random trade post for a popular coin.
# Monitors open trades for TP/SL hits (simple polling in a thread).
# Futuristic features added:
#   - Sentiment analysis on news using NLTK to influence signal confidence.
#   - Basic price prediction using linear regression from scikit-learn.
#   - AI-like advice generation based on analysis.
# User needs to install dependencies: pip install telebot tradingview_ta ccxt pandas plotly requests beautifulsoup4 nltk scikit-learn schedule
# Also, download NLTK data: in code.
# Set BOT_TOKEN and CHANNEL_USERNAME (e.g., '@yourchannel' or chat_id as int).

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import tradingview_ta
from tradingview_ta import TA_Handler, Interval, Exchange
import ccxt
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
import requests
from bs4 import BeautifulSoup
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from sklearn.linear_model import LinearRegression
import numpy as np
import threading
import time
import schedule
import random
import os

# Download NLTK data if not present
nltk.download('vader_lexicon', quiet=True)

# Configuration - Replace with your values
BOT_TOKEN = os.getenv('BOT_TOKEN')  # Use environment variable
CHANNEL_LINK = 'https://t.me/+T2lFw-AjK21kYWM0'
BINANCE_LINK = 'https://www.binance.com/referral/earn-together/refer-in-hotsummer/claim?hl=en&ref=GRO_20338_LRBY5&utm_source=default'
CHANNEL_USERNAME = '@your_channel_username'  # Or chat_id as int, e.g., -1001234567890. Bot must be admin in channel.
POPULAR_COINS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT']  # List of coins for daily posts

bot = telebot.TeleBot(BOT_TOKEN)
exchange = ccxt.binance()
sia = SentimentIntensityAnalyzer()

# Store open trades for monitoring {user_id: [{'symbol': 'BTCUSDT', 'entry': 50000, 'tps': [51000,52000,...], 'hit_tps': [], 'sl': 49000, 'type': 'long'}]}
open_trades = {}

# Function to get current price
def get_current_price(symbol):
    ticker = exchange.fetch_ticker(symbol)
    return ticker['last']

# Function to perform analysis using TradingView TA
def get_ta_analysis(symbol):
    handler = TA_Handler(
        symbol=symbol.replace('USDT', '/USDT'),
        screener="crypto",
        exchange="BINANCE",
        interval=Interval.INTERVAL_1_HOUR
    )
    analysis = handler.get_analysis()
    return analysis

# Futuristic: Simple price prediction using linear regression on last 30 candles
def predict_price(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=30)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    X = np.array(range(len(df))).reshape(-1, 1)
    y = df['close'].values
    model = LinearRegression().fit(X, y)
    future = np.array([[len(df) + 1]])
    predicted = model.predict(future)[0]
    return predicted

# Generate signal based on TA
def generate_signal(symbol):
    analysis = get_ta_analysis(symbol)
    rec = analysis.summary['RECOMMENDATION']
    if rec in ['BUY', 'STRONG_BUY']:
        direction = 'Long'
    elif rec in ['SELL', 'STRONG_SELL']:
        direction = 'Short'
    else:
        return None  # Neutral, no signal

    current_price = get_current_price(symbol)
    predicted = predict_price(symbol)
    volatility = analysis.indicators.get('Volatility', 0.02)  # Approximate

    if direction == 'Long':
        entry = current_price
        sl = entry * (1 - volatility)
        tps = [entry * (1 + 0.01 * i) for i in range(1, 6)]
    else:
        entry = current_price
        sl = entry * (1 + volatility)
        tps = [entry * (1 - 0.01 * i) for i in range(1, 6)]

    advice = f"Based on AI analysis, predicted price: {predicted:.2f}. Sentiment score: {analysis.indicators.get('RSI', 50)}. Trade with caution, manage risk."

    return {
        'direction': direction,
        'entry': entry,
        'tps': tps,
        'sl': sl,
        'advice': advice
    }

# Generate chart image with annotations, optional hit_tps for highlighting
def generate_chart_image(symbol, entry, tps, sl, direction, hit_tps=None):
    if hit_tps is None:
        hit_tps = []
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=50)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    fig = go.Figure(data=[go.Candlestick(x=df['timestamp'],
                                        open=df['open'],
                                        high=df['high'],
                                        low=df['low'],
                                        close=df['close'])])

    # Add entry line
    fig.add_hline(y=entry, line_dash="dash", line_color="blue", annotation_text="Entry")

    # Add SL red box (rectangle from last candle to SL)
    last_time = df['timestamp'].iloc[-1]
    fig.add_shape(type="rect",
                  x0=last_time, y0=min(entry, sl), x1=last_time + pd.Timedelta(hours=24), y1=max(entry, sl),
                  fillcolor="red", opacity=0.3, line_color="red")

    # Add green boxes for remaining TPs
    for tp in tps:
        fig.add_shape(type="rect",
                      x0=last_time, y0=tp - 0.001*tp, x1=last_time + pd.Timedelta(hours=24), y1=tp + 0.001*tp,
                      fillcolor="green", opacity=0.3, line_color="green")
        fig.add_hline(y=tp, line_dash="dot", line_color="green")

    # Add yellow lines for hit TPs
    for hit_tp in hit_tps:
        fig.add_hline(y=hit_tp, line_dash="solid", line_color="yellow", annotation_text="Hit TP")

    fig.update_layout(title=f"{symbol} Chart", xaxis_title="Time", yaxis_title="Price", showlegend=False)

    img_bytes = fig.to_image(format="png")
    return BytesIO(img_bytes)

# Scrape crypto news
def scrape_news():
    url = 'https://cointelegraph.com/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.find_all('a', class_='post-card__title-link', limit=5)
    news = []
    for article in articles:
        title = article.text.strip()
        link = 'https://cointelegraph.com' + article['href']
        # Get image if available
        img_tag = article.find_parent().find('img')
        img_url = img_tag['src'] if img_tag else None
        news.append({'title': title, 'link': link, 'img_url': img_url})
    return news

# Futuristic: Analyze news sentiment
def analyze_news_sentiment(news):
    sentiments = [sia.polarity_scores(item['title'])['compound'] for item in news]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
    return avg_sentiment

# Daily news post
def post_daily_news():
    news = scrape_news()
    sentiment = analyze_news_sentiment(news)
    message = f"Daily Crypto News (AI Sentiment: {sentiment:.2f}):\n"
    for item in news:
        message += f"- {item['title']} {item['link']}\n"
    
    bot.send_message(CHANNEL_USERNAME, message)
    # Send images if available
    for item in news:
        if item['img_url']:
            bot.send_photo(CHANNEL_USERNAME, item['img_url'], caption=item['title'])

# Daily trade post
def post_daily_trade():
    symbol = random.choice(POPULAR_COINS)
    signal = generate_signal(symbol)
    if not signal:
        return  # No signal

    message = f"Daily Confirmed Trade: {symbol} - {signal['direction']}\n"
    message += f"Entry: {signal['entry']:.2f}\n"
    for i, tp in enumerate(signal['tps'], 1):
        message += f"TP{i}: {tp:.2f}\n"
    message += f"SL: {signal['sl']:.2f}\n"
    message += f"Small Advice: {signal['advice']}\n"

    img = generate_chart_image(symbol, signal['entry'], signal['tps'], signal['sl'], signal['direction'])
    bot.send_photo(CHANNEL_USERNAME, img, caption=message)

# Monitor trades for TP/SL hits
def monitor_trades():
    while True:
        for user_id, trades in list(open_trades.items()):
            for trade in trades[:]:  # Copy to avoid modification during iteration
                current = get_current_price(trade['symbol'])
                if trade['type'] == 'long':
                    if current <= trade['sl']:
                        message = f"SL hit for {trade['symbol']}! Loss. Advice: Review strategy."
                        bot.send_message(user_id, message)
                        trades.remove(trade)
                    else:
                        for tp in trade['tps'][:]:
                            if current >= tp:
                                congrats_message = f"TP hit for {trade['symbol']} at {tp}! Congratulations! 🎉 Small Advice: Book profits and consider trailing the remaining stops."
                                bot.send_message(user_id, congrats_message)
                                bot.send_message(CHANNEL_USERNAME, congrats_message)
                                trade['hit_tps'].append(tp)
                                trade['tps'].remove(tp)
                                # Generate updated chart with hit TPs highlighted
                                img = generate_chart_image(trade['symbol'], trade['entry'], trade['tps'], trade['sl'], trade['type'].capitalize(), trade['hit_tps'])
                                bot.send_photo(user_id, img, caption="Updated Chart after TP hit")
                                bot.send_photo(CHANNEL_USERNAME, img, caption="Updated Chart after TP hit")
                else:  # Short
                    if current >= trade['sl']:
                        message = f"SL hit for {trade['symbol']}! Loss. Advice: Review strategy."
                        bot.send_message(user_id, message)
                        trades.remove(trade)
                    else:
                        for tp in trade['tps'][:]:
                            if current <= tp:
                                congrats_message = f"TP hit for {trade['symbol']} at {tp}! Congratulations! 🎉 Small Advice: Book profits and consider trailing the remaining stops."
                                bot.send_message(user_id, congrats_message)
                                bot.send_message(CHANNEL_USERNAME, congrats_message)
                                trade['hit_tps'].append(tp)
                                trade['tps'].remove(tp)
                                # Generate updated chart with hit TPs highlighted
                                img = generate_chart_image(trade['symbol'], trade['entry'], trade['tps'], trade['sl'], trade['type'].capitalize(), trade['hit_tps'])
                                bot.send_photo(user_id, img, caption="Updated Chart after TP hit")
                                bot.send_photo(CHANNEL_USERNAME, img, caption="Updated Chart after TP hit")
        time.sleep(60)  # Check every minute

# Schedule daily tasks
def run_scheduler():
    schedule.every().day.at("09:00").do(post_daily_news)
    schedule.every().day.at("10:00").do(post_daily_trade)
    while True:
        schedule.run_pending()
        time.sleep(1)

# Bot handlers
@bot.message_handler(commands=['start'])
def handle_start(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Join Channel", url=CHANNEL_LINK))
    bot.send_message(message.chat.id, "Please join my channel first to get signals:", reply_markup=markup)
    bot.send_message(message.chat.id, f"Binance Joining Link: {BINANCE_LINK}")
    bot.send_message(message.chat.id, "Now you can use /trade <symbol> e.g., /trade BTCUSDT")

@bot.message_handler(commands=['trade'])
def handle_trade(message):
    try:
        symbol = message.text.split()[1].upper() + 'USDT' if not message.text.split()[1].endswith('USDT') else message.text.split()[1].upper()
    except IndexError:
        bot.reply_to(message, "Usage: /trade <symbol> e.g., /trade BTC")
        return

    signal = generate_signal(symbol)
    if not signal:https://github.com/jawadilvl81-gif/jawadi--new/tree/main
        bot.reply_to(message, "No clear signal right now. Try later.")
        return

    message_text = f"Confirmed Trade: {symbol} - {signal['direction']}\n"
    message_text += f"Entry: {signal['entry']:.2f}\n"
    for i, tp in enumerate(signal['tps'], 1):
        message_text += f"TP{i}: {tp:.2f}\n"
    message_text += f"SL: {signal['sl']:.2f}\n"
    message_text += f"Small Advice: {signal['advice']}\n"

    img = generate_chart_image(symbol, signal['entry'], signal['tps'], signal['sl'], signal['direction'])

    bot.send_photo(message.chat.id, img, caption=message_text)

    # Add to open trades for monitoring
    if message.chat.id not in open_trades:
        open_trades[message.chat.id] = []
    open_trades[message.chat.id].append({
        'symbol': symbol,
        'entry': signal['entry'],
        'tps': signal['tps'][:],  # Copy list
        'hit_tps': [],  # List for hit TPs
        'sl': signal['sl'],
        'type': signal['direction'].lower()
    })

# Start monitoring and scheduler in threads
threading.Thread(target=monitor_trades, daemon=True).start()
threading.Thread(target=run_scheduler, daemon=True).start()

# Start bot
bot.infinity_polling()

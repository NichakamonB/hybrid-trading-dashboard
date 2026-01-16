import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from lightweight_charts.widgets import StreamlitChart

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Professional Trading Suite")

# --- DATA ENGINE (ใช้ร่วมกันทุกหน้า) ---
@st.cache_data(ttl=300)
def get_processed_data(symbol, timeframe):
    tf_map = {'1min': '1m', '5min': '5m', '15min': '15m', '30min': '30m', '1hour': '1h', '1day': '1d'}
    interval = tf_map.get(timeframe, '1d')
    period = '1mo' if timeframe in ['1hour', '1day'] else '5d'
    
    try:
        df = yf.download(symbol, interval=interval, period=period, progress=False)
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df = df.reset_index()
        df.columns = df.columns.str.lower()
        df = df.rename(columns={'datetime': 'time', 'date': 'time'})
        
        # คำนวณพื้นฐาน
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['resistance'] = df['high'].rolling(window=20).max()
        df['support'] = df['low'].rolling(window=20).min()
        
        # Backtest Logic
        df['signal'] = 0
        df.loc[df['close'] > df['resistance'].shift(1), 'signal'] = 1
        df.loc[df['close'] < df['support'].shift(1), 'signal'] = -1
        df['strategy_return'] = df['signal'].shift(1) * df['close'].pct_change()
        df['cum_return'] = (1 + df['strategy_return'].fillna(0)).cumprod()
        
        return df.dropna()
    except:
        return pd.DataFrame()

# --- ฟังก์ชันวาดกราฟ ---
def render_chart_panel(key_index, default_symbol, timeframe, stock_list):
    symbol = st.selectbox(f"Select Symbol {key_index}", stock_list, index=stock_list.index(default_symbol), key=f"sel_{key_index}")
    df = get_processed_data(symbol, timeframe)
    if not df.empty:
        chart = StreamlitChart(height=300)
        chart.set(df)
        chart.load()
    else:
        st.warning(f"No data for {symbol}")

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("RT Trading Tool")
    # ตัวเลือกหน้าหลัก (เหมือนกดลิงก์)
    page = st.radio("Go to Page:", ["📊 Market Grid (4 Screens)", "📈 Deep Backtest & S/R", "🔥 Market Heatmap"])
    st.divider()
    timeframe = st.selectbox("Global Timeframe", ('5min', '15min', '1hour', '1day'), index=3)
    stock_options = ('TSLA', 'AAPL', 'NVDA', 'BTC-USD', 'ETH-USD', 'CPALL.BK', 'PTT.BK')

# --- PAGE 1: MARKET GRID ---
if page == "📊 Market Grid (4 Screens)":
    st.subheader("Multi-Chart Monitoring")
    col1, col2 = st.columns(2)
    with col1: render_chart_panel(1, 'TSLA', timeframe, stock_options)
    with col2: render_chart_panel(2, 'NVDA', timeframe, stock_options)
    
    col3, col4 = st.columns(2)
    with col3: render_chart_panel(3, 'BTC-USD', timeframe, stock_options)
    with col4: render_chart_panel(4, 'AAPL', timeframe, stock_options)

# --- PAGE 2: BACKTEST & S/R ---
elif page == "📈 Deep Backtest & S/R":
    st.subheader("Data-Driven Analysis")
    target_sym = st.selectbox("Select Asset to Analyze", stock_options)
    df = get_processed_data(target_sym, timeframe)
    
    if not df.empty:
        # Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Support", f"{df['support'].iloc[-1]:,.2f}")
        m2.metric("Resistance", f"{df['resistance'].iloc[-1]:,.2f}")
        m3.metric("Total Return", f"{(df['cum_return'].iloc[-1]-1)*100:.2f}%")
        
        # Chart
        fig = px.line(df, x='time', y='cum_return', title=f"Equity Curve: {target_sym}")
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("### Recent Signals")
        st.dataframe(df[df['signal'] != 0].tail(10), use_container_width=True)

# --- PAGE 3: HEATMAP ---
elif page == "🔥 Market Heatmap":
    st.subheader("Cross-Asset Comparison")
    results = []
    for s in stock_options:
        d = get_processed_data(s, timeframe)
        if not d.empty:
            change = ((d['close'].iloc[-1] - d['open'].iloc[0]) / d['open'].iloc[0]) * 100
            results.append({'Symbol': s, 'Change %': change, 'Last Price $ ': d['close'].iloc[-1]})
    
    df_res = pd.DataFrame(results)
    fig_heat = px.bar(df_res, x='Symbol', y='Change %', color='Change %', color_continuous_scale='RdYlGn')
    st.plotly_chart(fig_heat, use_container_width=True)
    st.table(df_res)


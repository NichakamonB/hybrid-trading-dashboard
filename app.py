import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from lightweight_charts.widgets import StreamlitChart
from streamlit_autorefresh import st_autorefresh

#  CONFIGURATION 
st.set_page_config(layout="wide", page_title="kwan test", page_icon="📈")

st.markdown("""
    <style>

        .block-container { padding: 1rem 3rem 1rem 3rem !important; max-width: 100% !important; }
        iframe { width: 100% !important; border-radius: 8px !important; }
        [data-testid="stSidebar"] { width: 280px !important; }
        div[data-testid="stMetric"] { background-color: rgba(255,255,255,0.05); padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)


st_autorefresh(interval=120000, key="kwan test")

# SYSTEM STATE
if 'lang' not in st.session_state: st.session_state.lang = 'TH'
if 'selected_stock' not in st.session_state: st.session_state.selected_stock = "AAPL"

def t(th, en): return th if st.session_state.lang == 'TH' else en

ASSET_GROUPS = {
    "🇺🇸 US MARKET": {"AAPL": "🍎 APPLE", "TSLA": "🚗 TESLA", "NVDA": "🎮 NVIDIA", "MSFT": "💻 MICROSOFT", "GOOGL": "🔍 GOOGLE"},
    "🇹🇭 THAI MARKET": {"CPALL.BK": "🛒 CPALL", "PTT.BK": "⛽ PTT", "AOT.BK": "✈️ AOT","KBANK.BK": "🏦 KBANK", "DELTA.BK": "🔌 DELTA"},
    "🪙 CRYPTO": {"BTC-USD": "₿ BITCOIN", "ETH-USD": "💎 ETHEREUM", "BNB-USD": "🔶 BINANCE"},
    "📈 Indices": {"^SET.BK": "🇹🇭 SET Index", "^GSPC": "🇺🇸 S&P 500", "^IXIC": "🇺🇸 Nasdaq"}
}
ALL_SYMBOLS = [s for sub in ASSET_GROUPS.values() for s in sub]

#  DATA ENGINE 
@st.cache_data(ttl=110)
def get_pro_data(symbol, timeframe):
    tf_map = {'5min': '5m', '15min': '15m', '1hour': '1h', '1day': '1d'}
    interval = tf_map.get(timeframe, '1d')
    
   if timeframe == '5min' or timeframe == '15min':
        period = '5d'
    elif timeframe == '1hour':
        period = '1mo'
    else:
        period = '6mo'   
    
    try:
        df = yf.download(symbol, interval=interval, period=period, progress=False, auto_adjust=False)
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = df.columns.str.lower()
        
        if isinstance(df.index, pd.DatetimeIndex):
            if df.index.tz is None: df.index = df.index.tz_localize('UTC')
            df.index = df.index.tz_convert('Asia/Bangkok')
            
        df = df.reset_index().rename(columns={'Datetime': 'time', 'Date': 'time'})
        df['time'] = df['time'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S')) 
        
        # Indicators
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        df['sma20'] = df['close'].rolling(window=20).mean()
        df['std20'] = df['close'].rolling(window=20).std()
        df['bb_up'] = df['sma20'] + (df['std20'] * 2)
        df['bb_low'] = df['sma20'] - (df['std20'] * 2)
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        df['macd_line'] = df['close'].ewm(span=12, adjust=False).mean() - df['close'].ewm(span=26, adjust=False).mean()
        df['res'] = df['high'].rolling(window=20).max()
        df['sup'] = df['low'].rolling(window=20).min()
        df['signal'] = 0
        df.loc[df['close'] > df['res'].shift(1), 'signal'] = 1
        df.loc[df['close'] < df['sup'].shift(1), 'signal'] = -1
        df['cum_ret'] = (1 + (df['signal'].shift(1) * df['close'].pct_change()).fillna(0)).cumprod() - 1
        
        return df.dropna().tail(250) 
    except: return pd.DataFrame()

#  SIDEBAR 
with st.sidebar:
    st.markdown(f"### ⚡ **kwan test**")
    c1, c2 = st.columns(2)
    if c1.button("🇹🇭 TH", use_container_width=True): st.session_state.lang = 'TH'; st.rerun()
    if c2.button("🇺🇸 EN", use_container_width=True): st.session_state.lang = 'EN'; st.rerun()
    
    st.divider()
    page = st.radio(t("โหมดการทำงาน", "Mode"), [t("🔍 วิเคราะห์รายตัว", "Single View"), t("📊 กระดาน 4 จอ", "4-Screen Grid")])
    timeframe = st.selectbox(t("ช่วงเวลา", "Timeframe"), ('5min', '15min', '1hour', '1day'), index=3)
    
    st.divider()
    st.markdown(f"**⚙️ {t('ตั้งค่ากราฟ', 'Indicators')}**")
    show_vol = st.checkbox(t("Volume", "Volume"), value=True)
    show_ema50 = st.checkbox("EMA 50", value=True)
    show_ema200 = st.checkbox("EMA 200", value=True)
    show_bb = st.checkbox("Bollinger Bands", value=False)
    show_rsi = st.checkbox("RSI (Separate)", value=False)
    show_macd = st.checkbox("MACD (Separate)", value=False)
    
    st.divider()
    for cat, items in ASSET_GROUPS.items():
        with st.expander(cat):
            for sym, name in items.items():
                if st.button(name, key=f"s_{sym}", use_container_width=True):
                    st.session_state.selected_stock = sym; st.rerun()

# CHART HELPER
def render_full_chart(chart_obj, data):
    chart_obj.legend(visible=True, font_size=12, font_family='Trebuchet MS')
    chart_obj.set(data)
    
    if show_vol:
        v = chart_obj.create_histogram(name='Volume', color='rgba(0, 150, 136, 0.4)')
        v.set(data[['time', 'volume']].rename(columns={'volume': 'Volume'}))
    if show_bb:
        chart_obj.create_line(name='BB Up', color='rgba(173, 216, 230, 0.4)').set(data[['time', 'bb_up']].rename(columns={'bb_up': 'BB Up'}))
        chart_obj.create_line(name='BB Low', color='rgba(173, 216, 230, 0.4)').set(data[['time', 'bb_low']].rename(columns={'bb_low': 'BB Low'}))
    if show_ema50:
        chart_obj.create_line(name='EMA 50', color='#FFEB3B').set(data[['time', 'ema50']].rename(columns={'ema50': 'EMA 50'}))
    if show_ema200:
        chart_obj.create_line(name='EMA 200', color='#E040FB').set(data[['time', 'ema200']].rename(columns={'ema200': 'EMA 200'}))
    if show_rsi:
        rsi_l = chart_obj.create_line(name='RSI', color='#2962FF')
        rsi_l.set(data[['time', 'rsi']].rename(columns={'rsi': 'RSI'}))
    if show_macd:
        macd_l = chart_obj.create_line(name='MACD', color='#FF5252')
        macd_l.set(data[['time', 'macd_line']].rename(columns={'macd_line': 'MACD'}))

# MAIN CONTENT
if page == t("🔍 วิเคราะห์รายตัว", "Single View"):
    symbol = st.session_state.selected_stock
    df = get_pro_data(symbol, timeframe)
    if not df.empty:
        st.subheader(f"📊 {symbol} ({timeframe})")
        curr = df['close'].iloc[-1]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(t("ราคาล่าสุด", "Price"), f"{curr:,.2f}", f"{curr - df['close'].iloc[-2]:,.2f}")
        m2.metric(t("แนวต้าน", "Resistance"), f"{df['res'].iloc[-1]:,.2f}")
        m3.metric(t("แนวรับ", "Support"), f"{df['sup'].iloc[-1]:,.2f}")
        m4.metric(t("กำไรระบบ", "Strategy Profit"), f"{df['cum_ret'].iloc[-1]*100:.2f}%")

        chart = StreamlitChart(height=550)
        render_full_chart(chart, df)
        chart.load()

        with st.expander(t("🔍 วิเคราะห์จุดเข้า-ออก", "Signal Insight"), expanded=True):
            s_col1, s_col2 = st.columns([1, 2])
            with s_col1:
                last_sig = df['signal'].iloc[-1]
                trend = "BULL" if curr > df['ema200'].iloc[-1] else "BEAR"
                st.markdown(f"**Trend:** {'🟢' if trend=='BULL' else '🔴'} {trend}")
                if last_sig == 1: st.success(t("✅ ซื้อ (Breakout)", "✅ BUY"))
                elif last_sig == -1: st.error(t("❌ ขาย (Breakdown)", "❌ SELL"))
                else: st.info(t("⌛ ถือ/รอ (Sideway)", "⌛ HOLD/WAIT"))
            with s_col2:
                st.table(df[df['signal'] != 0][['time', 'close', 'signal']].tail(3))
    with cf2:
    st.markdown(f"""
        <div style="text-align: center; color: gray; font-size: 14px;">
            <p>© 2026 <b>KWAN TEST</b> | Intelligent Trading Analysis System</p>
            <p>📊 Data Source: <a href="https://finance.yahoo.com/quote/{st.session_state.selected_stock}" target="_blank" style="color: #ff4b4b; text-decoration: none;">Verify on Yahoo Finance (Official)</a></p>
            <p style="font-size: 12px; opacity: 0.6;">Disclaimer: ข้อมูลนี้ใช้เพื่อการทดสอบและวิเคราะห์เชิงเทคนิคเท่านั้น ไม่ใช่คำแนะนำในการลงทุน</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
else:
    st.subheader(t("📊 กระดาน 4 จอ", "4-Screen Grid"))
    grid_cols = st.columns(2)
    for i in range(4):
        with grid_cols[i % 2]:
            sel = st.selectbox(f"จอ {i+1}", ALL_SYMBOLS, index=i, key=f"grid_sel_{i}")
            d = get_pro_data(sel, timeframe)
            if not d.empty:
                st.markdown(f"**{sel}** | {d['close'].iloc[-1]:,.2f}")
                c = StreamlitChart(height=450) 
                render_full_chart(c, d)
                c.load()




import streamlit as st
import yfinance as yf
import pandas as pd
from lightweight_charts.widgets import StreamlitChart
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Kwan test", page_icon="📈")

# ✅ 2. SET REAL-TIME REFRESH (ทุกๆ 30 วินาที)
st_autorefresh(interval=30000, key="fivedatarefresh")

# --- 3. MULTI-LANGUAGE SYSTEM ---
if 'lang' not in st.session_state:
    st.session_state.lang = 'TH'

def t(th, en):
    return th if st.session_state.lang == 'TH' else en

# --- 4. ASSET MAPPING ---
ASSET_GROUPS = {
    "🇺🇸 หุ้นสหรัฐฯ (US)": {
        "AAPL": "🍎 APPLE", "TSLA": "🚗 TESLA", "NVDA": "🎮 NVIDIA",
        "MSFT": "💻 MICROSOFT", "GOOGL": "🔍 GOOGLE"
    },
    "🇹🇭 หุ้นไทย (SET)": {
        "CPALL.BK": "🛒 CPALL", "PTT.BK": "⛽ PTT", "AOT.BK": "✈️ AOT",
        "KBANK.BK": "🏦 KBANK", "DELTA.BK": "🔌 DELTA"
    },
    "🪙 คริปโต (Crypto)": {
        "BTC-USD": "₿ BITCOIN", "ETH-USD": "💎 ETHEREUM", "BNB-USD": "🔶 BINANCE"
    },
    "📈 ดัชนี (Indices)": {
        "^SET.BK": "🇹🇭 SET Index", "^GSPC": "🇺🇸 S&P 500", "^IXIC": "🇺🇸 Nasdaq"
    }
}

ALL_SYMBOLS = [s for sub in ASSET_GROUPS.values() for s in sub]

# --- 5. INITIAL SETTINGS ---
if 'selected_stock' not in st.session_state:
    st.session_state.selected_stock = "AAPL" 

# --- 6. DATA ENGINE ---
@st.cache_data(ttl=10) 
def get_processed_data(symbol, timeframe):
    tf_map = {'5min': '5m', '15min': '15m', '1hour': '1h', '1day': '1d'}
    interval = tf_map.get(timeframe, '1d')
    
    if timeframe == '1day':
        period = '2y'
    elif timeframe == '1hour':
        period = '730d'
    else:
        period = '60d'
    
    try:
        df = yf.download(symbol, interval=interval, period=period, progress=False)
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df = df.reset_index()
        df.columns = df.columns.str.lower()
        df = df.rename(columns={'datetime': 'time', 'date': 'time'})
        
        if timeframe == '1day':
            df['time'] = pd.to_datetime(df['time']).dt.date
        else:
            df['time'] = pd.to_datetime(df['time']).dt.strftime('%Y-%m-%d %H:%M:%S')

        df['resistance'] = df['high'].rolling(window=20).max()
        df['support'] = df['low'].rolling(window=20).min()
        
        return df.dropna()
    except:
        return pd.DataFrame()

# --- 7. SIDEBAR ---
with st.sidebar:
    st.title("🚀 RT Trading Tool")
    st.caption(f"Last Update: {pd.Timestamp.now().strftime('%H:%M:%S')}")
    
    l1, l2 = st.columns(2)
    if l1.button("🇹🇭 ไทย", use_container_width=True): 
        st.session_state.lang = 'TH'; st.rerun()
    if l2.button("🇺🇸 EN", use_container_width=True): 
        st.session_state.lang = 'EN'; st.rerun()
    
    st.divider()
    page = st.radio(t("🏠 เลือกโหมด:", "🏠 Mode:"), [t("🔍 วิเคราะห์รายตัว", "🔍 Single View"), t("📊 กระดาน 4 จอ", "📊 4-Screen Grid")])
    st.divider()
    timeframe = st.selectbox(t("ช่วงเวลา", "Timeframe"), ('5min', '15min', '1hour', '1day'), index=0)
    
    st.divider()
    for category, items in ASSET_GROUPS.items():
        with st.expander(category, expanded=(category == "🇺🇸 หุ้นสหรัฐฯ (US)")):
            for sym, name in items.items():
                if st.button(name, key=f"nav_{sym}", use_container_width=True):
                    st.session_state.selected_stock = sym

# --- 8. MAIN PAGE ---
if page in [t("🔍 วิเคราะห์รายตัว", "🔍 Single View")]:
    symbol = st.session_state.selected_stock
    display_name = next((name for group in ASSET_GROUPS.values() for s, name in group.items() if s == symbol), symbol)
    st.header(f"📈 {display_name} ({symbol})")
    
    df = get_processed_data(symbol, timeframe)
    
    if not df.empty:
        col1, col2 = st.columns(2)
        price_change = df['close'].iloc[-1] - df['close'].iloc[-2]
        col1.metric(t("ราคาล่าสุด", "Last Price"), f"{df['close'].iloc[-1]:,.2f}", f"{price_change:,.2f}")
        col2.metric(t("แนวต้าน (R)", "Resistance"), f"{df['resistance'].iloc[-1]:,.2f}")
        
        # ปุ่ม Reset
        if st.button(t("🎯 กลับไปที่ล่าสุด (Reset View)", "🎯 Back to Latest"), use_container_width=True):
            st.rerun()

        # วาดกราฟ (ย้ายออกมาข้างนอกเพื่อให้แสดงผลตลอดเวลา)
        chart = StreamlitChart(height=600)
        chart.set(df)
        chart.load()

else:
    st.header(t("📊 กระดาน 4 จอ", "📊 4-Screen Grid"))
    
    if st.button(t("🎯 รีเซ็ตทั้ง 4 จอเป็นราคาล่าสุด", "🎯 Reset All 4 Charts"), use_container_width=True):
        st.rerun()

    def render_grid_chart(key, default_sym):
        s = st.selectbox(f"{t('จอที่', 'Screen')} {key}", ALL_SYMBOLS, index=ALL_SYMBOLS.index(default_sym), key=f"grid_sel_{key}")
        d = get_processed_data(s, timeframe)
        if not d.empty:
            c = StreamlitChart(height=350)
            c.set(d)
            c.load()

    c1, c2 = st.columns(2)
    with c1: render_grid_chart(1, "AAPL")
    with c2: render_grid_chart(2, "TSLA")
    
    c3, c4 = st.columns(2)
    with c3: render_grid_chart(3, "BTC-USD")
    with c4: render_grid_chart(4, "^SET.BK")

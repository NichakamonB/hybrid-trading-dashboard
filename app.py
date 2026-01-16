
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from lightweight_charts.widgets import StreamlitChart
from streamlit_autorefresh import st_autorefresh
import pytz 

st.set_page_config(layout="wide", page_title="Kwan test", page_icon="📈")

st.markdown("""
    <style>
        .block-container { padding-top: 0.5rem; padding-bottom: 0rem; }
        [data-testid="stSidebarNav"] { padding-top: 0rem; }
        [data-testid="stSidebar"] .stButton > button {
            height: 2.0rem; font-size: 14px; margin-bottom: 1px !important;
            border-radius: 4px; text-align: left; padding-left: 10px;
        }
        [data-testid="stSidebar"] .stButton > button:hover { background-color: #ff4b4b; color: white; }
        .stExpander { border: 1px solid rgba(255,255,255,0.1); margin-bottom: 1px !important; }
        div[data-testid="stMetric"] { background-color: rgba(255,255,255,0.05); padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

st_autorefresh(interval=30000, key="kwan test")

# --- 2. SYSTEM STATE & ASSETS ---
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

@st.cache_data(ttl=15)
def get_pro_data(symbol, timeframe):
    tf_map = {'5min': '5m', '15min': '15m', '1hour': '1h', '1day': '1d'}
    interval = tf_map.get(timeframe, '1d')
    period = '2y' if timeframe == '1day' else '60d'
    
    try:
        df = yf.download(symbol, interval=interval, period=period, progress=False, auto_adjust=False, multi_level_index=False)
        
        if df.empty: return pd.DataFrame()
        
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = df.columns.str.lower()
        
        if isinstance(df.index, pd.DatetimeIndex):
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            df.index = df.index.tz_convert('Asia/Bangkok')
            
        df = df.reset_index().rename(columns={'Datetime': 'time', 'Date': 'time'})
        df['time'] = df['time'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S')) 
        
        # Trend Indicators (EMA)
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # Donchian Channels (S/R)
        df['res'] = df['high'].rolling(window=20).max()
        df['sup'] = df['low'].rolling(window=20).min()
        
        # Signals
        df['signal'] = 0
        df.loc[df['close'] > df['res'].shift(1), 'signal'] = 1
        df.loc[df['close'] < df['sup'].shift(1), 'signal'] = -1
        
        df['strat_ret'] = df['signal'].shift(1) * df['close'].pct_change()
        df['cum_ret'] = (1 + df['strat_ret'].fillna(0)).cumprod() - 1
        
        return df.dropna()
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown(f"### ⚡ **KWAN TEST**")
    c1, c2 = st.columns(2)
    if c1.button("🇹🇭 TH", use_container_width=True): st.session_state.lang = 'TH'; st.rerun()
    if c2.button("🇺🇸 EN", use_container_width=True): st.session_state.lang = 'EN'; st.rerun()
    
    st.divider()
    page = st.radio(t("โหมดการทำงาน", "Mode"), [t("🔍 วิเคราะห์รายตัว", "Single View"), t("📊 กระดาน 4 จอ", "4-Screen Grid")])
    timeframe = st.selectbox(t("ช่วงเวลา", "Timeframe"), ('5min', '15min', '1hour', '1day'))
    
    st.divider()
    st.markdown(f"**⚙️ {t('ตั้งค่ากราฟ', 'Settings')}**")
    show_ema50 = st.checkbox(f"🟡 EMA 50 ({t('กลาง', 'Mid')})", value=True)
    show_ema200 = st.checkbox(f"🟣 EMA 200 ({t('ยาว', 'Long')})", value=True)
    
    st.divider()
    if st.button("🔄 " + t("ล้างข้อมูล", "Refresh Data"), use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.divider()
    for cat, items in ASSET_GROUPS.items():
        with st.expander(cat, expanded=True):
            for sym, name in items.items():
                if st.button(f"{name}", key=f"s_{sym}", use_container_width=True):
                    st.session_state.selected_stock = sym
                    st.rerun()

# --- 5. MAIN CONTENT ---
if page == t("🔍 วิเคราะห์รายตัว", "Single View"):
    symbol = st.session_state.selected_stock
    df = get_pro_data(symbol, timeframe)

    if not df.empty:
        col_h, col_r = st.columns([4, 1])
        col_h.subheader(f"📊 {symbol} ({timeframe})")
        if col_r.button("🎯 Reset View", use_container_width=True): st.rerun()
        
        # Header Metrics
        curr = df['close'].iloc[-1]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(t("ราคาล่าสุด", "Price"), f"{curr:,.2f}", f"{curr - df['close'].iloc[-2]:,.2f}")
        m2.metric(t("แนวต้าน", "Resistance"), f"{df['res'].iloc[-1]:,.2f}")
        m3.metric(t("แนวรับ", "Support"), f"{df['sup'].iloc[-1]:,.2f}")
        m4.metric(t("กำไรระบบ", "Strategy Profit"), f"{df['cum_ret'].iloc[-1]*100:.2f}%")


        chart = StreamlitChart(height=550)
        

        chart.legend(visible=True, font_size=14, font_family='Trebuchet MS')
        
        chart.set(df)
        
        if show_ema50:

            l50 = chart.create_line(name='EMA 50', color='rgba(255, 235, 59, 0.8)')
            l50.set(df[['time', 'ema50']].rename(columns={'ema50': 'EMA 50'}))
            
        if show_ema200:

            l200 = chart.create_line(name='EMA 200', color='rgba(224, 64, 251, 0.9)')
            l200.set(df[['time', 'ema200']].rename(columns={'ema200': 'EMA 200'}))
            
        chart.load()


        # Detailed Analysis
    with st.expander(t("🔍 วิเคราะห์จุดเข้า-ออก", "Signal Insight"), expanded=True):
            s_col1, s_col2 = st.columns([1, 2])
            with s_col1:
                last_sig = df['signal'].iloc[-1]
                ema200_now = df['ema200'].iloc[-1]
                trend = "BULL" if curr > ema200_now else "BEAR"
                st.markdown(f"**Trend:** {'🟢' if trend=='BULL' else '🔴'} {trend}")
                
                if last_sig == 1:
                    st.success(t("✅ ซื้อ (Breakout)", "✅ BUY"))
                    if trend == "BEAR": st.warning(t("⚠️ ระวัง! สวนเทรนด์ใหญ่", "⚠️ Counter-Trend"))
                elif last_sig == -1:
                    st.error(t("❌ ขาย (Breakdown)", "❌ SELL"))
                else:
                    st.info(t("⌛ ถือ/รอ (Sideway)", "⌛ HOLD/WAIT"))
            with s_col2:
                st.table(df[df['signal'] != 0][['time', 'close', 'signal']].tail(3))
else:
    # --- 4-SCREEN GRID ---
    st.subheader(t("📊 กระดาน 4 จอ", "4-Screen Grid"))
    def render_grid(key, def_idx):
        sel = st.selectbox(f"จอ {key}", ALL_SYMBOLS, index=def_idx, key=f"gs_{key}")
        d = get_pro_data(sel, timeframe)
        if not d.empty:
            st.markdown(f"**{sel}** | {d['close'].iloc[-1]:,.2f}")
            c = StreamlitChart(height=300); c.set(d)
            if show_ema50:
                l50 = c.create_line(color='rgba(255, 235, 59, 0.8)')
                l50.set(d[['time', 'ema50']].rename(columns={'ema50': 'value'}))
            if show_ema200:
                l200 = c.create_line(color='rgba(224, 64, 251, 0.9)')
                l200.set(d[['time', 'ema200']].rename(columns={'ema200': 'value'}))
            c.load()

    r1c1, r1c2 = st.columns(2)
    with r1c1: render_grid(1, 0)
    with r1c2: render_grid(2, 1)
    st.divider()
    r2c1, r2c2 = st.columns(2)
    with r2c1: render_grid(3, 2)
    with r2c2: render_grid(4, 3)

# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from lightweight_charts.widgets import StreamlitChart
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURATION & STYLING ---
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

# ✅ สร้างตัวแปรรวมรายชื่อหุ้นทั้งหมด (แก้ Error ที่คุณเจอ)
ALL_SYMBOLS = [s for sub in ASSET_GROUPS.values() for s in sub]

# --- 3. DATA ENGINE ---
@st.cache_data(ttl=15)
def get_pro_data(symbol, timeframe):
    tf_map = {'5min': '5m', '15min': '15m', '1hour': '1h', '1day': '1d'}
    interval = tf_map.get(timeframe, '1d')
    period = '2y' if timeframe == '1day' else '60d'
    try:
        df = yf.download(symbol, interval=interval, period=period, progress=False)
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.reset_index().rename(columns={'Datetime': 'time', 'Date': 'time'})
        df.columns = df.columns.str.lower()
        df['res'] = df['high'].rolling(window=20).max()
        df['sup'] = df['low'].rolling(window=20).min()
        df['signal'] = 0
        df.loc[df['close'] > df['res'].shift(1), 'signal'] = 1
        df.loc[df['close'] < df['sup'].shift(1), 'signal'] = -1
        df['strat_ret'] = df['signal'].shift(1) * df['close'].pct_change()
        df['cum_ret'] = (1 + df['strat_ret'].fillna(0)).cumprod() - 1
        return df.dropna()
    except: return pd.DataFrame()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("### ⚡ **KWAN TEST**")
    c1, c2 = st.columns(2)
    if c1.button("🇹🇭 TH", use_container_width=True): st.session_state.lang = 'TH'; st.rerun()
    if c2.button("🇺🇸 EN", use_container_width=True): st.session_state.lang = 'EN'; st.rerun()
    
    st.divider()
    page = st.radio(t("โหมดการทำงาน", "System Mode"), [t("🔍 วิเคราะห์รายตัว", "🔍 Single View"), t("📊 กระดาน 4 จอ", "📊 4-Screen Grid")])
    timeframe = st.selectbox(t("ช่วงเวลา", "Timeframe"), ('5min', '15min', '1hour', '1day'))
    
    for cat, items in ASSET_GROUPS.items():
        with st.expander(cat, expanded=True):
            for sym, name in items.items():
                if st.button(f"{name}", key=f"s_{sym}", use_container_width=True):
                    st.session_state.selected_stock = sym
                    st.rerun()

# --- 5. MAIN CONTENT ---
if page == t("🔍 วิเคราะห์รายตัว", "🔍 Single View"):
    symbol = st.session_state.selected_stock
    df = get_pro_data(symbol, timeframe)
    
    if not df.empty:
        col_h, col_r = st.columns([4, 1])
        col_h.subheader(f"📊 {symbol} ({timeframe})")
        if col_r.button("🎯 Reset View", use_container_width=True): st.rerun()

        m1, m2, m3, m4 = st.columns(4)
        curr = df['close'].iloc[-1]
        m1.metric(t("ราคาล่าสุด", "Last Price"), f"{curr:,.2f}", f"{curr - df['close'].iloc[-2]:,.2f}")
        m2.metric(t("แนวต้าน", "Resistance"), f"{df['res'].iloc[-1]:,.2f}")
        m3.metric(t("แนวรับ", "Support"), f"{df['sup'].iloc[-1]:,.2f}")
        m4.metric(t("กำไรระบบ", "Strategy Profit"), f"{df['cum_ret'].iloc[-1]*100:.2f}%")

        chart = StreamlitChart(height=550)
        chart.set(df)
        chart.load()

        st.markdown('<div style="height:1px;"></div>', unsafe_allow_html=True)
        with st.expander(t("🔍 วิเคราะห์จุดเข้า-ออก แบบละเอียด", "🔍 Trade Signals & Detailed Insight"), expanded=True):
            tab_sig, tab_info = st.tabs([t("📊 สัญญาณปัจจุบัน", "📊 Trade Signal"), t("🏢 ข้อมูลพื้นฐาน", "🏢 Asset Info")])
            with tab_sig:
                s_col1, s_col2 = st.columns([1, 2])
                with s_col1:
                    last_sig = df['signal'].iloc[-1]
                    res_p, sup_p = df['res'].iloc[-1], df['sup'].iloc[-1]
                    # Logic ถือ/รอ แบบละเอียด
                    if last_sig == 1: st.success(t("✅ ซื้อ (Breakout)", "✅ BUY"))
                    elif last_sig == -1: st.error(t("❌ ขาย (Breakdown)", "❌ SELL"))
                    else:
                        d_res = (res_p - curr)/curr * 100
                        d_sup = (curr - sup_p)/curr * 100
                        if d_res < 1.5: st.warning(t("⌛ รอ: จ่อเบรกแนวต้าน", "⌛ Wait: Near Resistance"))
                        elif d_sup < 1.5: st.warning(t("⌛ รอ: จ่อหลุดแนวรับ", "⌛ Wait: Near Support"))
                        else: st.info(t("⌛ ถือ/รอ: พักตัวในกรอบ", "⌛ Hold/Wait: Sideways"))
                with s_col2:
                    st.table(df[df['signal'] != 0][['time', 'close', 'signal']].tail(3))
            with tab_info:
                try:
                    inf = yf.Ticker(symbol).info
                    st.write(f"**Name:** {inf.get('longName', symbol)}")
                    st.caption(inf.get('longBusinessSummary', '-')[:300] + "...")
                except: st.write("No Data")

else:
    # --- 6. 4-SCREEN GRID (Fixed & Selectable) ---
    st.subheader(t("📊 กระดาน 4 จอ", "📊 4-Screen Multi-Grid"))
    
    def render_selectable_grid(key, default_index):
        # ป้องกัน index เกินจำนวนหุ้นที่มี
        idx = default_index if default_index < len(ALL_SYMBOLS) else 0
        selected_sym = st.selectbox(f"จอที่ {key}", ALL_SYMBOLS, index=idx, key=f"grid_sel_{key}")
        d = get_pro_data(selected_sym, timeframe)
        if not d.empty:
            st.markdown(f"**{selected_sym}** | Profit: {d['cum_ret'].iloc[-1]*100:.1f}%")
            c = StreamlitChart(height=320); c.set(d); c.load()

    r1c1, r1c2 = st.columns(2)
    with r1c1: render_selectable_grid(1, 0)
    with r1c2: render_selectable_grid(2, 1)
    st.divider()
    r2c1, r2c2 = st.columns(2)
    with r2c1: render_selectable_grid(3, 2)
    with r2c2: render_selectable_grid(4, 3)


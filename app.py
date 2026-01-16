# -*- coding: utf-8 | แนะนำให้ Save ไฟล์เป็น UTF-8 -*-
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
        /* จัดการหน้าจอให้ชิดขอบที่สุด */
        .block-container { padding-top: 0.5rem; padding-bottom: 0rem; }
        [data-testid="stSidebarNav"] { padding-top: 0rem; }
        
        /* Sidebar Buttons: 1px Gap & Hover Effect */
        [data-testid="stSidebar"] .stButton > button {
            height: 2.0rem;
            font-size: 14px;
            margin-bottom: 1px !important;
            border-radius: 4px;
            text-align: left;
            padding-left: 10px;
            transition: all 0.2s;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background-color: #ff4b4b;
            color: white;
        }

        /* 1px Gap for Info Expanders */
        .stExpander { border: 1px solid rgba(255,255,255,0.1); margin-bottom: 1px !important; }
        
        /* Metric Box Styling */
        div[data-testid="stMetric"] {
            background-color: rgba(255,255,255,0.05);
            padding: 10px;
            border-radius: 5px;
        }
    </style>
    """, unsafe_allow_html=True)

# ✅ 2. REAL-TIME ENGINE
st_autorefresh(interval=30000, key="Test")

# --- 3. SYSTEM STATE & ASSETS ---
if 'lang' not in st.session_state: st.session_state.lang = 'TH'
if 'selected_stock' not in st.session_state: st.session_state.selected_stock = "AAPL"

def t(th, en): return th if st.session_state.lang == 'TH' else en

ASSET_GROUPS = {
    "🇺🇸 US MARKET": {"AAPL": "🍎APPLE", "TSLA": "🚗TESLA", "NVDA": "🎮NVIDIA", "MSFT": "💻MICROSOFT", "GOOGL": "🔍 GOOGLE"},
    "🇹🇭 THAI MARKET": {"CPALL.BK": "🛒 CPALL", "PTT.BK": "⛽ PTT", "AOT.BK": "✈️ AOT","KBANK.BK": "🏦 KBANK", "DELTA.BK": "🔌 DELTA"},
    "🪙 CRYPTO": {"BTC-USD": "₿ BITCOIN", "ETH-USD": "💎 ETHEREUM", "BNB-USD": "🔶 BINANCE"},
    "📈 ดัชนี (Indices)": {"^SET.BK": "🇹🇭 SET Index", "^GSPC": "🇺🇸 S&P 500", "^IXIC": "🇺🇸 Nasdaq"}
}   

# --- 4. BACKTEST & ANALYTICS ENGINE ---
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
        
        # 📊 คำนวณแนวรับ-แนวต้าน (Donchian 20)
        df['res'] = df['high'].rolling(window=20).max()
        df['sup'] = df['low'].rolling(window=20).min()
        
        # ⚡ สัญญาณซื้อขาย (Backtest Logic)
        df['signal'] = 0
        df.loc[df['close'] > df['res'].shift(1), 'signal'] = 1  # Buy Breakout
        df.loc[df['close'] < df['sup'].shift(1), 'signal'] = -1 # Sell Breakdown
        
        # 📉 คำนวณกำไรสะสม
        df['strat_ret'] = df['signal'].shift(1) * df['close'].pct_change()
        df['cum_ret'] = (1 + df['strat_ret'].fillna(0)).cumprod() - 1
        return df.dropna()
    except: return pd.DataFrame()

# --- 5. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("### ⚡ **KWAN**")
    c1, c2 = st.columns(2)
    if c1.button("🇹🇭 TH", use_container_width=True): st.session_state.lang = 'TH'; st.rerun()
    if c2.button("🇺🇸 EN", use_container_width=True): st.session_state.lang = 'EN'; st.rerun()
    
    st.divider()
    page = st.radio(t("โหมดการทำงาน", "System Mode"), [t("🔍 วิเคราะห์รายตัว", "🔍 Single View"), t("📊 กระดาน 4 จอ", "📊 4-Screen Grid")])
    timeframe = st.selectbox(t("ช่วงเวลา", "Timeframe"), ('5min', '15min', '1hour', '1day'))
    
    st.divider()
    for cat, items in ASSET_GROUPS.items():
        with st.expander(cat, expanded=True):
            for sym, name in items.items():
                # ใส่ไอคอนตรงหน้าชื่อหุ้นเพื่อให้ชัดเจน
                if st.button(f" {name}", key=f"s_{sym}", use_container_width=True):
                    st.session_state.selected_stock = sym
                    st.rerun()

# --- 6. MAIN CONTENT ---
if page == t("🔍 วิเคราะห์รายตัว", "🔍 Single View"):
    symbol = st.session_state.selected_stock
    df = get_pro_data(symbol, timeframe)
    
    if not df.empty:
        # Header & Summary
        col_h, col_r = st.columns([4, 1])
        col_h.subheader(f"📊 {symbol} ({timeframe})")
        if col_r.button("🎯 Reset View", use_container_width=True): st.rerun()

        m1, m2, m3, m4 = st.columns(4)
        curr = df['close'].iloc[-1]
        diff = curr - df['close'].iloc[-2]
        m1.metric(t("ราคาล่าสุด", "Last Price"), f"{curr:,.2f}", f"{diff:,.2f}")
        m2.metric(t("แนวต้าน", "Resistance"), f"{df['res'].iloc[-1]:,.2f}")
        m3.metric(t("แนวรับ", "Support"), f"{df['sup'].iloc[-1]:,.2f}")
        m4.metric(t("กำไรจากระบบ", "System Profit"), f"{df['cum_ret'].iloc[-1]*100:.2f}%")

        # 📈 กราฟหลัก
        chart = StreamlitChart(height=550)
        chart.set(df)
        chart.load()

        # 📋 ข้อมูลเชิงลึก & Backtest (เว้น 1px)
        st.markdown('<div style="height:1px;"></div>', unsafe_allow_html=True)
        with st.expander(t("🔍 วิเคราะห์จุดเข้า-ออก และ Backtest", "🔍 Trade Signals & Backtest"), expanded=True):
            tab_sig, tab_info = st.tabs([t("📊 สัญญาณปัจจุบัน", "📊 Trade Signal"), t("🏢 ข้อมูลพื้นฐาน", "🏢 Asset Info")])
            
            with tab_sig:
                s_col1, s_col2 = st.columns([1, 2])
                with s_col1:
                    last_sig = df['signal'].iloc[-1]
                    if last_sig == 1: st.success(t("✅ สัญญาณ: ซื้อ", "✅ Signal: BUY"))
                    elif last_sig == -1: st.error(t("❌ สัญญาณ: ขาย", "❌ Signal: SELL"))
                    else: st.warning(t("⌛ สัญญาณ: ถือ/รอ", "⌛ Signal: HOLD"))
                with s_col2:
                    st.write(t("**รายการเทรดล่าสุด**", "**Recent Trade Log**"))
                    log = df[df['signal'] != 0][['time', 'close', 'signal']].tail(3)
                    st.table(log)

            with tab_info:
                try:
                    info = yf.Ticker(symbol).info
                    st.write(f"**Business:** {info.get('longName', symbol)}")
                    st.caption(info.get('longBusinessSummary', '-')[:500] + "...")
                except: st.write("No Data Found")
else:
    # 📊 กระดาน 4 จอ
    st.subheader(t("📊 กระดาน 4 จออัจฉริยะ", "📊 4-Screen Multi-Grid"))
    grid_syms = ["AAPL", "TSLA", "BTC-USD", "CPALL.BK"]
    
    def draw_grid(sym):
        d = get_pro_data(sym, timeframe)
        if not d.empty:
            st.markdown(f"**{sym}** | Ret: {d['cum_ret'].iloc[-1]*100:.1f}%")
            c = StreamlitChart(height=320); c.set(d); c.load()

    r1_c1, r1_c2 = st.columns(2)
    with r1_c1: draw_grid(grid_syms[0])
    with r1_c2: draw_grid(grid_syms[1])
    r2_c1, r2_c2 = st.columns(2)
    with r2_c1: draw_grid(grid_syms[2])
    with r2_c2: draw_grid(grid_syms[3])

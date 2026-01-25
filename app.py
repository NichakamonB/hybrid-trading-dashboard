import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import glob
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# --- Try Import tvDatafeed safely ---
try:
    from tvDatafeed import TvDatafeed, Interval
except ImportError:
    st.error("⚠️ Library Missing: tvDatafeed. Please install: pip install git+https://github.com/rongardF/tvdatafeed.git")
    st.stop()

# ==========================================
# 1. CONFIGURATION & UI THEME
# ==========================================
st.set_page_config(
    page_title="Stock Scanner Pro (Cached)", 
    layout="wide", 
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# Custom CSS: Neon & Glassmorphism
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'Prompt', sans-serif; }
    
    .stApp {
        background-color: #0b0f19;
        background-image: 
            radial-gradient(at 0% 0%, rgba(41, 98, 255, 0.15) 0px, transparent 50%),
            radial-gradient(at 100% 0%, rgba(233, 30, 99, 0.1) 0px, transparent 50%);
        color: #e0e0e0;
    }
    
    [data-testid="stSidebar"] { background-color: rgba(17, 24, 39, 0.95); border-right: 1px solid rgba(255, 255, 255, 0.05); }

    /* Custom Radio Buttons */
    div[role="radiogroup"] > label > div:first-child { display: none !important; }
    div[role="radiogroup"] label {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 8px !important;
        padding: 8px !important;
        margin-bottom: 4px !important;
        color: #b0bec5 !important;
        justify-content: center;
    }
    div[role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: rgba(100, 181, 246, 0.5) !important;
    }
    div[role="radiogroup"] label[data-baseweb="radio"] {
        background: linear-gradient(90deg, rgba(41, 98, 255, 0.8) 0%, rgba(21, 101, 192, 0.8) 100%) !important;
        border: 1px solid #2962ff !important;
        color: #fff !important;
        box-shadow: 0 0 10px rgba(41, 98, 255, 0.3);
    }

    /* Cards */
    .metric-card {
        background: rgba(30, 41, 59, 0.4); backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px;
        padding: 15px; text-align: center; margin-bottom: 10px; height: 100%;
    }
    .val-box { font-size: 1.4rem; font-weight: 600; margin: 5px 0; }
    .status-bull { color: #00e676; text-shadow: 0 0 10px rgba(0, 230, 118, 0.3); }
    .status-bear { color: #ff1744; text-shadow: 0 0 10px rgba(255, 23, 68, 0.3); }
    .status-neutral { color: #ffea00; }
    
    .stats-header {
        background: linear-gradient(90deg, rgba(41, 98, 255, 0.2), transparent);
        border-left: 4px solid #2962ff;
        padding: 8px 15px; border-radius: 0 8px 8px 0;
        margin-bottom: 10px; font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

EMA_COLORS = { 5: '#00e676', 10: '#ffea00', 20: '#2979ff', 50: '#ff9100', 89: '#d500f9', 200: '#ffffff' }

# ==========================================
# 2. CACHED DATA FUNCTIONS (CORE ENGINE)
# ==========================================

@st.cache_resource(ttl=None)
def get_tv_instance():
    """Singleton for TV Datafeed connection."""
    try:
        username = st.secrets.get("TV_USERNAME")
        password = st.secrets.get("TV_PASSWORD")
        if username and password:
            return TvDatafeed(username=username, password=password)
        return TvDatafeed()
    except:
        return TvDatafeed()

@st.cache_data(ttl=3600) # Cache Watchlist for 1 Hour
def load_watchlist() -> Optional[pd.DataFrame]:
    """Load Excel files or generate Fallback Watchlist."""
    all_files = glob.glob("**/resistance_*.xlsx", recursive=True)
    
    if not all_files:
        # Fallback Mock Data if no Excel found
        data = {
            'Symbol': ['PTT', 'AOT', 'DELTA', 'KBANK', 'SCB', 'CPALL', 'TSLA', 'AAPL', 'NVDA'],
            'Source': ['SET']*6 + ['NASDAQ']*3,
            'Exchange': ['SET']*6 + ['NASDAQ']*3,
            'Attempts': [20, 15, 10, 25, 12, 8, 50, 45, 60],
            '+1': [18, 12, 9, 20, 10, 6, 30, 25, 40]
        }
        df = pd.DataFrame(data)
        df['WinRate'] = (df['+1'] / df['Attempts']) * 100
        return df
    
    df_list = []
    for f in all_files:
        try:
            df_temp = pd.read_excel(f)
            folder = os.path.dirname(f)
            if folder: name = folder.replace("resistance_", "").replace("_Turbo", "").upper()
            else: name = os.path.basename(f).replace("resistance_", "").replace(".xlsx", "").upper()
            
            df_temp['Source'] = name
            df_temp['Symbol'] = df_temp['Symbol'].astype(str).str.replace(r'\.0$', '', regex=True)
            if 'Exchange' not in df_temp.columns: df_temp['Exchange'] = 'SET'
            df_list.append(df_temp)
        except: continue 
            
    if df_list:
        combined = pd.concat(df_list, ignore_index=True)
        if 'Attempts' in combined.columns:
            combined['WinRate'] = (combined['+1'] / combined['Attempts']) * 100 
        else: combined['WinRate'] = 0
        combined = combined.fillna(0).sort_values(by=['WinRate', 'Attempts'], ascending=[False, False])
        return combined.drop_duplicates(subset=['Symbol'], keep='first')
    return None

def generate_dummy_data(symbol="DEMO"):
    """Generates synthetic Random Walk data to prevent crashes."""
    dates = pd.date_range(end=datetime.now(), periods=200, freq='B')
    base = 100
    rets = np.random.normal(0, 0.02, 200)
    close = base * np.cumprod(1 + rets)
    high = close * (1 + np.abs(np.random.normal(0, 0.01, 200)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, 200)))
    open_p = close * (1 + np.random.normal(0, 0.005, 200))
    vol = np.random.randint(1000, 50000, size=200)
    
    df = pd.DataFrame({'open': open_p, 'high': high, 'low': low, 'close': close, 'volume': vol}, index=dates)
    df = calculate_indicators(df)
    df['signal'] = False
    return df

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    # MACD
    exp12 = df['close'].ewm(span=12, adjust=False).mean()
    exp26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal']
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    # EMAs
    for span in [5, 10, 20, 50, 89, 200]:
        df[f'EMA{span}'] = df['close'].ewm(span=span, adjust=False).mean()
    return df

def process_shooting_star(df: pd.DataFrame) -> pd.DataFrame:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    bodyTop, bodyBot = np.maximum(o, c), np.minimum(o, c)
    body = bodyTop - bodyBot
    rng = (h - l).replace(0, 0.0001)
    upperWick = h - bodyTop
    lowerWick = bodyBot - l
    
    notDoji = body > rng * 0.15
    lowerShort = lowerWick <= body * 0.40
    upTrend = c > c.rolling(20).mean()
    prevGreen = c.shift(1) > o.shift(1)
    gapUp = o > c.shift(1) 
    wickC = upperWick >= body * 2
    
    df["signal"] = (notDoji & wickC & lowerShort & upTrend & prevGreen & gapUp)
    return df

@st.cache_data(ttl=1800, show_spinner=False) # Cache Stock Data for 30 mins
def get_stock_data(symbol: str, exchange: str, force_exchange: str = "Auto") -> Tuple[Optional[pd.DataFrame], bool]:
    tv = get_tv_instance()
    symbol = str(symbol).strip().replace(".0", "")
    target = str(exchange).strip().upper() if force_exchange == "Auto" else force_exchange
    
    attempts = []
    if force_exchange != "Auto": attempts.append({'s': symbol, 'e': force_exchange})
    attempts += [{'s': symbol, 'e': target}, {'s': symbol, 'e': 'SET'}, {'s': symbol, 'e': 'NASDAQ'}]
    if target in ['HK', 'HKEX']: attempts.append({'s': symbol.zfill(4), 'e': 'HKEX'})

    for a in attempts:
        try:
            if a['e'] in ["NAN", "UNNAMED"]: continue
            df = tv.get_hist(symbol=a['s'], exchange=a['e'], interval=Interval.in_daily, n_bars=300)
            if df is not None and not df.empty:
                df = calculate_indicators(df)
                df = process_shooting_star(df)
                return df, True
        except: continue

    return generate_dummy_data(symbol), False

# ==========================================
# 3. CHART & UI HELPERS
# ==========================================
def create_chart(df: pd.DataFrame, config: Dict) -> go.Figure:
    row_specs = [{'height': 0.6}]
    if config['macd']: row_specs.append({'height': 0.2})
    if config['rsi']: row_specs.append({'height': 0.2})
    
    fig = make_subplots(rows=len(row_specs), cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[r['height'] for r in row_specs])
    
    # Price
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price', increasing_line_color='#00e676', decreasing_line_color='#ff1744'), row=1, col=1)
    
    if config['trend']:
        for e in config['emas']:
            if f'EMA{e}' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df[f'EMA{e}'], mode='lines', name=f'EMA{e}', line=dict(color=EMA_COLORS.get(e, 'white'), width=1)), row=1, col=1)
    
    if config['star'] and 'signal' in df.columns:
        star = df[df['signal'] == True]
        if not star.empty:
            fig.add_trace(go.Scatter(x=star.index, y=star['high']*1.02, mode='markers', marker=dict(symbol='arrow-down', size=12, color='#ffea00'), name='Star'), row=1, col=1)

    r = 2
    if config['macd']:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#2979ff'), name='MACD'), row=r, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], line=dict(color='#ff9100'), name='Sig'), row=r, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], marker_color=['#00e676' if x>0 else '#ff1744' for x in df['MACD_Hist']], name='Hist'), row=r, col=1)
        r += 1
    
    if config['rsi']:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#d500f9'), name='RSI'), row=r, col=1)
        fig.add_hline(y=70, line_dash='dash', line_color='red', row=r, col=1)
        fig.add_hline(y=30, line_dash='dash', line_color='green', row=r, col=1)

    fig.update_layout(height=400 + (len(row_specs)*150), margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#b0bec5', family='Prompt'), showlegend=False, xaxis_rangeslider_visible=False, hovermode='x unified')
    fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.06)'); fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.06)')
    return fig

def create_card(title, value, status, sub=""):
    return f"<div class='metric-card'><h4 style='margin:0;opacity:0.8'>{title}</h4><div class='val-box status-{status}'>{value}</div><div style='font-size:0.8em;opacity:0.6'>{sub}</div></div>"

# ==========================================
# 4. MAIN APPLICATION
# ==========================================
def main():
    # --- Sidebar Controls ---
    st.sidebar.title("⚡ Scanner Pro")
    
    if st.sidebar.button("🔄 Refresh Cache", help="Clear memory and reload data"):
        st.cache_data.clear()
        st.rerun()

    # --- Load Data (Cached) ---
    with st.spinner("📂 Loading Watchlist..."):
        df_watch = load_watchlist()
    
    if df_watch is None: st.error("Fatal Error: Watchlist Failed"); st.stop()

    # --- Filters ---
    st.sidebar.subheader("🎯 Filters")
    sources = sorted(df_watch['Source'].unique())
    sel_src = st.sidebar.multiselect("Markets", sources, default=sources)
    min_att = st.sidebar.slider("Min Count", 0, 50, 5)
    
    mask = (df_watch['Source'].isin(sel_src)) & (df_watch['Attempts'] >= min_att)
    filtered = df_watch[mask].sort_values(by=['WinRate', 'Attempts'], ascending=[False, False])
    
    # --- Settings ---
    st.sidebar.markdown("---")
    show_trend = st.sidebar.checkbox("Trend", True)
    show_macd = st.sidebar.checkbox("MACD", True)
    show_rsi = st.sidebar.checkbox("RSI", False)
    show_star = st.sidebar.checkbox("Shooting Star", True)
    sel_emas = st.sidebar.multiselect("EMA", [5, 20, 50, 200], [20, 50, 200]) if show_trend else []

    # --- Layout ---
    col_list, col_main = st.columns([1, 4])
    
    with col_list:
        st.markdown("### Watchlist")
        search = st.text_input("🔍", placeholder="Search Symbol", label_visibility="collapsed")
        if search: filtered = filtered[filtered['Symbol'].str.contains(search, case=False, na=False)]
        
        st.markdown(f"<div class='stats-header'>Matches: <strong>{len(filtered)}</strong></div>", unsafe_allow_html=True)
        
        if not filtered.empty:
            filtered['Label'] = filtered.apply(lambda x: f"{x['Symbol']} | {int(x['WinRate'])}%", axis=1)
            with st.container(height=650):
                sel_label = st.radio("List", filtered['Label'].tolist(), label_visibility="collapsed")
            sel_row = filtered[filtered['Label'] == sel_label].iloc[0]
            sel_sym, sel_ex = sel_row['Symbol'], sel_row['Exchange']
        else:
            st.warning("No Data"); st.stop()

    with col_main:
        c1, c2 = st.columns([3, 1])
        with c1: st.markdown(f"## 🚀 {sel_sym} <span style='color:#90caf9;font-size:0.6em'>({sel_ex})</span>", unsafe_allow_html=True)
        with c2: range_t = st.radio("Time", ["3M", "6M", "1Y"], index=1, horizontal=True, label_visibility="collapsed")
        
        # --- Fetch Stock Data (Cached) ---
        with st.spinner(f"📡 Downloading {sel_sym}..."):
            df, is_live = get_stock_data(sel_sym, sel_ex)
            
        if df is not None:
            df.index = pd.to_datetime(df.index).normalize()
            if is_live: st.success(f"🟢 Connected: {sel_ex}", icon="📶")
            else: st.warning(f"🟠 Simulation Data (API Timeout)", icon="⚠️")
            
            # Slice Data
            bars = 66 if range_t == "3M" else (132 if range_t == "6M" else 252)
            d_view = df.tail(bars)
            last = df.iloc[-1]

            # KPI Cards
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                mp, mc = last.get('MACD',0)>0, last.get('MACD',0)>last.get('Signal',0)
                st.markdown(create_card("MACD", "BULL" if mp else "BEAR", "bull" if mp else "bear", "Cross UP" if mc else "Down"), unsafe_allow_html=True)
            with k2:
                r = last.get('RSI', 50)
                st.markdown(create_card("RSI", f"{r:.1f}", "bear" if r>70 else "bull" if r<30 else "neutral", "Over" if r>70 else "Norm"), unsafe_allow_html=True)
            with k3:
                ema_bull = sum([1 for e in sel_emas if last['close'] > last.get(f'EMA{e}', 999999)])
                st.markdown(create_card("TREND", f"{ema_bull}/{len(sel_emas)}", "bull" if ema_bull==len(sel_emas) else "neutral", "EMAs Passed"), unsafe_allow_html=True)
            with k4:
                is_star = last.get('signal', False)
                st.markdown(create_card("PATTERN", "STAR" if is_star else "-", "bear" if is_star else "neutral", "Detected" if is_star else "None"), unsafe_allow_html=True)

            # Chart
            config = {'trend': show_trend, 'macd': show_macd, 'rsi': show_rsi, 'star': show_star, 'emas': sel_emas}
            st.plotly_chart(create_chart(d_view, config), use_container_width=True)
        else:
            st.error("Data Load Failed")

if __name__ == "__main__":
    main()

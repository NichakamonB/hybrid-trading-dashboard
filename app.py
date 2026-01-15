import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from lightweight_charts.widgets import StreamlitChart

# ตั้งค่าหน้าเว็บเป็นแบบ Wide Screen
st.set_page_config(layout="wide", page_title="Hybrid Trading Dashboard")

# --- 1. ฟังก์ชันดึงข้อมูล (ใส่ Cache เพื่อความเร็ว) ---
@st.cache_data(ttl=300) # เก็บข้อมูลไว้ 5 นาที ไม่ต้องโหลดใหม่ถ้ารีเฟรช
def get_processed_data(symbol, timeframe):
    tf_map = {'1min': '1m', '5min': '5m', '15min': '15m', '30min': '30m', '1hour': '1h', '1day': '1d'}
    interval = tf_map.get(timeframe, '1d')
    
    # ดึงข้อมูลย้อนหลัง (ปรับตาม Timeframe)
    period = '1mo' if timeframe in ['1hour', '1day'] else '5d'
    
    try:
        print(f"Loading {symbol}...")
        df = yf.download(symbol, interval=interval, period=period, progress=False)
        if df.empty: return pd.DataFrame()

        # แก้ปัญหา MultiIndex ของ yfinance เวอร์ชั่นใหม่
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.reset_index()
        df.columns = df.columns.str.lower()
        
        # เปลี่ยนชื่อคอลัมน์เวลาให้เป็น 'time' ตามที่ Library ต้องการ
        rename_map = {'datetime': 'time', 'date': 'time'}
        df = df.rename(columns=rename_map)
        
        # คำนวณ Indicator
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # ตัดข้อมูลที่มี NaN ออก
        df = df.dropna()
        return df
    except Exception as e:
        st.error(f"Error loading {symbol}: {e}")
        return pd.DataFrame()

# --- 2. ฟังก์ชันวาดกราฟแต่ละช่อง (แก้ไขแล้ว: ไม่มี error key และ column name) ---
def render_chart_panel(key_index, default_symbol, timeframe, stock_list):
    # สร้าง Selectbox (ยังต้องใส่ key เพื่อไม่ให้ Dropdown ตีกันเอง)
    symbol = st.selectbox(f"Select Symbol {key_index}", stock_list, index=stock_list.index(default_symbol), key=f"sel_{key_index}")
    
    # ดึงข้อมูล
    df = get_processed_data(symbol, timeframe)
    
    if not df.empty:
        # 1. สร้างกราฟ (ไม่ต้องใส่ key ใน StreamlitChart แล้ว)
        chart = StreamlitChart(height=350)
        chart.set(df)
        
        # 2. สร้างเส้น EMA โดยระบุชื่อ name ให้ชัดเจน
        line_ema20 = chart.create_line(name='EMA 20', color='rgba(255, 68, 68, 0.8)', width=1)
        line_ema50 = chart.create_line(name='EMA 50', color='rgba(68, 68, 255, 0.8)', width=1)
        
        # 3. ส่งข้อมูลเข้าเส้น (สำคัญ: ต้อง rename คอลัมน์ให้ตรงกับ name ที่ตั้งไว้)
        line_ema20.set(df[['time', 'ema20']].rename(columns={'ema20': 'EMA 20'}))
        line_ema50.set(df[['time', 'ema50']].rename(columns={'ema50': 'EMA 50'}))
        
        chart.load()
    else:
        st.warning(f"No data for {symbol}")

# --- 3. ส่วนแสดงผลหน้าเว็บหลัก ---

st.title("🚀 Real-Time Hybrid Dashboard")

# Sidebar ตั้งค่า
with st.sidebar:
    st.header("⚙️ Settings")
    timeframe = st.selectbox("Timeframe", ('5min', '15min', '30min', '1hour', '1day'), index=1)
    st.info("Data source: Yahoo Finance")

# รายชื่อหุ้น
stock_options = ('TSLA', 'AAPL', 'NVDA', 'BTC-USD', 'ETH-USD', 'MSFT', 'GOOGL', 'CPALL.BK')

# === Grid 2x2 (Lightweight Charts) ===
st.subheader("1. Multi-Chart Grid (Lightweight Charts)")

# แถวบน
col1, col2 = st.columns(2)
with col1:
    render_chart_panel(1, 'TSLA', timeframe, stock_options)
with col2:
    render_chart_panel(2, 'AAPL', timeframe, stock_options)

# แถวล่าง
col3, col4 = st.columns(2)
with col3:
    render_chart_panel(3, 'BTC-USD', timeframe, stock_options)
with col4:
    render_chart_panel(4, 'NVDA', timeframe, stock_options)

st.divider()

# === Analytics (Plotly Hybrid) ===
st.subheader("2. Market Analysis (Plotly Hybrid)")

# คำนวณข้อมูลเปรียบเทียบจากหุ้นที่เลือกอยู่ปัจจุบัน
data_compare = []
# ดึงค่าจาก Selectbox ที่เราสร้างไว้ในฟังก์ชัน (key=sel_1, sel_2, ...)
current_selected = [st.session_state.get(f"sel_{i}", stock_options[i-1]) for i in range(1, 5)]

for sym in current_selected:
    d = get_processed_data(sym, timeframe)
    if not d.empty:
        last_price = d['close'].iloc[-1]
        first_price = d['open'].iloc[-1]
        change_pct = ((last_price - first_price) / first_price) * 100
        data_compare.append({'Symbol': sym, 'Price': last_price, 'Change %': change_pct})

df_compare = pd.DataFrame(data_compare)

if not df_compare.empty:
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.write("### 📊 Performance Heatmap")
        # Bar Chart สวยๆ จาก Plotly
        fig = px.bar(df_compare, x='Symbol', y='Change %', color='Change %',
                     color_continuous_scale=['red', 'gray', 'green'],
                     range_color=[-2, 2],
                     text_auto='.2f',
                     title=f"Price Change % ({timeframe})")
        st.plotly_chart(fig, use_container_width=True)
        
    with c2:
        st.write("### 📈 Price Comparison Table")
        st.dataframe(
            df_compare.style.format({'Price': '{:.2f}', 'Change %': '{:+.2f}%'})
            .background_gradient(subset=['Change %'], cmap='RdYlGn', vmin=-2, vmax=2),
            use_container_width=True
        )
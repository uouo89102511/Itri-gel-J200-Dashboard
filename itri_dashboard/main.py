import streamlit as st

st.set_page_config(
    page_title="ITRI 冷庫數據分析平台",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0a1628 0%, #0d2137 50%, #0a1628 100%); }
    .main .block-container { padding: 2rem 3rem; }

    .hero-title {
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(90deg, #4fc3f7, #42a5f5, #90caf9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.2;
        margin-bottom: 0.3rem;
    }
    .hero-subtitle {
        font-size: 1rem;
        color: #7ab3d4;
        letter-spacing: 0.08em;
        margin-bottom: 0;
    }

    .nav-card {
        background: linear-gradient(145deg, #0d2137 0%, #102840 100%);
        border: 1px solid #1e4976;
        border-radius: 16px;
        padding: 28px 24px 24px 24px;
        height: 100%;
        transition: all 0.25s ease;
        position: relative;
        overflow: hidden;
    }
    .nav-card:hover {
        border-color: #42a5f5;
        box-shadow: 0 0 28px rgba(66,165,245,0.25);
        transform: translateY(-2px);
    }
    .nav-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
    }
    .card-pa60::before { background: linear-gradient(90deg, #f5a623, #f0e233); }
    .card-gm10::before { background: linear-gradient(90deg, #42a5f5, #4fc3f7); }
    .card-compare::before { background: linear-gradient(90deg, #66bb6a, #a5d6a7); }

    .card-icon { font-size: 2.8rem; margin-bottom: 12px; display: block; }
    .card-title { font-size: 1.25rem; font-weight: 700; color: #e3f2fd; margin-bottom: 6px; }
    .card-desc { font-size: 0.85rem; color: #7ab3d4; line-height: 1.6; margin-bottom: 16px; }

    .tag {
        display: inline-block;
        font-size: 0.72rem;
        padding: 2px 9px;
        border-radius: 20px;
        margin-right: 5px;
        margin-bottom: 4px;
        font-weight: 600;
        letter-spacing: 0.04em;
    }
    .tag-yellow { background: rgba(245,166,35,0.15); color: #f5a623; border: 1px solid rgba(245,166,35,0.3); }
    .tag-blue   { background: rgba(66,165,245,0.15); color: #42a5f5; border: 1px solid rgba(66,165,245,0.3); }
    .tag-green  { background: rgba(102,187,106,0.15); color: #66bb6a; border: 1px solid rgba(102,187,106,0.3); }
    .tag-gray   { background: rgba(144,164,174,0.15); color: #90a4ae; border: 1px solid rgba(144,164,174,0.3); }

    .divider { border: none; border-top: 1px solid #1e3a5f; margin: 2rem 0; }

    .info-row {
        background: rgba(13,33,55,0.7);
        border: 1px solid #1e4976;
        border-radius: 10px;
        padding: 14px 20px;
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 0.85rem;
        color: #7ab3d4;
    }
    .footer {
        text-align: center;
        color: #3a5a7a;
        font-size: 0.78rem;
        padding: 1.5rem 0 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ── Hero Header ─────────────────────────────────────────────────────────────
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.markdown("<div style='font-size:4rem; padding-top:10px;'>🧊</div>", unsafe_allow_html=True)
with col_title:
    st.markdown("<div class='hero-title'>ITRI 冷庫數據分析平台</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>GB+44015-2026 ｜ 綠能所 智慧控制設備研究室 ｜ 熱流 + IoT + AI 整合平台</div>", unsafe_allow_html=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

st.markdown("<div style='font-size:0.8rem; color:#4a7fa5; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:1.2rem;'>▸ 選擇分析工具</div>", unsafe_allow_html=True)

# ── Navigation Cards ─────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3, gap="large")

with col1:
    st.markdown("""
    <div class='nav-card card-pa60'>
        <span class='card-icon'>⚡</span>
        <div class='card-title'>PA60 電力分析工具</div>
        <div class='card-desc'>
            互動式電力數據比對，支援多天 CSV 疊圖比較。涵蓋壓縮機、除霜、除霧、冷凝風扇、蒸發風扇各分路耗電分析與梯形積分 kWh 計算。
        </div>
        <span class='tag tag-yellow'>多檔比對</span>
        <span class='tag tag-yellow'>kWh 積分</span>
        <span class='tag tag-yellow'>日報分析</span>
        <span class='tag tag-gray'>PA60 CSV</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⚡ 前往 PA60 分析", use_container_width=True, type="primary", key="btn_pa60"):
        st.switch_page("pages/1_PA60.py")

with col2:
    st.markdown("""
    <div class='nav-card card-gm10'>
        <span class='card-icon'>❄️</span>
        <div class='card-title'>GM10 數位雙生系統</div>
        <div class='card-desc'>
            冷庫溫度數位雙生，8 點庫內感測器 3D 空間可視化，搭配庫外環境（壓縮機溫度、濕度）監控、熱圖與警報診斷。
        </div>
        <span class='tag tag-blue'>3D 溫度圖</span>
        <span class='tag tag-blue'>熱圖分析</span>
        <span class='tag tag-blue'>警報診斷</span>
        <span class='tag tag-gray'>GM10 CSV</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("❄️ 前往 GM10 數位雙生", use_container_width=True, type="primary", key="btn_gm10"):
        st.switch_page("pages/2_GM10.py")

with col3:
    st.markdown("""
    <div class='nav-card card-compare'>
        <span class='card-icon'>📊</span>
        <div class='card-title'>PA60 × GM10 疊圖比對</div>
        <div class='card-desc'>
            同時上傳 PA60 與 GM10 兩種 CSV，將電力數據與溫度數據對齊時間軸疊圖，分析壓縮機運作周期與庫內溫度變化的關聯。
        </div>
        <span class='tag tag-green'>跨儀器疊圖</span>
        <span class='tag tag-green'>時間對齊</span>
        <span class='tag tag-green'>相關分析</span>
        <span class='tag tag-gray'>雙 CSV</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📊 前往疊圖比對", use_container_width=True, type="primary", key="btn_compare"):
        st.switch_page("pages/3_PA60xGM10.py")

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ── Info Row ─────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    st.markdown("""
    <div class='info-row'>
        <span style='font-size:1.4rem;'>📂</span>
        <div><b style='color:#b3d4f0;'>支援格式</b><br>CSV（UTF-8 / UTF-8-BOM）</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class='info-row'>
        <span style='font-size:1.4rem;'>⚙️</span>
        <div><b style='color:#b3d4f0;'>技術棧</b><br>Streamlit + Plotly + Pandas</div>
    </div>
    """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class='footer'>
    🧊 ITRI 冷庫數據分析平台 ｜ 綠能所 智慧控制設備研究室 ｜ GB+44015-2026<br>
</div>
""", unsafe_allow_html=True)

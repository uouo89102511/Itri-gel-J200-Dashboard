"""
商錄冷庫 GM10 數位雙生系統 - 月份分析版
支援多檔（整月）CSV 一次上傳分析
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #050d1a 0%, #071525 50%, #050d1a 100%); color: #cce7ff; }
    .main .block-container { padding: 1rem 2rem 2rem 2rem; }

    .page-header {
        background: linear-gradient(90deg, #071525, #0a1e32);
        border: 1px solid #0e3a5c; border-left: 4px solid #4fc3f7;
        border-radius: 8px; padding: 14px 20px; margin-bottom: 1rem;
        display: flex; align-items: center; gap: 14px;
    }
    .page-header-title { font-size: 1.4rem; font-weight: 700; color: #4fc3f7; line-height: 1.2; }
    .page-header-sub { font-size: 0.8rem; color: #3a7fa0; }

    .kpi-card {
        background: linear-gradient(145deg, #071525 0%, #0a1e32 100%);
        border: 1px solid #0e3a5c; border-radius: 10px;
        padding: 12px 14px; text-align: center;
        box-shadow: 0 2px 12px rgba(0,100,200,0.1); height: 100%;
    }
    .kpi-label { font-size: 0.68rem; color: #2a6a8a; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 3px; }
    .kpi-value { font-size: 1.6rem; font-weight: 700; line-height: 1.1; }
    .kpi-unit  { font-size: 0.76rem; color: #2a6a8a; }
    .kpi-delta { font-size: 0.72rem; margin-top: 3px; }

    .section-title {
        font-size: 0.75rem; font-weight: 600; color: #29b6f6;
        text-transform: uppercase; letter-spacing: 0.1em;
        margin: 14px 0 7px 0; padding-bottom: 4px;
        border-bottom: 1px solid #0e3a5c;
    }

    .badge-ok   { background:#0a2a12; color:#4caf50; border:1px solid #2e7d32; border-radius:6px; padding:2px 10px; font-size:0.76rem; }
    .badge-warn { background:#2a1f00; color:#ffb300; border:1px solid #ff8f00; border-radius:6px; padding:2px 10px; font-size:0.76rem; }
    .badge-err  { background:#2a0a08; color:#ef5350; border:1px solid #c62828; border-radius:6px; padding:2px 10px; font-size:0.76rem; }

    .alert-box { background: rgba(239,83,80,0.1); border-left: 3px solid #ef5350; border-radius: 4px; padding: 7px 12px; margin: 3px 0; font-size: 0.8rem; color: #ef9a9a; }
    .warn-box  { background: rgba(255,179,0,0.1); border-left: 3px solid #ffb300; border-radius: 4px; padding: 7px 12px; margin: 3px 0; font-size: 0.8rem; color: #ffe082; }

    .file-chip {
        display: inline-flex; background: rgba(79,195,247,0.1);
        border: 1px solid rgba(79,195,247,0.3); border-radius: 16px;
        padding: 2px 9px; font-size: 0.74rem; color: #4fc3f7; margin: 2px;
    }

    section[data-testid="stSidebar"] { background: #040c18; border-right: 1px solid #0e3a5c; }
    section[data-testid="stSidebar"] label { color: #4a8aa8 !important; font-size: 0.82rem !important; }

    .upload-prompt {
        background: linear-gradient(145deg, #071525, #0a1e32);
        border: 2px dashed #0e3a5c; border-radius: 12px;
        padding: 40px 24px; text-align: center; margin-top: 1rem;
    }

    .js-plotly-plot { border-radius: 10px; overflow: hidden; }
    .stTabs [data-baseweb="tab-list"] { background: transparent; border-bottom: 1px solid #0e3a5c; }
    .stTabs [data-baseweb="tab"] { color: #3a7fa0; font-size: 0.9rem; }
    .stTabs [aria-selected="true"] { color: #4fc3f7 !important; border-bottom: 2px solid #4fc3f7 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sensor Layout
# ─────────────────────────────────────────────
INSIDE_SENSORS = {
    'CH1': {'label': 'CH1 後左上', 'col_key': 'CH1(測試通道_01)', 'pos': (0, 1, 1)},
    'CH2': {'label': 'CH2 前左上', 'col_key': 'CH2(測試通道_02)', 'pos': (0, 0, 1)},
    'CH3': {'label': 'CH3 前右上', 'col_key': 'CH3(通道 3)',      'pos': (1, 0, 1)},
    'CH4': {'label': 'CH4 後右上', 'col_key': 'CH4(通道 4)',      'pos': (1, 1, 1)},
    'CH5': {'label': 'CH5 後左下', 'col_key': 'CH5(通道 5)',      'pos': (0, 1, 0)},
    'CH6': {'label': 'CH6 前左下', 'col_key': 'CH6(通道 6)',      'pos': (0, 0, 0)},
    'CH7': {'label': 'CH7 前右下', 'col_key': 'CH7(通道 7)',      'pos': (1, 0, 0)},
    'CH8': {'label': 'CH8 後右下', 'col_key': 'CH8(通道 8)',      'pos': (1, 1, 0)},
}
OUTSIDE_SENSORS = {
    'CH104': {'label': 'CH104 上T',      'col_key': 'CH104(通道 104)',         'unit': '°C'},
    'CH101': {'label': 'CH101 壓縮機',   'col_key': 'CH101(一號壓縮機)',         'unit': '°C'},
    'CH102': {'label': 'CH102 左T',      'col_key': 'CH102(通道 102)',         'unit': '°C'},
    'CH103': {'label': 'CH103 前T',      'col_key': 'CH103(通道 103)',         'unit': '°C'},
    'CH106': {'label': 'CH106 前T(溫溼)','col_key': 'CH106(關鍵數據 (CH106))', 'unit': '°C'},
    'CH105': {'label': 'CH105 前H(溫溼)','col_key': 'CH105(通道 105)',         'unit': '%RH'},
}

INSIDE_COLORS = ["#4fc3f7","#29b6f6","#81d4fa","#b3e5fc","#42a5f5","#1e88e5","#90caf9","#e3f2fd"]
OUT_T_COLORS  = ["#ff6b6b","#ffa726","#42a5f5","#66bb6a","#ab47bc"]

def style_fig(fig, height=420):
    fig.update_layout(
        plot_bgcolor="rgba(5,13,26,0.95)", paper_bgcolor="rgba(0,0,0,0)",
        height=height, hovermode="x unified",
        margin=dict(l=8, r=8, t=28, b=8),
        font=dict(color="#5a9ab8"),
        legend=dict(font=dict(color="#5a9ab8", size=10), bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.15),
    )
    fig.update_xaxes(gridcolor="rgba(14,58,92,0.7)", tickfont=dict(color="#3a7a9a"),
                     showspikes=True, spikecolor="#4fc3f7", spikethickness=1)
    fig.update_yaxes(gridcolor="rgba(14,58,92,0.5)", tickfont=dict(color="#3a7a9a"))
    return fig

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <span style="font-size:2rem;">❄️</span>
    <div>
        <div class="page-header-title">商錄冷庫 GM10 數位雙生系統</div>
        <div class="page-header-sub">GB+44015-2026 ｜ 月份分析模式 ｜ 多檔上傳整月資料</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:8px 0;'>
        <div style='font-size:1.6rem;'>❄️</div>
        <div style='color:#4fc3f7; font-weight:700; font-size:1rem;'>GM10 數位雙生</div>
        <div style='color:#3a7fa0; font-size:0.75rem;'>月份分析版</div>
    </div>
    <hr style="border-color:#0e3a5c; margin:8px 0;"/>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "📂 上傳 GM10 CSV（可多選整月）",
        type=["csv"],
        accept_multiple_files=True,
        help="可一次上傳整月或多日的 GM10 CSV，系統會自動串接時間軸"
    )

    st.markdown("---")
    st.markdown('<div class="section-title">⚙️ 顯示設定</div>', unsafe_allow_html=True)
    resample_opt = st.selectbox(
        "資料重採樣（建議月份用 5 分鐘以上）",
        ["1分鐘","5分鐘","15分鐘","30分鐘","1小時"],
        index=1
    )
    show_raw   = st.checkbox("顯示原始通道曲線", value=True)
    show_stats = st.checkbox("顯示統計分析", value=True)

    st.markdown("---")
    st.markdown('<div class="section-title">🌡️ 溫度警戒值</div>', unsafe_allow_html=True)
    alarm_high = st.slider("庫內上限 (°C)", -30, -5, -10, 1)
    alarm_low  = st.slider("庫內下限 (°C)", -40, -20, -30, 1)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.75rem; color:#2a6a8a; line-height:1.8;'>
        <b style='color:#4fc3f7;'>系統資訊</b><br>
        專案: GB+44015-2026<br>
        單位: 綠能所 智慧控制設備研究室<br>
        模組: GM10 Module 1&amp;2
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_gm10_single(file_bytes):
    df = pd.read_csv(io.BytesIO(file_bytes), parse_dates=['時間'])
    df = df.sort_values('時間').reset_index(drop=True)
    return df

if not uploaded_files:
    st.markdown("""
    <div class="upload-prompt">
        <div style="font-size:3rem; margin-bottom:12px;">❄️</div>
        <div style="font-size:1.1rem; font-weight:600; color:#4fc3f7; margin-bottom:6px;">請上傳 GM10 CSV 資料檔（可多選整月）</div>
        <div style="font-size:0.85rem; color:#2a6a8a;">8 點庫內溫度 ｜ 庫外環境監控 ｜ 3D 空間視覺化 ｜ 警報診斷</div>
        <div style="margin-top:16px; font-size:0.78rem; color:#1a4a6a;">
            必要欄位：時間 / CH1-CH8 / CH101-CH106
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Multi-load with progress
all_dfs = []
load_errors = []
progress = st.progress(0, text=f"載入 0/{len(uploaded_files)} 個檔案...")
for i, f in enumerate(uploaded_files):
    try:
        fbytes = f.read()
        df = load_gm10_single(fbytes)
        all_dfs.append(df)
    except Exception as e:
        load_errors.append((f.name, str(e)))
    progress.progress((i+1)/len(uploaded_files), text=f"已載入 {i+1}/{len(uploaded_files)}：{f.name}")
progress.empty()

if load_errors:
    with st.expander(f"⚠️ {len(load_errors)} 個檔案載入失敗", expanded=False):
        for fn, err in load_errors:
            st.caption(f"**{fn}**：{err}")

if not all_dfs:
    st.error("沒有成功載入任何檔案")
    st.stop()

# Concat + dedupe
df_raw = pd.concat(all_dfs, ignore_index=True)
df_raw = df_raw.sort_values('時間').drop_duplicates(subset=['時間']).reset_index(drop=True)

# Compute derived columns
inside_cols_actual = [s['col_key'] for s in INSIDE_SENSORS.values() if s['col_key'] in df_raw.columns]
if inside_cols_actual:
    df_raw['avg_inside_T'] = df_raw[inside_cols_actual].mean(axis=1)
    df_raw['max_inside_T'] = df_raw[inside_cols_actual].max(axis=1)
    df_raw['min_inside_T'] = df_raw[inside_cols_actual].min(axis=1)
    df_raw['uniformity']   = df_raw[inside_cols_actual].std(axis=1)

outside_temp_keys = [s['col_key'] for s in OUTSIDE_SENSORS.values()
                     if s['col_key'] in df_raw.columns and s.get('unit') == '°C']
if outside_temp_keys:
    df_raw['avg_outside_T'] = df_raw[outside_temp_keys].mean(axis=1)

# Resample
resample_map = {"1分鐘":"1min","5分鐘":"5min","15分鐘":"15min","30分鐘":"30min","1小時":"1h"}
rs = resample_map[resample_opt]
df = df_raw.set_index('時間').resample(rs).mean(numeric_only=True).reset_index()

# ─────────────────────────────────────────────
# Date / files banner
# ─────────────────────────────────────────────
date_start = df['時間'].min()
date_end   = df['時間'].max()
days_span  = (date_end - date_start).total_seconds() / 86400 + 1

c_info1, c_info2 = st.columns([3, 2])
with c_info1:
    st.markdown(f"""<div style='color:#3a7fa0; font-size:0.82rem; padding:6px 0;'>
        📅 <b style='color:#4fc3f7;'>{len(uploaded_files)}</b> 個檔案 ｜ 
        <b style='color:#4fc3f7;'>{date_start.strftime('%Y-%m-%d')}</b> 
        → <b style='color:#4fc3f7;'>{date_end.strftime('%Y-%m-%d')}</b> 
        ｜ 涵蓋 <b style='color:#4fc3f7;'>{days_span:.1f}</b> 天 
        ｜ 抽樣後 <b style='color:#4fc3f7;'>{len(df):,}</b> 筆（{resample_opt}）
    </div>""", unsafe_allow_html=True)
with c_info2:
    chips = "".join(f'<span class="file-chip">📄 {f.name}</span>' for f in uploaded_files[:5])
    if len(uploaded_files) > 5:
        chips += f'<span class="file-chip">+{len(uploaded_files)-5}</span>'
    st.markdown(f"<div style='text-align:right; padding:4px 0;'>{chips}</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Time Range Slider (MM/DD HH:mm format)
# ─────────────────────────────────────────────
t_min = df['時間'].min().to_pydatetime()
t_max = df['時間'].max().to_pydatetime()

col_sl, col_sl_lbl = st.columns([5, 1])
with col_sl:
    time_range = st.slider(
        "⏱️ 時間範圍",
        min_value=t_min, max_value=t_max,
        value=(t_min, t_max),
        format="MM/DD HH:mm",
        label_visibility="collapsed"
    )
with col_sl_lbl:
    st.markdown(f"<div style='padding-top:8px; font-size:0.75rem; color:#3a7fa0; line-height:1.5;'>"
                f"{time_range[0].strftime('%m/%d %H:%M')}<br>→ {time_range[1].strftime('%m/%d %H:%M')}</div>",
                unsafe_allow_html=True)

dff = df[(df['時間'] >= time_range[0]) & (df['時間'] <= time_range[1])]
if len(dff) == 0:
    st.error("選取時間範圍內無資料，請調整滑桿。")
    st.stop()

latest      = dff.iloc[-1]
inside_cols = [s['col_key'] for s in INSIDE_SENSORS.values() if s['col_key'] in dff.columns]
inside_vals = [latest[c] for c in inside_cols]

avg_T  = np.mean(inside_vals)
max_T  = np.max(inside_vals)
min_T  = np.min(inside_vals)
unif   = np.std(inside_vals)
comp_T = latest.get('CH101(一號壓縮機)', np.nan)
humid  = latest.get('CH105(通道 105)',   np.nan)
amb_T  = latest.get('CH106(關鍵數據 (CH106))', np.nan)

if avg_T > alarm_high:
    alarm_status = 'err'
elif avg_T > alarm_high - 2 or avg_T < alarm_low:
    alarm_status = 'warn'
else:
    alarm_status = 'ok'

# ─────────────────────────────────────────────
# KPI Row (latest snapshot of selected range)
# ─────────────────────────────────────────────
st.markdown('<div class="section-title">📊 即時關鍵指標（區間最後時刻）</div>', unsafe_allow_html=True)

kpi_color_map = {'err':"#ef5350",'warn':"#ffb300",'ok':"#4fc3f7"}
badge_map = {
    'ok':'<span class="badge-ok">✅ 正常</span>',
    'warn':'<span class="badge-warn">⚠️ 注意</span>',
    'err':'<span class="badge-err">🚨 異常</span>',
}

kpi_cols = st.columns(7)
kpis = [
    ("庫內平均溫", f"{avg_T:.1f}", "°C", badge_map[alarm_status], kpi_color_map[alarm_status]),
    ("庫內最高溫", f"{max_T:.1f}", "°C", f"min {min_T:.1f}°C", "#ef5350"),
    ("溫度均勻度", f"±{unif:.2f}", "°C", "σ 標準差", "#ffd54f"),
    ("壓縮機溫度", f"{comp_T:.1f}" if not np.isnan(comp_T) else "N/A", "°C", "CH101", "#ff8a65"),
    ("環境溫度", f"{amb_T:.1f}" if not np.isnan(amb_T) else "N/A", "°C", "CH106", "#a5d6a7"),
    ("環境濕度", f"{humid:.1f}" if not np.isnan(humid) else "N/A", "%RH", "CH105", "#80deea"),
    ("區間點數", f"{len(dff):,}", "筆", resample_opt, "#90a4ae"),
]
for kcol, (lbl, val, unit, delta, color) in zip(kpi_cols, kpis):
    kcol.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{lbl}</div>
        <div class="kpi-value" style="color:{color};">{val}</div>
        <div class="kpi-unit">{unit}</div>
        <div class="kpi-delta">{delta}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Main Layout: 3D + Charts
# ─────────────────────────────────────────────
col_left, col_right = st.columns([1, 2])

with col_left:
    st.markdown("""
    <div style='background:linear-gradient(90deg,#071525,#0a1e32); border:1px solid #0e3a5c;
         border-radius:8px; padding:7px 12px; margin-bottom:8px; font-size:0.78rem; color:#5a9ab8; text-align:center;'>
        🔬 <b style='color:#4fc3f7'>GM10</b> &nbsp;|&nbsp;
        <span style='color:#42a5f5'>Module 1 庫內</span> CH1-CH8 &nbsp;+&nbsp;
        <span style='color:#ffa726'>Module 2 庫外</span> CH101-CH106
    </div>
    """, unsafe_allow_html=True)

    mod_tab1, mod_tab2 = st.tabs(["❄️ 庫內 3D 分布", "🌡️ 庫外感測器"])

    with mod_tab1:
        latest_time_str = dff['時間'].iloc[-1].strftime('%m/%d %H:%M:%S')
        st.markdown(
            f"<div class='section-title'>Module 1 — 8 點溫度 3D 分布"
            f"<span style='font-weight:400; color:#2a6a8a; font-size:0.75rem; margin-left:10px;'>"
            f"快照：<b style='color:#4fc3f7'>{latest_time_str}</b></span></div>",
            unsafe_allow_html=True)

        fig_floor = go.Figure()
        corners = {'A':(0,0,1),'B':(1,0,1),'C':(0,0,0),'D':(1,0,0),
                   'E':(0,1,1),'F':(1,1,1),'G':(0,1,0),'H':(1,1,0)}
        edges = [('A','B'),('A','C'),('B','D'),('C','D'),
                 ('E','F'),('E','G'),('F','H'),('G','H'),
                 ('A','E'),('B','F'),('C','G'),('D','H')]
        hidden = {('C','G'),('D','H'),('E','G'),('G','H')}

        def add_edge(p1, p2, dashed=False):
            x0,y0,z0 = corners[p1]; x1,y1,z1 = corners[p2]
            fig_floor.add_trace(go.Scatter3d(
                x=[x0,x1,None], y=[y0,y1,None], z=[z0,z1,None],
                mode='lines',
                line=dict(color='#1565c0' if not dashed else 'rgba(21,101,192,0.35)',
                          width=4 if not dashed else 2,
                          dash='dash' if dashed else 'solid'),
                showlegend=False, hoverinfo='skip'
            ))
        for p1, p2 in edges:
            add_edge(p1, p2, dashed=(p1,p2) in hidden or (p2,p1) in hidden)

        vals = [latest[s['col_key']] for s in INSIDE_SENSORS.values() if s['col_key'] in latest.index]
        vmin_t = min(vals) - 1; vmax_t = max(vals) + 1
        xs, ys, zs, colors_3d, texts, hovers = [], [], [], [], [], []
        for name, s in INSIDE_SENSORS.items():
            if s['col_key'] not in latest.index: continue
            x,y,z = s['pos']
            val = latest[s['col_key']]
            ratio = (val - vmin_t) / max(vmax_t - vmin_t, 0.1)
            r = int(20+180*ratio); g = int(100+120*ratio); b = int(220+30*ratio)
            xs.append(x); ys.append(y); zs.append(z)
            colors_3d.append(f'rgb({r},{g},{b})')
            texts.append(f"{val:.1f}°C")
            hovers.append(f"<b>{name}</b><br>{s['label']}<br>溫度: {val:.2f}°C")

        fig_floor.add_trace(go.Scatter3d(
            x=xs, y=ys, z=zs, mode='markers+text',
            marker=dict(size=18, color=colors_3d, opacity=0.92,
                        line=dict(color='white', width=1.5)),
            text=texts, textposition='top center',
            textfont=dict(size=11, color='white'),
            hovertext=hovers, hoverinfo='text', showlegend=False
        ))
        fig_floor.update_layout(
            scene=dict(
                xaxis=dict(title='左→右', tickvals=[0,1], ticktext=['左','右'],
                           gridcolor='#0e3a5c', backgroundcolor='rgba(5,13,26,0.5)',
                           tickfont=dict(color='#4a8aa8')),
                yaxis=dict(title='前→後', tickvals=[0,1], ticktext=['前','後'],
                           gridcolor='#0e3a5c', backgroundcolor='rgba(5,13,26,0.5)',
                           tickfont=dict(color='#4a8aa8')),
                zaxis=dict(title='下→上', tickvals=[0,1], ticktext=['下','上'],
                           gridcolor='#0e3a5c', backgroundcolor='rgba(5,13,26,0.5)',
                           tickfont=dict(color='#4a8aa8')),
                bgcolor='rgba(5,13,26,0.8)',
            ),
            scene_camera=dict(eye=dict(x=1.5, y=-1.5, z=1.2)),
            margin=dict(l=0, r=0, t=10, b=0), height=380,
            paper_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_floor, use_container_width=True)

        st.markdown('<div class="section-title">各通道即時值</div>', unsafe_allow_html=True)
        sensor_items = list(INSIDE_SENSORS.items())
        for row_start in range(0, len(sensor_items), 4):
            row_cols = st.columns(4)
            for col_idx, (name, s) in enumerate(sensor_items[row_start:row_start+4]):
                if s['col_key'] not in latest.index: continue
                v = latest[s['col_key']]
                color = "#ef5350" if v > alarm_high else ("#ffb300" if v < alarm_low else "#4fc3f7")
                row_cols[col_idx].markdown(f"""
                <div class="kpi-card" style="padding:8px 10px;">
                    <div class="kpi-label">{name}</div>
                    <div class="kpi-value" style="font-size:1.2rem; color:{color};">{v:.1f}°C</div>
                    <div class="kpi-unit" style="font-size:0.68rem;">{s['label'].split(' ',1)[1]}</div>
                </div>""", unsafe_allow_html=True)

    with mod_tab2:
        st.markdown('<div class="section-title">Module 2 — 庫外感測器即時值</div>', unsafe_allow_html=True)
        out_items = list(OUTSIDE_SENSORS.items())
        for row_start in range(0, len(out_items), 3):
            row_cols = st.columns(3)
            for ci, (name, s) in enumerate(out_items[row_start:row_start+3]):
                if s['col_key'] not in latest.index: continue
                v = latest[s['col_key']]
                unit = s['unit']
                color = "#ff8a65" if name == 'CH101' and v > 40 else ("#80deea" if unit == '%RH' else "#a5d6a7")
                row_cols[ci].markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">{s['label']}</div>
                    <div class="kpi-value" style="color:{color};">{v:.1f}</div>
                    <div class="kpi-unit">{unit}</div>
                </div>""", unsafe_allow_html=True)

with col_right:
    tab_t, tab_out, tab_stat = st.tabs(["🌡️ 庫內溫度", "🏭 庫外環境", "📈 統計分析"])

    with tab_t:
        st.markdown('<div class="section-title">庫內 8 點溫度時序</div>', unsafe_allow_html=True)
        fig_inside = go.Figure()
        if show_raw:
            for i, (name, s) in enumerate(INSIDE_SENSORS.items()):
                if s['col_key'] not in dff.columns: continue
                fig_inside.add_trace(go.Scatter(
                    x=dff['時間'], y=dff[s['col_key']],
                    name=s['label'], mode='lines',
                    line=dict(width=1.5, color=INSIDE_COLORS[i]),
                    hovertemplate=f"{s['label']}: %{{y:.2f}}°C<extra></extra>"
                ))
        if 'avg_inside_T' in dff.columns:
            fig_inside.add_trace(go.Scatter(
                x=dff['時間'], y=dff['avg_inside_T'],
                name='庫內平均', mode='lines',
                line=dict(width=3, color='white', dash='dot'),
                hovertemplate="平均: %{y:.2f}°C<extra></extra>"
            ))
        fig_inside.add_hline(y=alarm_high, line=dict(color="#ef5350", width=1.5, dash="dash"),
                              annotation_text=f"上限 {alarm_high}°C",
                              annotation_font=dict(color="#ef5350", size=10))
        fig_inside.add_hline(y=alarm_low, line=dict(color="#42a5f5", width=1.5, dash="dash"),
                              annotation_text=f"下限 {alarm_low}°C",
                              annotation_font=dict(color="#42a5f5", size=10))
        fig_inside = style_fig(fig_inside, height=360)
        fig_inside.update_yaxes(title_text="溫度 (°C)")
        st.plotly_chart(fig_inside, use_container_width=True)

    with tab_out:
        st.markdown('<div class="section-title">庫外溫度 & 濕度時序</div>', unsafe_allow_html=True)
        fig_out = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                subplot_titles=["庫外溫度 (°C)","濕度 (%RH)"],
                                vertical_spacing=0.1)
        out_temp_sensors = ['CH101(一號壓縮機)','CH102(通道 102)','CH103(通道 103)',
                            'CH104(通道 104)','CH106(關鍵數據 (CH106))']
        out_temp_labels = ['CH101 壓縮機','CH102 左T','CH103 前T','CH104 上T','CH106 前T(溫溼)']
        for col_, lbl, color in zip(out_temp_sensors, out_temp_labels, OUT_T_COLORS):
            if col_ not in dff.columns: continue
            fig_out.add_trace(go.Scatter(
                x=dff['時間'], y=dff[col_], name=lbl,
                line=dict(width=2, color=color),
                hovertemplate=f"{lbl}: %{{y:.2f}}°C<extra></extra>"
            ), row=1, col=1)
        hum_col = 'CH105(通道 105)'
        if hum_col in dff.columns:
            fig_out.add_trace(go.Scatter(
                x=dff['時間'], y=dff[hum_col],
                name='CH105 濕度', fill='tozeroy',
                line=dict(width=2, color='#4fc3f7'),
                fillcolor='rgba(79,195,247,0.1)',
                hovertemplate="濕度: %{y:.1f}%RH<extra></extra>"
            ), row=2, col=1)
        fig_out = style_fig(fig_out, height=380)
        for ann in fig_out.layout.annotations:
            ann.font.color = "#3a7fa0"; ann.font.size = 10
        st.plotly_chart(fig_out, use_container_width=True)

    with tab_stat:
        if not show_stats:
            st.info("請在左側勾選「顯示統計分析」")
        else:
            st.markdown('<div class="section-title">統計分析</div>', unsafe_allow_html=True)
            fig_stat = make_subplots(
                rows=2, cols=2,
                subplot_titles=["溫度均勻度 σ (°C)","Max-Min 溫差 (°C)",
                                "庫內平均溫分布","各通道平均溫"],
                vertical_spacing=0.16, horizontal_spacing=0.1
            )
            if 'uniformity' in dff.columns:
                fig_stat.add_trace(go.Scatter(
                    x=dff['時間'], y=dff['uniformity'],
                    fill='tozeroy', line=dict(color='#4fc3f7', width=1.5),
                    fillcolor='rgba(79,195,247,0.1)', name='σ',
                    hovertemplate="σ: %{y:.3f}°C<extra></extra>"
                ), row=1, col=1)
            if 'max_inside_T' in dff.columns and 'min_inside_T' in dff.columns:
                span = dff['max_inside_T'] - dff['min_inside_T']
                fig_stat.add_trace(go.Scatter(
                    x=dff['時間'], y=span,
                    fill='tozeroy', line=dict(color='#ffa726', width=1.5),
                    fillcolor='rgba(255,167,38,0.1)', name='溫差',
                    hovertemplate="差: %{y:.2f}°C<extra></extra>"
                ), row=1, col=2)
            if 'avg_inside_T' in dff.columns:
                fig_stat.add_trace(go.Histogram(
                    x=dff['avg_inside_T'], nbinsx=40,
                    marker_color='#4fc3f7', opacity=0.75, name='分布',
                ), row=2, col=1)
            ch_avgs = {n: dff[s['col_key']].mean() for n, s in INSIDE_SENSORS.items()
                       if s['col_key'] in dff.columns}
            bar_colors = ["#42a5f5" if v < alarm_high else "#ef5350" for v in ch_avgs.values()]
            fig_stat.add_trace(go.Bar(
                x=list(ch_avgs.keys()), y=list(ch_avgs.values()),
                marker_color=bar_colors, name='各CH平均',
                hovertemplate="%{x}: %{y:.2f}°C<extra></extra>"
            ), row=2, col=2)
            fig_stat = style_fig(fig_stat, height=420)
            fig_stat.update_layout(showlegend=False)
            for ann in fig_stat.layout.annotations:
                ann.font.color = "#3a7fa0"; ann.font.size = 10
            st.plotly_chart(fig_stat, use_container_width=True)

# ─────────────────────────────────────────────
# Heatmap + Alerts
# ─────────────────────────────────────────────
st.markdown("---")
col_hm, col_alert = st.columns([3, 1])

with col_hm:
    st.markdown('<div class="section-title">🗓️ 時間-通道 溫度熱圖</div>', unsafe_allow_html=True)
    step = max(1, len(dff) // 400)
    df_hm = dff.iloc[::step]
    hm_cols = [s['col_key'] for s in INSIDE_SENSORS.values() if s['col_key'] in df_hm.columns]
    ch_labels = [f"{n} {s['label'].split(' ',1)[1]}" for n, s in INSIDE_SENSORS.items()
                 if s['col_key'] in df_hm.columns]
    z_data = df_hm[hm_cols].T.values
    # Use MM/DD HH:mm for monthly clarity
    x_labels = df_hm['時間'].dt.strftime('%m/%d %H:%M')
    fig_hm = go.Figure(go.Heatmap(
        z=z_data, x=x_labels, y=ch_labels,
        colorscale=[[0,'#03174a'],[0.35,'#0d47a1'],[0.7,'#1e88e5'],[1,'#b3e5fc']],
        hoverongaps=False,
        colorbar=dict(title=dict(text="°C", font=dict(color='#4fc3f7')),
                      tickfont=dict(color='#3a7fa0'), thickness=10),
        hovertemplate="%{y}<br>時間: %{x}<br>溫度: %{z:.2f}°C<extra></extra>"
    ))
    fig_hm.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(5,13,26,0.95)',
        height=270, margin=dict(l=8, r=50, t=8, b=8),
        xaxis=dict(tickfont=dict(size=9, color='#3a7fa0'), nticks=14),
        yaxis=dict(tickfont=dict(size=9, color='#3a7fa0')),
    )
    st.plotly_chart(fig_hm, use_container_width=True)

with col_alert:
    st.markdown('<div class="section-title">🚨 警報診斷</div>', unsafe_allow_html=True)
    alerts = []
    for name, s in INSIDE_SENSORS.items():
        if s['col_key'] not in latest.index: continue
        v = latest[s['col_key']]
        if v > alarm_high: alerts.append(('err', f"{name} 超上限: {v:.1f}°C"))
        elif v < alarm_low: alerts.append(('warn', f"{name} 低於下限: {v:.1f}°C"))
    if unif > 1.5: alerts.append(('warn', f"均勻性差: σ={unif:.2f}°C"))
    if not np.isnan(humid):
        if humid > 90: alerts.append(('err', f"濕度過高: {humid:.1f}%RH"))
        elif humid < 60: alerts.append(('warn', f"濕度偏低: {humid:.1f}%RH"))
    if not np.isnan(comp_T):
        if comp_T > 40: alerts.append(('err', f"壓縮機溫高: {comp_T:.1f}°C"))
        elif comp_T > 35: alerts.append(('warn', f"壓縮機偏高: {comp_T:.1f}°C"))

    if not alerts:
        st.markdown("<div class='badge-ok' style='padding:8px 12px; font-size:0.85rem;'>✅ 系統運作正常<br>無警報</div>", unsafe_allow_html=True)
    else:
        for level, msg in alerts:
            css_cls = 'alert-box' if level == 'err' else 'warn-box'
            icon = '🚨' if level == 'err' else '⚠️'
            st.markdown(f"<div class='{css_cls}'>{icon} {msg}</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    avg_humid_str = f"{dff['CH105(通道 105)'].mean():.1f}%RH" if 'CH105(通道 105)' in dff.columns else "N/A"
    st.markdown(f"""
    <div class="kpi-card" style="text-align:left;">
        <div class="kpi-label">區間統計摘要</div>
        <div style="font-size:0.8rem; color:#4a8aa8; line-height:2.0;">
        📊 點數: <b>{len(dff):,}</b><br>
        🌡️ 區間均溫: <b>{dff['avg_inside_T'].mean():.2f}°C</b><br>
        🔺 最高溫: <b>{dff['max_inside_T'].max():.2f}°C</b><br>
        🔻 最低溫: <b>{dff['min_inside_T'].min():.2f}°C</b><br>
        📐 均勻度σ: <b>{dff['uniformity'].mean():.3f}°C</b><br>
        💧 平均濕度: <b>{avg_humid_str}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# NEW: Daily Summary
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(f'<div class="section-title">📅 日別統計摘要（共 {int(days_span)} 天）</div>', unsafe_allow_html=True)

agg_dict = {}
if 'avg_inside_T' in dff.columns: agg_dict['avg_inside_T'] = 'mean'
if 'max_inside_T' in dff.columns: agg_dict['max_inside_T'] = 'max'
if 'min_inside_T' in dff.columns: agg_dict['min_inside_T'] = 'min'
if 'uniformity'   in dff.columns: agg_dict['uniformity']   = 'mean'
if 'CH101(一號壓縮機)' in dff.columns: agg_dict['CH101(一號壓縮機)'] = 'mean'
if 'CH105(通道 105)'   in dff.columns: agg_dict['CH105(通道 105)']   = 'mean'

daily = dff.set_index('時間').resample('D').agg(agg_dict).reset_index()
rename_daily = {
    '時間':'日期',
    'avg_inside_T':'庫內平均(°C)',
    'max_inside_T':'最高溫(°C)',
    'min_inside_T':'最低溫(°C)',
    'uniformity':'均勻度σ',
    'CH101(一號壓縮機)':'壓縮機(°C)',
    'CH105(通道 105)':'濕度(%RH)',
}
daily = daily.rename(columns=rename_daily)
daily['日期'] = daily['日期'].dt.strftime('%Y-%m-%d')
for c in ['庫內平均(°C)','最高溫(°C)','最低溫(°C)','壓縮機(°C)']:
    if c in daily.columns: daily[c] = daily[c].round(2)
if '均勻度σ' in daily.columns: daily['均勻度σ'] = daily['均勻度σ'].round(3)
if '濕度(%RH)' in daily.columns: daily['濕度(%RH)'] = daily['濕度(%RH)'].round(1)
st.dataframe(daily, use_container_width=True, hide_index=True, height=min(360, 36*(len(daily)+1)+10))

# Download daily summary
csv_daily = daily.to_csv(index=False).encode('utf-8-sig')
st.download_button("⬇️ 下載日別統計 CSV", csv_daily,
                    file_name=f"GM10_daily_summary_{date_start.strftime('%Y%m%d')}_{date_end.strftime('%Y%m%d')}.csv",
                    mime="text/csv")

# ─────────────────────────────────────────────
# Raw data
# ─────────────────────────────────────────────
with st.expander("📋 原始資料表（區間最後 200 筆）& 下載"):
    display_cols = ['時間'] + [s['col_key'] for s in INSIDE_SENSORS.values() if s['col_key'] in dff.columns] + \
                  [s['col_key'] for s in OUTSIDE_SENSORS.values() if s['col_key'] in dff.columns]
    rename_map = {'時間':'時間'}
    rename_map.update({s['col_key']: f"{n} {s['label'].split(' ',1)[1]}"
                       for n, s in INSIDE_SENSORS.items() if s['col_key'] in dff.columns})
    rename_map.update({s['col_key']: s['label'] for s in OUTSIDE_SENSORS.values() if s['col_key'] in dff.columns})
    df_show = dff[display_cols].rename(columns=rename_map).tail(200)
    st.dataframe(df_show, hide_index=True, use_container_width=True, height=280)

    csv_bytes = dff[display_cols].to_csv(index=False).encode('utf-8-sig')
    st.download_button("⬇️ 下載篩選後完整資料 (CSV)", csv_bytes,
                        file_name=f"GM10_filtered_{time_range[0].strftime('%Y%m%d')}_{time_range[1].strftime('%Y%m%d')}.csv",
                        mime="text/csv", use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align:center; color:#1a4a6a; font-size:0.76rem;'>
    ❄️ 商錄冷庫 GM10 數位雙生系統 - 月份分析版 ｜ ITRI 綠能所 智慧控制設備研究室 ｜ GB+44015-2026
</div>
""", unsafe_allow_html=True)
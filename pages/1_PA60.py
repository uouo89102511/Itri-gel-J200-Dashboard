"""
PA60 互動式電力數據分析工具 - 優化版
ItriGel J200 PA60 | ITRI 綠能所 智慧控制設備研究室
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

# ─────────────────────────────────────────────
# Page Style
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f1117 0%, #1a1f2e 100%); color: #e8eaf6; }
    .main .block-container { padding: 1.2rem 2rem 2rem 2rem; }

    .page-header {
        background: linear-gradient(90deg, #1a1f2e, #1e2a3a);
        border: 1px solid #2a3a4a;
        border-left: 4px solid #f5a623;
        border-radius: 8px;
        padding: 14px 20px;
        margin-bottom: 1.2rem;
        display: flex; align-items: center; gap: 14px;
    }
    .page-header-icon { font-size: 2rem; }
    .page-header-title { font-size: 1.4rem; font-weight: 700; color: #f5a623; line-height: 1.2; }
    .page-header-sub { font-size: 0.8rem; color: #6a8aa0; }

    .kpi-card {
        background: linear-gradient(145deg, #1a1f2e, #1e2640);
        border: 1px solid #2a3a4a;
        border-radius: 10px;
        padding: 14px 16px;
        text-align: center;
        height: 100%;
    }
    .kpi-label { font-size: 0.7rem; color: #4a6a84; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 4px; }
    .kpi-value { font-size: 1.5rem; font-weight: 700; line-height: 1.1; }
    .kpi-unit  { font-size: 0.78rem; color: #4a6a84; }

    .section-label {
        font-size: 0.75rem; font-weight: 600; color: #f5a623;
        text-transform: uppercase; letter-spacing: 0.12em;
        margin: 14px 0 6px 0; padding-bottom: 3px;
        border-bottom: 1px solid #2a3a4a;
    }

    .upload-prompt {
        background: linear-gradient(145deg, #1a1f2e, #1e2640);
        border: 2px dashed #2a3a4a;
        border-radius: 12px;
        padding: 40px 24px;
        text-align: center;
        margin-top: 1rem;
    }

    .file-chip {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(245,166,35,0.1); border: 1px solid rgba(245,166,35,0.3);
        border-radius: 20px; padding: 3px 10px;
        font-size: 0.78rem; color: #f5a623; margin: 2px;
    }

    section[data-testid="stSidebar"] {
        background: #12161f;
        border-right: 1px solid #2a3a4a;
    }
    section[data-testid="stSidebar"] label { color: #8aa4b8 !important; font-size: 0.82rem !important; }

    .js-plotly-plot { border-radius: 10px; overflow: hidden; }

    .stTabs [data-baseweb="tab-list"] { background: transparent; border-bottom: 1px solid #2a3a4a; }
    .stTabs [data-baseweb="tab"] { color: #6a8aa0; font-size: 0.9rem; }
    .stTabs [aria-selected="true"] { color: #f5a623 !important; border-bottom: 2px solid #f5a623 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <span class="page-header-icon">⚡</span>
    <div>
        <div class="page-header-title">PA60 電力數據分析工具</div>
        <div class="page-header-sub">ItriGel J200 PA60 ｜ 多日比對 ｜ kWh 積分 ｜ 梯形積分法</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar author badge
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 10px 0 6px 0;">
        <a href="https://github.com/YORROY123" target="_blank">
            <img src="https://avatars.githubusercontent.com/YORROY123"
                 width="60" style="border-radius:50%; border:2px solid #f5a623;"/>
        </a><br/>
        <a href="https://github.com/YORROY123" target="_blank"
           style="color:#f5a623; font-weight:bold; text-decoration:none; font-size:13px;">
            YORROY123
        </a>
        <p style="color:#4a6a84; font-size:10px; margin:2px 0 0 0;">Made by YORROY123</p>
    </div>
    <hr style="border-color:#2a3a4a; margin: 8px 0;"/>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data(file_bytes, file_name):
    df = pd.read_csv(io.BytesIO(file_bytes))
    if '時間' in df.columns:
        df['時間'] = pd.to_datetime(df['時間'])
        df.set_index('時間', inplace=True)
    return df

@st.cache_data(show_spinner=False)
def compute_derived_columns(df_in):
    df = df_in.copy()
    warn_msgs = []

    derived = {
        "L1_kW_total (冷庫總電)":   (["L1_kW_a","L1_kW_b","L1_kW_c"], lambda d: d["L1_kW_a"]+d["L1_kW_b"]+d["L1_kW_c"]),
        "L2_kW_total (壓縮機總電)": (["L2_kW_a","L2_kW_b","L2_kW_c"], lambda d: d["L2_kW_a"]+d["L2_kW_b"]+d["L2_kW_c"]),
        "L3_kW_total (除霜電熱)":   (["L3_kW_a","L3_kW_b","L3_kW_c"], lambda d: d["L3_kW_a"]+d["L3_kW_b"]+d["L3_kW_c"]),
        "L4_除霧電熱": (["L4_V_ab","L4_I_a"], lambda d: d["L4_V_ab"]*d["L4_I_a"]*1.0),
        "L4_冷凝風扇": (["L4_V_bc","L4_I_b"], lambda d: d["L4_V_bc"]*d["L4_I_b"]*0.83),
        "L4_蒸發風扇": (["L4_V_ab","L4_I_c"], lambda d: d["L4_V_ab"]*d["L4_I_c"]*1.0),
    }
    for new_col, (req, formula) in derived.items():
        if all(c in df.columns for c in req):
            num = {c: pd.to_numeric(df[c], errors='coerce') for c in req}
            df[new_col] = formula(num)
        else:
            miss = [c for c in req if c not in df.columns]
            warn_msgs.append(f"無法計算 `{new_col}`，缺少：{miss}")

    for col in ["L4_除霧電熱","L4_冷凝風扇","L4_蒸發風扇"]:
        if col in df.columns:
            df[col] = df[col] * 0.001

    comp_cols = {
        "壓縮機": "L2_kW_total (壓縮機總電)",
        "除霜":   "L3_kW_total (除霜電熱)",
        "除霧":   "L4_除霧電熱",
        "冷凝":   "L4_冷凝風扇",
        "蒸發":   "L4_蒸發風扇",
    }
    if all(v in df.columns for v in comp_cols.values()):
        df["驗算用的冷庫總電 (kW)"] = sum(df[c] for c in comp_cols.values())
    else:
        miss = [v for v in comp_cols.values() if v not in df.columns]
        warn_msgs.append(f"無法計算驗算總電，缺少：{miss}")

    tc = "L1_kW_total (冷庫總電)"
    vc = "驗算用的冷庫總電 (kW)"
    if tc in df.columns and vc in df.columns:
        df["總電誤差 (%)"]      = (df[tc] - df[vc]) / df[tc] * 100
        df["冷庫總電差值 (kW)"] = df[tc] - df[vc]

    kwh_targets = {
        "L1_kW_total (冷庫總電)":    "冷庫總電 累積 (kWh)",
        "驗算用的冷庫總電 (kW)":      "驗算冷庫總電 累積 (kWh)",
        "L2_kW_total (壓縮機總電)":  "壓縮機 累積 (kWh)",
        "L3_kW_total (除霜電熱)":    "除霜電熱 累積 (kWh)",
        "L4_除霧電熱":               "除霧耗電 累積 (kWh)",
        "L4_冷凝風扇":               "冷凝風扇耗電 累積 (kWh)",
        "L4_蒸發風扇":               "蒸發風扇耗電 累積 (kWh)",
    }
    t_hours = df.index.astype(np.int64) / 1e9 / 3600
    for src, nc in kwh_targets.items():
        if src in df.columns:
            power = pd.to_numeric(df[src], errors='coerce').fillna(0).values
            dt    = np.diff(t_hours.values)
            avg_p = (power[:-1] + power[1:]) / 2
            df[nc] = np.concatenate([[0], np.cumsum(avg_p * dt)])

    return df, warn_msgs

def calc_kwh_in_range(df_src, col, t0, t1):
    if col not in df_src.columns:
        return 0.0
    df_copy = df_src[[col]].copy()
    if df_copy.index.tz is not None:
        df_copy.index = df_copy.index.tz_localize(None)
    df_copy = df_copy.loc[t0:t1]
    s = pd.to_numeric(df_copy[col], errors='coerce').dropna()
    if len(s) < 2:
        return 0.0
    t_hr = s.index.astype(np.int64) / 1e9 / 3600
    return float(np.sum((s.values[:-1] + s.values[1:]) / 2 * np.diff(t_hr.values)))

# ─────────────────────────────────────────────
# Plot theme helper
# ─────────────────────────────────────────────
PLOT_COLORS = [
    "#f5a623","#4fc3f7","#66bb6a","#ef5350","#ab47bc",
    "#26c6da","#ffd54f","#8d6e63","#78909c","#ec407a",
]

def style_fig(fig, height=500, legend_bottom=False):
    legend_cfg = dict(
        font=dict(color="#8aa4b8", size=11),
        bgcolor="rgba(0,0,0,0)",
        bordercolor="#2a3a4a", borderwidth=1,
    )
    if legend_bottom:
        legend_cfg.update(orientation="h", y=-0.12)
    fig.update_layout(
        plot_bgcolor="rgba(20,26,40,0.95)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=height,
        hovermode="x unified",
        dragmode="zoom",
        legend=legend_cfg,
        margin=dict(l=8, r=8, t=30, b=8),
        font=dict(color="#8aa4b8"),
    )
    fig.update_xaxes(
        gridcolor="rgba(42,58,74,0.8)",
        zerolinecolor="rgba(42,58,74,0.8)",
        tickfont=dict(color="#6a8aa0"),
        title_font=dict(color="#6a8aa0"),
        showspikes=True, spikecolor="#f5a623",
        spikethickness=1, spikedash="dot",
    )
    fig.update_yaxes(
        gridcolor="rgba(42,58,74,0.6)",
        zerolinecolor="rgba(42,58,74,0.6)",
        tickfont=dict(color="#6a8aa0"),
    )
    return fig

# ─────────────────────────────────────────────
# Preset Management
# ─────────────────────────────────────────────
if "pa60_presets" not in st.session_state:
    st.session_state.pa60_presets = {"樣式 1": [], "樣式 2": [], "樣式 3": []}

# ─────────────────────────────────────────────
# File Upload
# ─────────────────────────────────────────────
uploaded_files = st.file_uploader(
    "📂 上傳 PA60 CSV 資料（可多選，支援多日比對）",
    type="csv",
    accept_multiple_files=True,
    help="可同時上傳多天的 CSV，系統會自動對齊時間軸進行比對"
)

if not uploaded_files:
    st.markdown("""
    <div class="upload-prompt">
        <div style="font-size:3rem; margin-bottom:12px;">⚡</div>
        <div style="font-size:1.1rem; font-weight:600; color:#f5a623; margin-bottom:6px;">請上傳 PA60 CSV 資料檔</div>
        <div style="font-size:0.85rem; color:#4a6a84;">支援多檔同時上傳 · 自動計算衍生欄位 · 梯形積分 kWh</div>
        <div style="margin-top:16px; font-size:0.78rem; color:#3a5a6a;">
            必要欄位：時間 / L1~L4 各相電壓電流
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────
# Load & Process
# ─────────────────────────────────────────────
file_dict = {f.name: f for f in uploaded_files}

with st.sidebar:
    st.markdown('<div class="section-label" style="color:#f5a623;">📁 檔案選擇</div>', unsafe_allow_html=True)
    selected_files = st.multiselect(
        "選擇要分析的檔案",
        list(file_dict.keys()),
        default=list(file_dict.keys()),
        help="可選多天進行比對"
    )

if not selected_files:
    st.info("👈 請在左側選擇至少一個檔案進行分析。")
    st.stop()

dfs         = {}
all_warns   = {}
all_columns = []
min_time    = pd.Timestamp.max
max_time    = pd.Timestamp.min

progress_bar = st.progress(0, text="載入資料中…")
for i, fname in enumerate(selected_files):
    f = file_dict[fname]
    raw_bytes = f.read()
    df = load_data(raw_bytes, fname)
    df, warns = compute_derived_columns(df)
    dfs[fname]       = df
    all_warns[fname] = warns
    for col in df.columns:
        all_columns.append(f"{fname} - {col}")
    if df.index.min() < min_time: min_time = df.index.min()
    if df.index.max() > max_time: max_time = df.index.max()
    progress_bar.progress((i+1)/len(selected_files), text=f"已載入 {fname}")
progress_bar.empty()

all_warn_flat = [(f, w) for f, ws in all_warns.items() for w in ws]
if all_warn_flat:
    with st.expander(f"⚠️ 衍生欄位計算警告（{len(all_warn_flat)} 項）", expanded=False):
        for fname, w in all_warn_flat:
            st.caption(f"**{fname}**：{w}")

chips_html = "".join(f'<span class="file-chip">📄 {f}</span>' for f in selected_files)
st.markdown(f'<div style="margin-bottom:0.8rem;">{chips_html}</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar Controls
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-label" style="color:#f5a623;">💾 欄位樣式</div>', unsafe_allow_html=True)
    preset_slot = st.radio("preset", ["樣式 1","樣式 2","樣式 3"],
                            horizontal=True, label_visibility="collapsed")
    pc1, pc2 = st.columns(2)
    if pc1.button("📥 載入", use_container_width=True, key="pa60_load_preset"):
        saved = st.session_state.pa60_presets.get(preset_slot, [])
        matched = [c for c in all_columns if c.split(" - ",1)[1] in saved]
        st.session_state.pa60_selected_cols = matched
        st.rerun()
    if pc2.button("💾 儲存", use_container_width=True, key="pa60_save_preset"):
        curr = st.session_state.get("pa60_selected_cols", [])
        pure = list({c.split(" - ",1)[1] for c in curr})
        st.session_state.pa60_presets[preset_slot] = pure
        st.sidebar.success(f"✅ 已儲存至 {preset_slot}")

    st.markdown('<div class="section-label" style="color:#f5a623; margin-top:14px;">⚙️ 圖表設定</div>', unsafe_allow_html=True)

    resample_rule = st.selectbox(
        "資料抽樣頻率",
        ["每 1 分鐘（推薦）","每 5 分鐘","每 10 分鐘","原始資料"],
        index=0
    )
    rule_map = {"原始資料": None, "每 1 分鐘（推薦）": "1min",
                "每 5 分鐘": "5min", "每 10 分鐘": "10min"}
    freq = rule_map[resample_rule]

    selected_options = st.multiselect(
        "選擇比對欄位",
        all_columns,
        key="pa60_selected_cols",
        help="可跨檔案選擇同名欄位進行多天比對"
    )

    plot_mode = st.radio(
        "顯示模式",
        ["分開顯示（子圖）","合併顯示（同一圖）"],
        horizontal=False
    )

    st.markdown('<div class="section-label" style="color:#f5a623; margin-top:14px;">📏 座標軸</div>', unsafe_allow_html=True)

    min_dt = min_time.to_pydatetime().replace(microsecond=0)
    max_dt = max_time.to_pydatetime().replace(microsecond=0)
    selected_time = st.slider(
        "X 軸時間範圍",
        min_value=min_dt, max_value=max_dt,
        value=(min_dt, max_dt)
    )

    enable_y_axis = st.checkbox("手動設定 Y 軸範圍")
    y_min_val, y_max_val = 0.0, 100.0
    if enable_y_axis:
        yc1, yc2 = st.columns(2)
        y_min_val = yc1.number_input("Y 下限", value=0.0, step=10.0)
        y_max_val = yc2.number_input("Y 上限", value=100.0, step=10.0)

valid_options = [opt for opt in selected_options if opt.split(" - ",1)[0] in dfs]

# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 互動圖表", "📋 日報分析", "🗂️ 原始資料"])

# ══════════════════════════════════════════════
# Tab 1 – Interactive Chart
# ══════════════════════════════════════════════
with tab1:
    if not valid_options:
        st.info("👈 請在左側選擇欲比對的欄位。")
    else:
        n = len(valid_options)

        if plot_mode == "合併顯示（同一圖）":
            fig = go.Figure()
            for i, option in enumerate(valid_options):
                fname, col = option.split(" - ",1)
                s = pd.to_numeric(dfs[fname][col], errors='coerce')
                if freq:
                    s = s.resample(freq).mean()
                fig.add_trace(go.Scatter(
                    x=s.index, y=s, mode='lines', name=option,
                    line=dict(width=1.8, color=PLOT_COLORS[i % len(PLOT_COLORS)]),
                    hovertemplate=f"{option}: %{{y:.3f}}<extra></extra>"
                ))
            fig = style_fig(fig, height=560, legend_bottom=True)
        else:
            spacing = min(0.06, 0.85 / max(n-1, 1))
            fig = make_subplots(
                rows=n, cols=1,
                shared_xaxes=True,
                subplot_titles=valid_options,
                vertical_spacing=spacing
            )
            for i, option in enumerate(valid_options):
                fname, col = option.split(" - ",1)
                s = pd.to_numeric(dfs[fname][col], errors='coerce')
                if freq:
                    s = s.resample(freq).mean()
                fig.add_trace(go.Scatter(
                    x=s.index, y=s, mode='lines',
                    name=option,
                    line=dict(width=1.8, color=PLOT_COLORS[i % len(PLOT_COLORS)]),
                    hovertemplate="%{y:.3f}<extra></extra>",
                    showlegend=False,
                ), row=i+1, col=1)
            fig = style_fig(fig, height=max(280, 260*n), legend_bottom=False)
            for ann in fig.layout.annotations:
                ann.font.color = "#6a8aa0"
                ann.font.size  = 10

        fig.update_xaxes(range=[selected_time[0], selected_time[1]])
        if enable_y_axis:
            fig.update_yaxes(range=[y_min_val, y_max_val])

        st.plotly_chart(fig, use_container_width=True)

        # Quick stats bar
        st.markdown('<div class="section-label">📐 選取欄位統計摘要</div>', unsafe_allow_html=True)
        cols_stat = st.columns(min(n, 4))
        t0_v = pd.Timestamp(selected_time[0])
        t1_v = pd.Timestamp(selected_time[1])
        for i, option in enumerate(valid_options[:4]):
            fname, col = option.split(" - ",1)
            s = pd.to_numeric(dfs[fname][col], errors='coerce')
            s = s.loc[t0_v:t1_v].dropna()
            short = col[:22]
            cols_stat[i].markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">{short}</div>
                <div class="kpi-value" style="font-size:1.05rem; color:{PLOT_COLORS[i]};">{s.mean():.3f}</div>
                <div class="kpi-unit">avg ｜ ↑{s.max():.2f} ↓{s.min():.2f}</div>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# Tab 2 – Daily Report
# ══════════════════════════════════════════════
with tab2:
    verify_kwh_cols = ["壓縮機","除霜電熱","除霧耗電","冷凝風扇","蒸發風扇"]
    src_col_map = {
        "冷庫總電":  "L1_kW_total (冷庫總電)",
        "壓縮機":    "L2_kW_total (壓縮機總電)",
        "除霜電熱":  "L3_kW_total (除霜電熱)",
        "除霧耗電":  "L4_除霧電熱",
        "冷凝風扇":  "L4_冷凝風扇",
        "蒸發風扇":  "L4_蒸發風扇",
    }

    t_start_ts = pd.Timestamp(selected_time[0]).tz_localize(None)
    t_end_ts   = pd.Timestamp(selected_time[1]).tz_localize(None)
    duration_hrs = (t_end_ts - t_start_ts).total_seconds() / 3600
    sample_hrs = 1/60
    for fname in selected_files:
        df_f = dfs[fname]
        if len(df_f.index) >= 2:
            delta = (df_f.index[1] - df_f.index[0]).total_seconds() / 3600
            if delta > 0:
                sample_hrs = delta
            break
    total_mins = round((duration_hrs + sample_hrs) * 60)
    duration_display = f"{total_mins//60}h {total_mins%60:02d}m"

    ic1, ic2, ic3 = st.columns(3)
    ic1.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">🕐 起始時間</div>
        <div class="kpi-value" style="font-size:1rem; color:#4fc3f7;">{t_start_ts.strftime('%Y-%m-%d %H:%M')}</div>
    </div>""", unsafe_allow_html=True)
    ic2.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">🕑 結束時間</div>
        <div class="kpi-value" style="font-size:1rem; color:#4fc3f7;">{t_end_ts.strftime('%Y-%m-%d %H:%M')}</div>
    </div>""", unsafe_allow_html=True)
    ic3.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">⏱ 總時長</div>
        <div class="kpi-value" style="font-size:1.2rem; color:#f5a623;">{duration_display}</div>
    </div>""", unsafe_allow_html=True)
    st.caption("時間範圍可在左側滑桿調整，數值即時更新")
    st.markdown("---")

    all_results = {}
    for fname in selected_files:
        df_f = dfs[fname]
        row  = {lbl: calc_kwh_in_range(df_f, col, t_start_ts, t_end_ts)
                for lbl, col in src_col_map.items()}
        row["驗算總電"] = sum(row[k] for k in verify_kwh_cols)
        l1 = row["冷庫總電"]
        row["誤差(%)"] = (l1 - row["驗算總電"]) / l1 * 100 if l1 > 0 else 0.0
        all_results[fname] = row

    if len(selected_files) > 1:
        st.markdown('<div class="section-label">📊 多日比較總覽</div>', unsafe_allow_html=True)
        compare_rows = []
        for fname, row in all_results.items():
            err_icon = "🟢" if abs(row["誤差(%)"]) < 5 else ("🟡" if abs(row["誤差(%)"]) < 10 else "🔴")
            compare_rows.append({
                "檔案":           fname,
                "冷庫總電 (kWh)":  f"{row['冷庫總電']:.3f}",
                "驗算總電 (kWh)":  f"{row['驗算總電']:.3f}",
                "誤差 (%)":       f"{err_icon} {row['誤差(%)']:.2f}%",
                "壓縮機 (kWh)":   f"{row['壓縮機']:.3f}",
                "除霜 (kWh)":     f"{row['除霜電熱']:.3f}",
                "除霧 (kWh)":     f"{row['除霧耗電']:.3f}",
                "冷凝 (kWh)":     f"{row['冷凝風扇']:.3f}",
                "蒸發 (kWh)":     f"{row['蒸發風扇']:.3f}",
            })
        st.dataframe(compare_rows, use_container_width=True, hide_index=True)

        st.markdown('<div class="section-label">📊 各元件耗電多日堆疊比較</div>', unsafe_allow_html=True)
        labels_bar = list(all_results.keys())
        fig_bar = go.Figure()
        for j, comp_lbl in enumerate(verify_kwh_cols):
            fig_bar.add_trace(go.Bar(
                name=comp_lbl,
                x=labels_bar,
                y=[all_results[f][comp_lbl] for f in labels_bar],
                marker_color=PLOT_COLORS[j],
                hovertemplate=f"{comp_lbl}: %{{y:.3f}} kWh<extra></extra>"
            ))
        fig_bar = style_fig(fig_bar, height=340)
        fig_bar.update_layout(
            barmode='stack',
            legend=dict(orientation="h", y=-0.2, font=dict(color="#8aa4b8"),
                        bgcolor="rgba(0,0,0,0)")
        )
        fig_bar.update_xaxes(tickangle=-20)
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown("---")

    for fname in selected_files:
        row = all_results[fname]
        err_abs   = abs(row["誤差(%)"])
        err_color = "#66bb6a" if err_abs < 5 else ("#ffd54f" if err_abs < 10 else "#ef5350")

        st.markdown(f'<div class="section-label">📄 {fname}</div>', unsafe_allow_html=True)

        kc1, kc2, kc3, kc4 = st.columns(4)
        for kc, lbl, val, unit, color in [
            (kc1, "🔵 冷庫總電", f"{row['冷庫總電']:.3f}", "kWh", "#4fc3f7"),
            (kc2, "🟢 驗算總電", f"{row['驗算總電']:.3f}", "kWh", "#66bb6a"),
            (kc3, "🟠 量測誤差", f"{row['誤差(%)']:.2f}", "%", err_color),
            (kc4, "⏱ 時長",     duration_display,           "hh:mm", "#f5a623"),
        ]:
            kc.markdown(f"""<div class="kpi-card">
                <div class="kpi-label">{lbl}</div>
                <div class="kpi-value" style="color:{color};">{val}</div>
                <div class="kpi-unit">{unit}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col_pie, col_tbl = st.columns([1, 1])
        pie_vals   = [row[k] for k in verify_kwh_cols]
        pie_colors = PLOT_COLORS[:len(verify_kwh_cols)]

        with col_pie:
            fig_pie = go.Figure(go.Pie(
                labels=verify_kwh_cols, values=pie_vals,
                hole=0.42,
                marker=dict(colors=pie_colors, line=dict(color="#1a1f2e", width=2)),
                textinfo="label+percent",
                textfont=dict(color="#e8eaf6", size=11),
                hovertemplate="%{label}<br>%{value:.3f} kWh (%{percent})<extra></extra>"
            ))
            total_disp = sum(pie_vals)
            fig_pie.add_annotation(
                text=f"<b>{total_disp:.2f}</b><br>kWh",
                x=0.5, y=0.5, font=dict(size=13, color="#f5a623"),
                showarrow=False, xref="paper", yref="paper"
            )
            fig_pie.update_layout(
                height=320, margin=dict(t=20, b=10, l=0, r=0),
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_tbl:
            st.markdown("**各元件耗電明細**")
            total_v  = row["驗算總電"]
            tbl_rows = []
            for k in verify_kwh_cols:
                v   = row[k]
                pct = v / total_v * 100 if total_v > 0 else 0.0
                tbl_rows.append({"元件": k, "耗電 (kWh)": f"{v:.3f}", "佔比": f"{pct:.1f}%"})
            tbl_rows.append({"元件": "── 合計 ──", "耗電 (kWh)": f"{total_v:.3f}", "佔比": "100.0%"})
            st.dataframe(tbl_rows, use_container_width=True, hide_index=True, height=240)

            csv_bytes = pd.DataFrame(tbl_rows).to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ 下載本日報表 CSV",
                data=csv_bytes,
                file_name=f"PA60_report_{fname.replace('.csv','')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        st.markdown("---")

# ══════════════════════════════════════════════
# Tab 3 – Raw Data
# ══════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-label">🗂️ 原始資料預覽</div>', unsafe_allow_html=True)
    sel_file_view = st.selectbox("選擇檔案", selected_files, key="pa60_raw_view")
    if sel_file_view:
        df_show  = dfs[sel_file_view]
        t0_view  = pd.Timestamp(selected_time[0])
        t1_view  = pd.Timestamp(selected_time[1])
        df_view  = df_show.loc[(df_show.index >= t0_view) & (df_show.index <= t1_view)]
        st.caption(f"顯示 {len(df_view):,} 筆 / 共 {len(df_show):,} 筆（依左側時間範圍篩選）")
        st.dataframe(df_view.reset_index(), use_container_width=True, height=380)

        csv_dl = df_view.reset_index().to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ 下載篩選後資料 CSV",
            data=csv_dl,
            file_name=f"PA60_filtered_{sel_file_view}",
            mime="text/csv",
        )
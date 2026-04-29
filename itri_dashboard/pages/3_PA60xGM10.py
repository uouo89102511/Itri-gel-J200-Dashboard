"""
PA60 × GM10 疊圖比對分析 - 月份分析版
- 兩側支援多檔（整月）CSV
- 電力比對：L1 冷庫總電 vs 驗算總電（壓縮機+除霜+除霧+冷凝+蒸發）
- 溫度統計：CH1-CH8 個別 + 庫內 8 點總平均、CH101-CH106 個別 + 庫外 5 點總平均
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
    .stApp { background: linear-gradient(135deg, #0a1628 0%, #0d2137 50%, #0a1628 100%); color: #e3f2fd; }
    .main .block-container { padding: 1.5rem 2rem; }
    .section-title {
        font-size: 0.85rem; font-weight: 600; color: #42a5f5;
        text-transform: uppercase; letter-spacing: 0.1em;
        margin: 16px 0 8px 0; padding-bottom: 4px;
        border-bottom: 2px solid #1e4976;
    }
    .kpi-card {
        background: linear-gradient(135deg, #0d2137 0%, #102840 100%);
        border: 1px solid #1e4976; border-radius: 10px;
        padding: 12px 14px; text-align: center; height: 100%;
    }
    .kpi-label { font-size: 0.7rem; color: #4a7fa5; letter-spacing: 0.08em; text-transform: uppercase; }
    .kpi-value { font-size: 1.5rem; font-weight: 700; color: #4fc3f7; }
    .kpi-unit  { font-size: 0.78rem; color: #4a7fa5; }
    .upload-box {
        background: rgba(13,33,55,0.6); border: 1px dashed #1e4976;
        border-radius: 10px; padding: 16px; margin-bottom: 12px;
    }
    .file-chip {
        display: inline-block; background: rgba(102,187,106,0.1);
        border: 1px solid rgba(102,187,106,0.3); border-radius: 16px;
        padding: 2px 9px; font-size: 0.72rem; color: #66bb6a; margin: 1px;
    }
    .highlight-box {
        background: linear-gradient(90deg, rgba(13,33,55,0.5), rgba(21,101,192,0.2), rgba(13,33,55,0.5));
        border: 1px solid #4fc3f7; border-radius: 10px;
        padding: 14px 22px; text-align: center; margin: 10px 0;
    }
    .highlight-box-orange {
        background: linear-gradient(90deg, rgba(13,33,55,0.5), rgba(255,138,101,0.18), rgba(13,33,55,0.5));
        border: 1px solid #ff8a65; border-radius: 10px;
        padding: 14px 22px; text-align: center; margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("""
<div style='display:flex; align-items:center; gap:14px; margin-bottom:0.3rem;'>
    <span style='font-size:2.2rem;'>📊</span>
    <div>
        <div style='font-size:1.8rem; font-weight:800; background:linear-gradient(90deg,#66bb6a,#4fc3f7);
             -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;'>
            PA60 × GM10 疊圖比對分析
        </div>
        <div style='font-size:0.85rem; color:#4a7fa5;'>月份分析版 ｜ 多檔上傳 ｜ 電力驗算 + 庫內外溫度統計</div>
    </div>
</div>
<hr style='border:none; border-top:1px solid #1e3a5f; margin:1rem 0;'>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Definitions
# ─────────────────────────────────────────────
INSIDE_SENSORS = {
    'CH1': {'label': 'CH1 後左上', 'col_key': 'CH1(測試通道_01)'},
    'CH2': {'label': 'CH2 前左上', 'col_key': 'CH2(測試通道_02)'},
    'CH3': {'label': 'CH3 前右上', 'col_key': 'CH3(通道 3)'},
    'CH4': {'label': 'CH4 後右上', 'col_key': 'CH4(通道 4)'},
    'CH5': {'label': 'CH5 後左下', 'col_key': 'CH5(通道 5)'},
    'CH6': {'label': 'CH6 前左下', 'col_key': 'CH6(通道 6)'},
    'CH7': {'label': 'CH7 前右下', 'col_key': 'CH7(通道 7)'},
    'CH8': {'label': 'CH8 後右下', 'col_key': 'CH8(通道 8)'},
}
OUTSIDE_SENSORS = {
    'CH101': {'label': 'CH101 壓縮機',  'col_key': 'CH101(一號壓縮機)',         'unit': '°C'},
    'CH102': {'label': 'CH102 左T',     'col_key': 'CH102(通道 102)',         'unit': '°C'},
    'CH103': {'label': 'CH103 前T',     'col_key': 'CH103(通道 103)',         'unit': '°C'},
    'CH104': {'label': 'CH104 上T',     'col_key': 'CH104(通道 104)',         'unit': '°C'},
    'CH106': {'label': 'CH106 前T溫溼', 'col_key': 'CH106(關鍵數據 (CH106))', 'unit': '°C'},
    'CH105': {'label': 'CH105 前H溫溼', 'col_key': 'CH105(通道 105)',         'unit': '%RH'},
}

# 注意順序：L1 與 驗算總電 為主要比對，放最前面
PA60_POWER_COLS = {
    "L1 冷庫總電 (kW)":   "L1_kW_total (冷庫總電)",
    "驗算總電 (kW)":      "驗算總電 (kW)",
    "L2 壓縮機總電 (kW)": "L2_kW_total (壓縮機總電)",
    "L3 除霜電熱 (kW)":   "L3_kW_total (除霜電熱)",
    "L4 除霧電熱 (kW)":   "L4_除霧電熱",
    "L4 冷凝風扇 (kW)":   "L4_冷凝風扇",
    "L4 蒸發風扇 (kW)":   "L4_蒸發風扇",
}

# ─────────────────────────────────────────────
# Loaders
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_pa60_single(file_bytes):
    df = pd.read_csv(io.BytesIO(file_bytes))
    if '時間' in df.columns:
        df['時間'] = pd.to_datetime(df['時間'])
        df = df.sort_values('時間').reset_index(drop=True)

    derived = {
        "L1_kW_total (冷庫總電)":   (["L1_kW_a","L1_kW_b","L1_kW_c"], lambda d: d["L1_kW_a"]+d["L1_kW_b"]+d["L1_kW_c"]),
        "L2_kW_total (壓縮機總電)": (["L2_kW_a","L2_kW_b","L2_kW_c"], lambda d: d["L2_kW_a"]+d["L2_kW_b"]+d["L2_kW_c"]),
        "L3_kW_total (除霜電熱)":   (["L3_kW_a","L3_kW_b","L3_kW_c"], lambda d: d["L3_kW_a"]+d["L3_kW_b"]+d["L3_kW_c"]),
        "L4_除霧電熱": (["L4_V_ab","L4_I_a"], lambda d: d["L4_V_ab"]*d["L4_I_a"]*0.001),
        "L4_冷凝風扇": (["L4_V_bc","L4_I_b"], lambda d: d["L4_V_bc"]*d["L4_I_b"]*0.83*0.001),
        "L4_蒸發風扇": (["L4_V_ab","L4_I_c"], lambda d: d["L4_V_ab"]*d["L4_I_c"]*0.001),
    }
    for new_col, (req, formula) in derived.items():
        if all(c in df.columns for c in req):
            num = {c: pd.to_numeric(df[c], errors='coerce') for c in req}
            df[new_col] = formula(num)

    # 驗算總電 (kW) = L2 + L3 + L4 三項
    verify_components = [
        "L2_kW_total (壓縮機總電)",
        "L3_kW_total (除霜電熱)",
        "L4_除霧電熱",
        "L4_冷凝風扇",
        "L4_蒸發風扇",
    ]
    if all(c in df.columns for c in verify_components):
        df["驗算總電 (kW)"] = sum(df[c] for c in verify_components)

    return df

@st.cache_data(show_spinner=False)
def load_gm10_single(file_bytes):
    df = pd.read_csv(io.BytesIO(file_bytes), parse_dates=['時間'])
    df = df.sort_values('時間').reset_index(drop=True)
    return df

def add_gm10_derived(df):
    inside_cols = [s['col_key'] for s in INSIDE_SENSORS.values() if s['col_key'] in df.columns]
    if inside_cols:
        df['avg_inside_T'] = df[inside_cols].mean(axis=1)
        df['max_inside_T'] = df[inside_cols].max(axis=1)
        df['min_inside_T'] = df[inside_cols].min(axis=1)
    # 庫外 5 點(°C only, 排除 CH105 濕度)
    outside_temp_keys = [s['col_key'] for s in OUTSIDE_SENSORS.values()
                         if s['col_key'] in df.columns and s.get('unit') == '°C']
    if outside_temp_keys:
        df['avg_outside_T'] = df[outside_temp_keys].mean(axis=1)
    return df

def trapezoid_kwh(times, powers):
    """梯形積分計算 kWh"""
    s = pd.to_numeric(powers, errors='coerce').dropna()
    if len(s) < 2: return 0.0
    t_hr = pd.DatetimeIndex(times[s.index]).astype(np.int64) / 1e9 / 3600
    return float(np.sum((s.values[:-1] + s.values[1:]) / 2 * np.diff(t_hr)))

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 疊圖比對設定")
    st.markdown("---")

    st.markdown("### 📂 上傳資料（兩側皆可多選）")
    pa60_files = st.file_uploader(
        "⚡ PA60 電力 CSV（多選）", type=["csv"],
        accept_multiple_files=True, key="pa60_uploads",
        help="可一次上傳整月的 PA60 CSV"
    )
    gm10_files = st.file_uploader(
        "❄️ GM10 溫度 CSV（多選）", type=["csv"],
        accept_multiple_files=True, key="gm10_uploads",
        help="可一次上傳整月的 GM10 CSV"
    )

    st.markdown("---")
    st.markdown("### ⚙️ 重採樣")
    resample_opt = st.selectbox(
        "資料頻率（月份建議 5 分鐘以上）",
        ["原始","1 分鐘","5 分鐘","15 分鐘","30 分鐘","1 小時"],
        index=2
    )
    resample_map = {"原始":None,"1 分鐘":"1min","5 分鐘":"5min",
                    "15 分鐘":"15min","30 分鐘":"30min","1 小時":"1h"}
    rs_rule = resample_map[resample_opt]

    st.markdown("---")
    st.markdown("### 📋 電力欄位")
    selected_pa60_cols = st.multiselect(
        "PA60 電力欄位",
        list(PA60_POWER_COLS.keys()),
        default=["L1 冷庫總電 (kW)", "驗算總電 (kW)"],
        key="pa60_cols"
    )

    st.markdown("---")
    st.markdown("### 🌡️ 溫度欄位")
    gm10_temp_options = {
        **{v['label']: v['col_key'] for v in INSIDE_SENSORS.values()},
        **{v['label']: v['col_key'] for v in OUTSIDE_SENSORS.values()},
        "庫內 8 點總平均": "avg_inside_T",
        "庫外 5 點總平均": "avg_outside_T",
        "庫內最高溫": "max_inside_T",
        "庫內最低溫": "min_inside_T",
    }
    selected_gm10_cols = st.multiselect(
        "GM10 溫度欄位",
        list(gm10_temp_options.keys()),
        default=["庫內 8 點總平均", "庫外 5 點總平均", "CH101 壓縮機"],
        key="gm10_cols"
    )

    st.markdown("---")
    st.markdown("### 🎛️ 顯示設定")
    show_overlap = st.checkbox("電力 + 溫度合併同一 Y 軸", value=False)
    show_corr    = st.checkbox("顯示相關係數矩陣", value=True)
    show_stats   = st.checkbox("顯示統計摘要", value=True)

# ─────────────────────────────────────────────
# Wait for both
# ─────────────────────────────────────────────
if not pa60_files or not gm10_files:
    col_a, col_b = st.columns(2)
    pa60_status = "✅" if pa60_files else "⏳"
    gm10_status = "✅" if gm10_files else "⏳"
    pa60_count  = f"已選 {len(pa60_files)} 個" if pa60_files else "請上傳"
    gm10_count  = f"已選 {len(gm10_files)} 個" if gm10_files else "請上傳"
    with col_a:
        st.markdown(f"""<div class='upload-box'>
            <div style='font-size:2rem; text-align:center;'>⚡</div>
            <div style='text-align:center; color:#f5a623; font-weight:600; margin:6px 0 4px;'>PA60 電力 CSV（多選）</div>
            <div style='text-align:center; font-size:0.82rem; color:#4a7fa5;'>{pa60_count}</div>
            <div style='text-align:center; margin-top:8px;'><span style='font-size:1.6rem;'>{pa60_status}</span></div>
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""<div class='upload-box'>
            <div style='font-size:2rem; text-align:center;'>❄️</div>
            <div style='text-align:center; color:#42a5f5; font-weight:600; margin:6px 0 4px;'>GM10 溫度 CSV（多選）</div>
            <div style='text-align:center; font-size:0.82rem; color:#4a7fa5;'>{gm10_count}</div>
            <div style='text-align:center; margin-top:8px;'><span style='font-size:1.6rem;'>{gm10_status}</span></div>
        </div>""", unsafe_allow_html=True)
    st.info("👈 請在左側同時上傳 **PA60 電力 CSV** 與 **GM10 溫度 CSV**（皆支援多選整月）。")
    st.stop()

# ─────────────────────────────────────────────
# Multi-load both sides
# ─────────────────────────────────────────────
with st.spinner("載入並處理資料中..."):
    pa60_dfs, gm10_dfs = [], []
    pa60_errs, gm10_errs = [], []

    progress = st.progress(0, text="載入 PA60...")
    total = len(pa60_files) + len(gm10_files)
    cnt = 0
    for f in pa60_files:
        try:
            pa60_dfs.append(load_pa60_single(f.read()))
        except Exception as e:
            pa60_errs.append((f.name, str(e)))
        cnt += 1
        progress.progress(cnt/total, text=f"PA60 {cnt}/{len(pa60_files)}: {f.name}")
    for f in gm10_files:
        try:
            gm10_dfs.append(load_gm10_single(f.read()))
        except Exception as e:
            gm10_errs.append((f.name, str(e)))
        cnt += 1
        progress.progress(cnt/total, text=f"GM10: {f.name}")
    progress.empty()

if pa60_errs or gm10_errs:
    with st.expander(f"⚠️ {len(pa60_errs)+len(gm10_errs)} 個檔案載入失敗", expanded=False):
        for fn, e in pa60_errs + gm10_errs:
            st.caption(f"**{fn}**：{e}")

if not pa60_dfs or not gm10_dfs:
    st.error("PA60 或 GM10 沒有成功載入任何檔案")
    st.stop()

# Concat
df_pa60 = pd.concat(pa60_dfs, ignore_index=True).sort_values('時間').drop_duplicates(subset=['時間']).reset_index(drop=True)
df_gm10 = pd.concat(gm10_dfs, ignore_index=True).sort_values('時間').drop_duplicates(subset=['時間']).reset_index(drop=True)
df_gm10 = add_gm10_derived(df_gm10)

# Resample
if rs_rule:
    df_pa60 = df_pa60.set_index('時間').resample(rs_rule).mean(numeric_only=True).reset_index()
    df_gm10 = df_gm10.set_index('時間').resample(rs_rule).mean(numeric_only=True).reset_index()

# Time overlap
pa60_ts, pa60_te = df_pa60['時間'].min(), df_pa60['時間'].max()
gm10_ts, gm10_te = df_gm10['時間'].min(), df_gm10['時間'].max()
overlap_start = max(pa60_ts, gm10_ts)
overlap_end   = min(pa60_te, gm10_te)
has_overlap   = overlap_start < overlap_end

# ─────────────────────────────────────────────
# Time Info
# ─────────────────────────────────────────────
st.markdown("<div class='section-title'>📅 資料載入概況</div>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f"""<div class='kpi-card'>
    <div class='kpi-label'>⚡ PA60 檔案</div>
    <div class='kpi-value' style='font-size:1.2rem; color:#f5a623;'>{len(pa60_files)} 個</div>
    <div class='kpi-unit'>{pa60_ts.strftime('%m/%d')} → {pa60_te.strftime('%m/%d')}</div>
</div>""", unsafe_allow_html=True)
c2.markdown(f"""<div class='kpi-card'>
    <div class='kpi-label'>⚡ PA60 點數</div>
    <div class='kpi-value' style='font-size:1.2rem; color:#f5a623;'>{len(df_pa60):,}</div>
    <div class='kpi-unit'>{resample_opt}</div>
</div>""", unsafe_allow_html=True)
c3.markdown(f"""<div class='kpi-card'>
    <div class='kpi-label'>❄️ GM10 檔案</div>
    <div class='kpi-value' style='font-size:1.2rem; color:#4fc3f7;'>{len(gm10_files)} 個</div>
    <div class='kpi-unit'>{gm10_ts.strftime('%m/%d')} → {gm10_te.strftime('%m/%d')}</div>
</div>""", unsafe_allow_html=True)
c4.markdown(f"""<div class='kpi-card'>
    <div class='kpi-label'>❄️ GM10 點數</div>
    <div class='kpi-value' style='font-size:1.2rem; color:#4fc3f7;'>{len(df_gm10):,}</div>
    <div class='kpi-unit'>{resample_opt}</div>
</div>""", unsafe_allow_html=True)

if has_overlap:
    overlap_days = (overlap_end - overlap_start).total_seconds() / 86400
    st.success(f"✅ 時間重疊區間：**{overlap_start.strftime('%Y-%m-%d %H:%M')}** → **{overlap_end.strftime('%Y-%m-%d %H:%M')}**（{overlap_days:.1f} 天）")
else:
    st.error("⚠️ PA60 與 GM10 資料時間範圍**無重疊**，請確認 CSV 日期。")
    st.stop()

# ─────────────────────────────────────────────
# Time Slider
# ─────────────────────────────────────────────
st.markdown("<div class='section-title'>⏱️ 選擇分析時間範圍</div>", unsafe_allow_html=True)
time_range = st.slider(
    "時間範圍",
    min_value=overlap_start.to_pydatetime(),
    max_value=overlap_end.to_pydatetime(),
    value=(overlap_start.to_pydatetime(), overlap_end.to_pydatetime()),
    format="MM/DD HH:mm",
    label_visibility="collapsed"
)
t0 = pd.Timestamp(time_range[0])
t1 = pd.Timestamp(time_range[1])

dff_pa60 = df_pa60[(df_pa60['時間'] >= t0) & (df_pa60['時間'] <= t1)].copy()
dff_gm10 = df_gm10[(df_gm10['時間'] >= t0) & (df_gm10['時間'] <= t1)].copy()

if len(dff_pa60) == 0 or len(dff_gm10) == 0:
    st.error("選取範圍內無足夠資料。")
    st.stop()

# ─────────────────────────────────────────────
# ⭐ NEW: Power Verification Highlight (L1 vs 驗算總電)
# ─────────────────────────────────────────────
st.markdown("<div class='section-title'>⚡ 電力驗算：L1 冷庫總電 vs 驗算總電</div>", unsafe_allow_html=True)
st.caption("驗算總電 = L2 壓縮機 + L3 除霜電熱 + L4 除霧 + L4 冷凝風扇 + L4 蒸發風扇")

l1_col  = "L1_kW_total (冷庫總電)"
ver_col = "驗算總電 (kW)"

if l1_col in dff_pa60.columns and ver_col in dff_pa60.columns:
    s_l1  = pd.to_numeric(dff_pa60[l1_col],  errors='coerce').reset_index(drop=True)
    s_ver = pd.to_numeric(dff_pa60[ver_col], errors='coerce').reset_index(drop=True)
    times_arr = pd.DatetimeIndex(dff_pa60['時間']).reset_index(drop=True) if hasattr(pd.DatetimeIndex(dff_pa60['時間']), 'reset_index') else pd.Series(dff_pa60['時間'].values)

    # 直接以 ndarray 做梯形積分
    t_hr = pd.DatetimeIndex(dff_pa60['時間']).astype(np.int64).values / 1e9 / 3600
    l1_vals  = s_l1.fillna(0).values
    ver_vals = s_ver.fillna(0).values
    dt = np.diff(t_hr)
    l1_kwh  = float(np.sum((l1_vals[:-1]  + l1_vals[1:])  / 2 * dt))
    ver_kwh = float(np.sum((ver_vals[:-1] + ver_vals[1:]) / 2 * dt))
    diff_kwh = l1_kwh - ver_kwh
    err_pct  = (diff_kwh / l1_kwh * 100) if l1_kwh > 0 else 0.0
    err_color = "#66bb6a" if abs(err_pct) < 5 else ("#ffd54f" if abs(err_pct) < 10 else "#ef5350")
    err_icon  = "🟢" if abs(err_pct) < 5 else ("🟡" if abs(err_pct) < 10 else "🔴")

    pc1, pc2, pc3, pc4 = st.columns(4)
    pc1.markdown(f"""<div class='kpi-card'>
        <div class='kpi-label'>🔵 L1 冷庫總電</div>
        <div class='kpi-value' style='color:#4fc3f7;'>{l1_kwh:.2f}</div>
        <div class='kpi-unit'>kWh</div>
    </div>""", unsafe_allow_html=True)
    pc2.markdown(f"""<div class='kpi-card'>
        <div class='kpi-label'>🟢 驗算總電</div>
        <div class='kpi-value' style='color:#66bb6a;'>{ver_kwh:.2f}</div>
        <div class='kpi-unit'>kWh</div>
    </div>""", unsafe_allow_html=True)
    pc3.markdown(f"""<div class='kpi-card'>
        <div class='kpi-label'>差值 (L1 - 驗算)</div>
        <div class='kpi-value' style='color:#ffd54f;'>{diff_kwh:+.2f}</div>
        <div class='kpi-unit'>kWh</div>
    </div>""", unsafe_allow_html=True)
    pc4.markdown(f"""<div class='kpi-card'>
        <div class='kpi-label'>{err_icon} 量測誤差</div>
        <div class='kpi-value' style='color:{err_color};'>{err_pct:+.2f}</div>
        <div class='kpi-unit'>%</div>
    </div>""", unsafe_allow_html=True)

    # Dedicated overlay chart for L1 vs 驗算總電
    fig_pwr = go.Figure()
    fig_pwr.add_trace(go.Scatter(
        x=dff_pa60['時間'], y=s_l1,
        name='L1 冷庫總電', mode='lines',
        line=dict(width=2.2, color='#4fc3f7'),
        hovertemplate="L1: %{y:.3f} kW<extra></extra>"
    ))
    fig_pwr.add_trace(go.Scatter(
        x=dff_pa60['時間'], y=s_ver,
        name='驗算總電', mode='lines',
        line=dict(width=2.2, color='#66bb6a', dash='dot'),
        hovertemplate="驗算: %{y:.3f} kW<extra></extra>"
    ))
    # Diff area
    fig_pwr.add_trace(go.Scatter(
        x=dff_pa60['時間'], y=(s_l1 - s_ver),
        name='差值 (L1 - 驗算)', mode='lines',
        line=dict(width=1, color='#ffd54f', dash='dash'),
        hovertemplate="差: %{y:.3f} kW<extra></extra>",
        visible='legendonly'
    ))
    fig_pwr.update_layout(
        plot_bgcolor='rgba(10,20,40,0.9)', paper_bgcolor='rgba(0,0,0,0)',
        height=360, hovermode='x unified',
        legend=dict(orientation='h', y=-0.18, font=dict(color='#b3d4f0', size=10),
                    bgcolor='rgba(0,0,0,0)'),
        xaxis=dict(gridcolor='rgba(30,73,118,0.4)', tickfont=dict(color='#7ab3d4')),
        yaxis=dict(title='功率 (kW)', gridcolor='rgba(30,73,118,0.3)',
                   tickfont=dict(color='#7ab3d4'), title_font=dict(color='#7ab3d4')),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig_pwr, use_container_width=True)
else:
    st.warning("⚠️ PA60 資料缺少 L1 冷庫總電或驗算總電所需欄位，無法計算驗算對比。")

# ─────────────────────────────────────────────
# ⭐ NEW: Temperature Summary Cards
# ─────────────────────────────────────────────
st.markdown("<div class='section-title'>🌡️ 庫內外溫度統計（範圍內平均）</div>", unsafe_allow_html=True)

# ── 庫內 CH1-CH8 ──
st.markdown("**❄️ 庫內 8 點 (CH1 ~ CH8)**")
in_row1 = st.columns(4)
in_row2 = st.columns(4)
inside_items = list(INSIDE_SENSORS.items())
for i, (name, s) in enumerate(inside_items):
    if s['col_key'] not in dff_gm10.columns: continue
    sval = pd.to_numeric(dff_gm10[s['col_key']], errors='coerce').dropna()
    if len(sval) == 0: continue
    avg_v, max_v, min_v = sval.mean(), sval.max(), sval.min()
    target = in_row1[i] if i < 4 else in_row2[i-4]
    target.markdown(f"""<div class='kpi-card'>
        <div class='kpi-label'>{name}</div>
        <div class='kpi-value' style='color:#4fc3f7; font-size:1.2rem;'>{avg_v:.2f}°C</div>
        <div class='kpi-unit'>{s['label'].split(' ',1)[1]} ｜ ↑{max_v:.1f} ↓{min_v:.1f}</div>
    </div>""", unsafe_allow_html=True)

# 庫內 8 點總平均 - 強調卡
if 'avg_inside_T' in dff_gm10.columns:
    inside_overall = pd.to_numeric(dff_gm10['avg_inside_T'], errors='coerce').mean()
    inside_max = pd.to_numeric(dff_gm10['avg_inside_T'], errors='coerce').max()
    inside_min = pd.to_numeric(dff_gm10['avg_inside_T'], errors='coerce').min()
    st.markdown(f"""<div class='highlight-box'>
        <span style='color:#7ab3d4; font-size:0.78rem; letter-spacing:0.1em;'>📊 庫內 8 點總平均</span>
        <span style='color:#4fc3f7; font-size:1.9rem; font-weight:800; margin-left:14px;'>{inside_overall:.2f} °C</span>
        <span style='color:#7ab3d4; font-size:0.82rem; margin-left:14px;'>
            （區間最高 {inside_max:.2f}°C ｜ 最低 {inside_min:.2f}°C）
        </span>
    </div>""", unsafe_allow_html=True)

# ── 庫外 CH101-CH106 ──
st.markdown("**🏭 庫外 6 點 (CH101 ~ CH106)**")
out_row = st.columns(6)
out_items = list(OUTSIDE_SENSORS.items())
for i, (name, s) in enumerate(out_items):
    if s['col_key'] not in dff_gm10.columns: continue
    sval = pd.to_numeric(dff_gm10[s['col_key']], errors='coerce').dropna()
    if len(sval) == 0: continue
    avg_v = sval.mean()
    unit = s['unit']
    if unit == '%RH':
        color = "#80deea"
    elif name == 'CH101':
        color = "#ff8a65"
    else:
        color = "#a5d6a7"
    label_short = s['label'].split(' ',1)[1] if ' ' in s['label'] else s['label']
    out_row[i].markdown(f"""<div class='kpi-card'>
        <div class='kpi-label'>{name}</div>
        <div class='kpi-value' style='color:{color}; font-size:1.2rem;'>{avg_v:.2f}{unit}</div>
        <div class='kpi-unit'>{label_short}</div>
    </div>""", unsafe_allow_html=True)

# 庫外 5 點總平均（°C 不含濕度）
if 'avg_outside_T' in dff_gm10.columns:
    outside_overall = pd.to_numeric(dff_gm10['avg_outside_T'], errors='coerce').mean()
    outside_max = pd.to_numeric(dff_gm10['avg_outside_T'], errors='coerce').max()
    outside_min = pd.to_numeric(dff_gm10['avg_outside_T'], errors='coerce').min()
    st.markdown(f"""<div class='highlight-box-orange'>
        <span style='color:#7ab3d4; font-size:0.78rem; letter-spacing:0.1em;'>📊 庫外 5 點(°C) 總平均（排除 CH105 濕度）</span>
        <span style='color:#ff8a65; font-size:1.9rem; font-weight:800; margin-left:14px;'>{outside_overall:.2f} °C</span>
        <span style='color:#7ab3d4; font-size:0.82rem; margin-left:14px;'>
            （區間最高 {outside_max:.2f}°C ｜ 最低 {outside_min:.2f}°C）
        </span>
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Validate selected columns for time-series chart
# ─────────────────────────────────────────────
valid_pa60 = [(label, PA60_POWER_COLS[label]) for label in selected_pa60_cols
              if PA60_POWER_COLS[label] in dff_pa60.columns]
valid_gm10 = [(label, gm10_temp_options[label]) for label in selected_gm10_cols
              if gm10_temp_options[label] in dff_gm10.columns]

# ─────────────────────────────────────────────
# Overlay Plot (custom selections)
# ─────────────────────────────────────────────
if valid_pa60 or valid_gm10:
    st.markdown("<div class='section-title'>📈 自訂欄位疊圖比對</div>", unsafe_allow_html=True)

    POWER_COLORS = ['#f5a623','#ffd54f','#ffb74d','#ff8a65','#a5d6a7','#80cbc4','#ce93d8']
    TEMP_COLORS  = ['#4fc3f7','#29b6f6','#81d4fa','#b3e5fc','#90caf9','#42a5f5','#ce93d8','#f48fb1','#a5d6a7','#80cbc4']

    if show_overlap:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        for i, (label, col) in enumerate(valid_pa60):
            s = pd.to_numeric(dff_pa60[col], errors='coerce')
            fig.add_trace(go.Scatter(
                x=dff_pa60['時間'], y=s, name=f"⚡ {label}",
                mode='lines', line=dict(width=2, color=POWER_COLORS[i % len(POWER_COLORS)]),
                hovertemplate=f"⚡ {label}: %{{y:.3f}} kW<extra></extra>"
            ), secondary_y=False)
        for i, (label, col) in enumerate(valid_gm10):
            s = pd.to_numeric(dff_gm10[col], errors='coerce')
            fig.add_trace(go.Scatter(
                x=dff_gm10['時間'], y=s, name=f"🌡️ {label}",
                mode='lines', line=dict(width=2, color=TEMP_COLORS[i % len(TEMP_COLORS)], dash='dot'),
                hovertemplate=f"🌡️ {label}: %{{y:.2f}}°C<extra></extra>"
            ), secondary_y=True)
        fig.update_yaxes(title_text="電力 (kW)", secondary_y=False,
                         title_font=dict(color='#f5a623'), tickfont=dict(color='#f5a623'),
                         gridcolor='rgba(245,166,35,0.1)')
        fig.update_yaxes(title_text="溫度 (°C)", secondary_y=True,
                         title_font=dict(color='#4fc3f7'), tickfont=dict(color='#4fc3f7'))
        fig.update_layout(
            plot_bgcolor='rgba(10,20,40,0.9)', paper_bgcolor='rgba(0,0,0,0)',
            height=480, hovermode='x unified',
            legend=dict(orientation='h', y=-0.15, font=dict(color='#b3d4f0', size=10),
                        bgcolor='rgba(0,0,0,0)'),
            xaxis=dict(gridcolor='rgba(30,73,118,0.4)', tickfont=dict(color='#7ab3d4')),
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        n_rows = (1 if valid_pa60 else 0) + (1 if valid_gm10 else 0)
        if n_rows > 0:
            row_titles = []
            if valid_pa60: row_titles.append("⚡ 電力數據 (kW)")
            if valid_gm10: row_titles.append("🌡️ 溫度數據 (°C)")
            fig = make_subplots(rows=n_rows, cols=1, shared_xaxes=True,
                                subplot_titles=row_titles, vertical_spacing=0.08)
            row_idx = 1
            if valid_pa60:
                for i, (label, col) in enumerate(valid_pa60):
                    s = pd.to_numeric(dff_pa60[col], errors='coerce')
                    fig.add_trace(go.Scatter(
                        x=dff_pa60['時間'], y=s, name=f"⚡ {label}",
                        mode='lines', line=dict(width=2, color=POWER_COLORS[i % len(POWER_COLORS)]),
                        hovertemplate=f"⚡ {label}: %{{y:.3f}} kW<extra></extra>"
                    ), row=row_idx, col=1)
                row_idx += 1
            if valid_gm10:
                for i, (label, col) in enumerate(valid_gm10):
                    s = pd.to_numeric(dff_gm10[col], errors='coerce')
                    fig.add_trace(go.Scatter(
                        x=dff_gm10['時間'], y=s, name=f"🌡️ {label}",
                        mode='lines', line=dict(width=2, color=TEMP_COLORS[i % len(TEMP_COLORS)]),
                        hovertemplate=f"🌡️ {label}: %{{y:.2f}}°C<extra></extra>"
                    ), row=row_idx, col=1)
            fig.update_layout(
                plot_bgcolor='rgba(10,20,40,0.9)', paper_bgcolor='rgba(0,0,0,0)',
                height=280 * n_rows, hovermode='x unified', dragmode='zoom',
                legend=dict(orientation='h', y=-0.12, font=dict(color='#b3d4f0', size=10),
                            bgcolor='rgba(0,0,0,0)'),
                margin=dict(l=10, r=10, t=30, b=10),
            )
            for axis_key in [f'xaxis{i}' if i > 1 else 'xaxis' for i in range(1, n_rows+1)]:
                fig.update_layout(**{axis_key: dict(gridcolor='rgba(30,73,118,0.4)',
                                                    tickfont=dict(color='#7ab3d4'))})
            for axis_key in [f'yaxis{i}' if i > 1 else 'yaxis' for i in range(1, n_rows+1)]:
                fig.update_layout(**{axis_key: dict(gridcolor='rgba(30,73,118,0.3)',
                                                    tickfont=dict(color='#7ab3d4'))})
            for ann in fig.layout.annotations:
                ann.font.color = "#4a7fa5"; ann.font.size = 11
            st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# Correlation
# ─────────────────────────────────────────────
if show_corr and valid_pa60 and valid_gm10:
    st.markdown("<div class='section-title'>🔗 相關係數分析（時間對齊 1 分鐘 merge）</div>", unsafe_allow_html=True)
    pa60_sel = dff_pa60[['時間'] + [c for _, c in valid_pa60]].set_index('時間')
    gm10_sel = dff_gm10[['時間'] + [c for _, c in valid_gm10]].set_index('時間')
    pa60_1m = pa60_sel.resample('1min').mean()
    gm10_1m = gm10_sel.resample('1min').mean()
    merged  = pd.concat([pa60_1m, gm10_1m], axis=1).dropna()

    if len(merged) > 5:
        rename_pa60 = {c: lbl for lbl, c in valid_pa60}
        rename_gm10 = {c: lbl for lbl, c in valid_gm10}
        merged_disp = merged.rename(columns={**rename_pa60, **rename_gm10})
        corr = merged_disp.corr()
        pa60_labels = [lbl for lbl, _ in valid_pa60]
        gm10_labels = [lbl for lbl, _ in valid_gm10]
        cross_corr = corr.loc[pa60_labels, gm10_labels]
        fig_corr = go.Figure(go.Heatmap(
            z=cross_corr.values,
            x=cross_corr.columns.tolist(),
            y=cross_corr.index.tolist(),
            colorscale=[[0, '#ff5252'], [0.5, '#ffffff'], [1, '#00e676']],
            zmid=0, zmin=-1, zmax=1,
            text=np.round(cross_corr.values, 2),
            texttemplate="%{text}",
            textfont=dict(size=13, color='black'),
            colorbar=dict(title='r', tickfont=dict(color='#7ab3d4')),
            hovertemplate="電力: %{y}<br>溫度: %{x}<br>相關係數: %{z:.3f}<extra></extra>"
        ))
        fig_corr.update_layout(
            plot_bgcolor='rgba(10,20,40,0.9)', paper_bgcolor='rgba(0,0,0,0)',
            height=max(220, 60*len(pa60_labels) + 100),
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis=dict(tickfont=dict(color='#7ab3d4'), side='bottom'),
            yaxis=dict(tickfont=dict(color='#7ab3d4')),
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        st.caption("r ≈ +1 正相關，r ≈ -1 負相關")
    else:
        st.warning("重疊資料點數不足，無法計算相關係數。")

# ─────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────
if show_stats:
    st.markdown("<div class='section-title'>📋 統計摘要</div>", unsafe_allow_html=True)
    cs1, cs2 = st.columns(2)
    with cs1:
        st.markdown("**⚡ PA60 電力統計**")
        if valid_pa60:
            rows = []
            for label, col in valid_pa60:
                s = pd.to_numeric(dff_pa60[col], errors='coerce').dropna()
                if len(s):
                    rows.append({"欄位": label, "平均 (kW)": f"{s.mean():.3f}",
                                 "最大 (kW)": f"{s.max():.3f}", "最小 (kW)": f"{s.min():.3f}",
                                 "標準差": f"{s.std():.3f}"})
            if rows: st.dataframe(rows, hide_index=True, use_container_width=True)
        else:
            st.info("未選擇 PA60 欄位")
    with cs2:
        st.markdown("**🌡️ GM10 溫度統計**")
        if valid_gm10:
            rows = []
            for label, col in valid_gm10:
                s = pd.to_numeric(dff_gm10[col], errors='coerce').dropna()
                if len(s):
                    rows.append({"欄位": label, "平均 (°C)": f"{s.mean():.2f}",
                                 "最大 (°C)": f"{s.max():.2f}", "最小 (°C)": f"{s.min():.2f}",
                                 "標準差": f"{s.std():.3f}"})
            if rows: st.dataframe(rows, hide_index=True, use_container_width=True)
        else:
            st.info("未選擇 GM10 欄位")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align:center; color:#3a5a7a; font-size:0.78rem;'>
    📊 PA60 × GM10 疊圖比對分析 - 月份分析版 ｜ ITRI 綠能所 智慧控制設備研究室 ｜ GB+44015-2026
</div>
""", unsafe_allow_html=True)
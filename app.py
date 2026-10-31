from html import escape

import pandas as pd
import streamlit as st

st.set_page_config(page_title="数据分析平台", page_icon="📊", layout="wide")
st.markdown("""
<style>
.stApp {background: #f5f7fb;}
.block-container {max-width: 1440px; padding-top: 5rem; padding-bottom: 3rem;}
[data-testid="stSidebar"] {background: #fff; border-right: 1px solid #e5eaf2;}
h1, h2, h3 {color: #172b4d;}
[data-testid="stMetric"] {background: white; border: 1px solid #e5eaf2;
 border-radius: 12px; padding: 20px; min-height: 120px;}
[data-testid="stMetricLabel"] {color: #64748b;}
[data-testid="stMetricValue"] {color: #1d4ed8;}
[data-baseweb="tab-list"] {gap: 24px; border-bottom: 1px solid #e5eaf2; margin-bottom: 20px;}
[data-baseweb="tab"] {padding: 12px 4px;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 12px;}
.brand {font-size: 20px; font-weight: 700; color: #1d4ed8; margin-bottom: 4px;}
.eyebrow {color: #64748b; font-size: 13px; letter-spacing: 1px; margin-bottom: 8px;}
.empty-state {background: white; border: 1px dashed #cbd5e1; border-radius: 14px;
 padding: 48px 24px; text-align: center; margin-top: 12px;}
.empty-state h3 {margin: 12px 0;}
.empty-state p {color: #64748b;}
@media (max-width: 640px) {
 .block-container {padding-top: 4rem;}
 [data-baseweb="tab-list"] {gap: 12px;}
 [data-testid="stMetric"] {padding: 14px;}
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="brand">📊 数析工作台</div>', unsafe_allow_html=True)
    st.caption("让数据清晰，让决策简单")
    st.divider()
    st.subheader("数据源")
    uploaded_file = st.file_uploader("上传数据文件", type=["csv", "xlsx"],
                                    help="支持 CSV、Excel；CSV 自动尝试 UTF-8 和 GB18030 编码。")
    st.caption("支持 .csv / .xlsx · Excel 可选择工作表")
    if uploaded_file is not None:
        st.success("文件已载入")
        st.text(uploaded_file.name)
    with st.expander("使用指南", expanded=uploaded_file is None):
        st.markdown("1. 上传 CSV 或 Excel 文件\n2. 查看数据概览与字段质量\n3. 选择指标，生成图表\n4. 下载当前数据")
    st.divider()
    st.caption("数据安全提示：请勿上传含密码或敏感个人信息的数据。")

st.markdown('<div class="eyebrow">工作空间 / 数据分析</div>', unsafe_allow_html=True)
st.title("数据分析平台")
st.caption("从数据导入到可视化分析，在一个工作台完成。")
overview, preview, statistics, charts = st.tabs(["数据概览", "数据明细", "统计分析", "可视化图表"])

if uploaded_file is None:
    with overview:
        for column, label in zip(st.columns(4), ["数据行数", "字段数量", "缺失值数量", "重复行数量"]):
            column.metric(label, "—")
        st.markdown('<div class="empty-state"><div>📂</div><h3>开启你的数据分析</h3>'
                    '<p>在左侧上传 CSV 或 Excel 文件，即可查看概况、统计与图表。</p></div>',
                    unsafe_allow_html=True)
    for tab in (preview, statistics, charts):
        with tab:
            st.info("请先在左侧上传数据文件。")
    st.stop()

try:
    if uploaded_file.name.lower().endswith(".csv"):
        try:
            df = pd.read_csv(uploaded_file)
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding="gb18030")
    else:
        workbook = pd.ExcelFile(uploaded_file)
        sheet = st.sidebar.selectbox("选择工作表", workbook.sheet_names)
        df = pd.read_excel(workbook, sheet_name=sheet)
except Exception as error:
    st.error(f"文件读取失败：{error}")
    st.stop()

if df.empty:
    st.warning("文件中没有可分析的数据。")
    st.stop()

missing = int(df.isna().sum().sum())
duplicates = int(df.duplicated().sum())
numeric_columns = df.select_dtypes(include="number").columns.tolist()
with overview:
    st.subheader("数据概览")
    st.caption(f"当前数据源：{uploaded_file.name}")
    for column, label, value in zip(st.columns(4),
            ["数据行数", "字段数量", "缺失值数量", "重复行数量"],
            [f"{len(df):,}", len(df.columns), missing, duplicates]):
        column.metric(label, value)
    left, right = st.columns([2, 1])
    with left, st.container(border=True):
        st.subheader("数据快览")
        st.dataframe(df.head(8), width="stretch", hide_index=True)
        st.caption("展示前 8 行，完整预览请切换至「数据明细」。")
    with right, st.container(border=True):
        st.subheader("数据质量")
        completeness = 1 - missing / df.size
        st.progress(completeness, text=f"数据完整率 {completeness:.1%}")
        st.write(f"数值字段：{len(numeric_columns)} 个")
        st.write(f"非数值字段：{len(df.columns) - len(numeric_columns)} 个")
        if missing or duplicates:
            st.info("存在缺失值或重复行，可在明细与统计中进一步检查。")
        else:
            st.success("未发现缺失值或重复行。")

with preview:
    st.subheader("数据明细")
    st.caption("最多显示前 500 行，下载可获取当前工作表的完整数据。")
    st.dataframe(df.head(500), width="stretch", hide_index=True)
    with st.expander("字段信息与缺失情况", expanded=True):
        field_info = pd.DataFrame({
            "字段": df.columns, "类型": df.dtypes.astype(str).values,
            "缺失数量": df.isna().sum().values,
            "缺失比例（%）": (df.isna().mean().values * 100).round(2),
        })
        st.dataframe(field_info, width="stretch", hide_index=True)

with statistics:
    st.subheader("描述性统计")
    st.caption("按字段汇总分布情况；非数值字段显示计数、唯一值等信息。")
    st.dataframe(df.describe(include="all").T, width="stretch")
    st.caption(f"当前数据包含 {duplicates:,} 行重复记录。")

with charts:
    st.subheader("可视化分析")
    if not numeric_columns:
        st.info("没有数值字段，暂时无法绘图。")
    else:
        controls, canvas = st.columns([1, 3])
        with controls, st.container(border=True):
            st.markdown("**图表设置**")
            x_column = st.selectbox("横轴字段", df.columns)
            y_column = st.selectbox("分析指标", numeric_columns)
            chart_type = st.radio("图表类型", ["柱状图", "折线图"])
            st.caption("聚合方式：分组平均值\n\n最多展示 100 组，忽略缺失值。")
        with canvas, st.container(border=True):
            if x_column == y_column:
                st.info("请选择不同的横轴字段和分析指标。")
            else:
                st.markdown(f"**{escape(str(y_column))} · 按 {escape(str(x_column))} 分组**")
                summary = (df[[x_column, y_column]].dropna()
                           .groupby(x_column, sort=True)[y_column].mean().head(100))
                if summary.empty:
                    st.info("所选字段没有可用于绘图的有效数据。")
                elif chart_type == "柱状图":
                    st.bar_chart(summary, color="#2563eb", height=380)
                else:
                    st.line_chart(summary, color="#2563eb", height=380)

st.divider()
footer, action = st.columns([3, 1])
footer.caption("导出当前数据 · CSV 使用 UTF-8 BOM 编码，便于 Excel 打开。")
with action:
    st.download_button("下载当前数据（CSV）", data=df.to_csv(index=False).encode("utf-8-sig"),
                       file_name="analysis_data.csv", mime="text/csv", width="stretch")

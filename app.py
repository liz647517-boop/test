import pandas as pd
import streamlit as st

st.set_page_config(page_title="数据分析平台", page_icon="📊", layout="wide")
st.title("📊 数据分析平台")
st.caption("上传数据 → 查看概况 → 分析与可视化")

with st.sidebar:
    st.header("导入数据")
    uploaded_file = st.file_uploader(
        "选择 CSV 或 Excel 文件",
        type=["csv", "xlsx"],
    )
    st.caption("请勿上传含密码或敏感个人信息的数据。")

if uploaded_file is None:
    st.info("请在左侧上传数据文件，开始分析。")
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

col1, col2, col3 = st.columns(3)
col1.metric("数据行数", f"{len(df):,}")
col2.metric("字段数量", len(df.columns))
col3.metric("缺失值数量", int(df.isna().sum().sum()))

preview, statistics, charts = st.tabs(["数据预览", "统计分析", "图表"])

with preview:
    st.dataframe(df.head(500), use_container_width=True)
    st.caption("最多显示前 500 行。")

    st.subheader("字段信息")
    field_info = pd.DataFrame({
        "字段": df.columns,
        "类型": df.dtypes.astype(str).values,
        "缺失数量": df.isna().sum().values,
        "缺失比例（%）": (df.isna().mean().values * 100).round(2),
    })
    st.dataframe(field_info, use_container_width=True, hide_index=True)

with statistics:
    st.subheader("描述性统计")
    st.dataframe(df.describe(include="all").T, use_container_width=True)
    st.metric("重复行数量", int(df.duplicated().sum()))

with charts:
    numeric_columns = df.select_dtypes(include="number").columns.tolist()

    if not numeric_columns:
        st.info("没有数值字段，暂时无法绘图。")
    else:
        x_column = st.selectbox("横轴字段", df.columns)
        y_column = st.selectbox("分析指标", numeric_columns)
        chart_type = st.radio("图表类型", ["柱状图", "折线图"], horizontal=True)

        chart_data = (
            df[[x_column, y_column]]
            if x_column != y_column
            else df[[y_column]]
        )

        if x_column == y_column:
            st.info("请选择不同的横轴字段和分析指标。")
        else:
            summary = (
                chart_data.dropna()
                .groupby(x_column, sort=True)[y_column]
                .mean()
                .head(100)
            )
            st.caption("按横轴分组计算指标平均值，最多展示 100 组。")
            if chart_type == "柱状图":
                st.bar_chart(summary)
            else:
                st.line_chart(summary)

st.download_button(
    "下载当前数据（CSV）",
    data=df.to_csv(index=False).encode("utf-8-sig"),
    file_name="analysis_data.csv",
    mime="text/csv",
)

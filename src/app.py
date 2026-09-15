from pathlib import Path
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="食價寶寶", page_icon="🥬")

base_dir = Path(__file__).resolve().parent.parent
db_path = base_dir / "data" / "prices.db"

# 讀取資料庫全部資料
conn = sqlite3.connect(db_path)
df = pd.read_sql_query("SELECT * FROM prices", conn)
conn.close()

st.title("🥬 食價寶寶")
st.caption("今天貴不貴，先問價寶寶")

# 品項下拉選單（用「口語名稱」讓使用者選）
crop_list = sorted(df["口語名稱"].unique())
selected_crop = st.selectbox("選擇食材", crop_list)

# 單位切換
unit = st.radio("價格單位", ["公斤", "台斤"], horizontal=True)

# 依單位決定要用哪個欄位、顯示什麼文字
if unit == "公斤":
    price_col = "平均價"
    unit_label = "kg"
    axis_label = "平均價 (元/公斤)"
else:
    price_col = "平均價_台斤"
    unit_label = "台斤"
    axis_label = "平均價 (元/台斤)"

# 篩選出選定品項的資料，並排除「休市」（平均價為0）的紀錄
filtered = df[(df["口語名稱"] == selected_crop) & (df["平均價"] > 0)].copy()

if filtered.empty:
    st.warning("目前沒有這個品項的有效價格資料。")
else:
    # 依交易日期排序，並用平均價做整體平均（若有多品種則取當日平均）
    daily_avg = filtered.groupby("交易日期")[price_col].mean().reset_index()
    daily_avg = daily_avg.sort_values("交易日期")

    latest_price = daily_avg[price_col].iloc[-1]
    st.metric(label=f"{selected_crop} 目前平均批發價", value=f"${latest_price:.1f} /{unit_label}")

    st.subheader("📈 近期價格趨勢")
    fig = px.line(daily_avg, x="交易日期", y=price_col, markers=True)
    fig.update_layout(yaxis_title=axis_label, xaxis_title="交易日期")
    st.plotly_chart(fig, width='stretch')

    st.caption("資料來源：農業部台北一批發市場｜批發價僅供趨勢參考，非零售實際售價")
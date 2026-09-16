from pathlib import Path
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

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

# 市場選擇
market_options = ["雙北綜合", "台北一", "台北二"]
selected_market = st.radio("選擇市場", market_options, horizontal=True)

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

# 篩選出選定品項＋選定市場的資料，並排除「休市」（平均價為0）的紀錄
filtered = df[
    (df["口語名稱"] == selected_crop) &
    (df["市場名稱"] == selected_market) &
    (df["平均價"] > 0)
].copy()

if filtered.empty:
    st.warning("目前沒有這個品項在此市場的有效價格資料。")
else:
    # 依交易日期排序，並用平均價做整體平均（若有多品種則取當日平均）
    daily_avg = filtered.groupby("交易日期")[price_col].mean().reset_index()
    daily_avg = daily_avg.sort_values("交易日期")

    latest_price = daily_avg[price_col].iloc[-1]
    st.metric(label=f"{selected_crop}（{selected_market}）目前平均批發價", value=f"${latest_price:.1f} /{unit_label}")

    # ---- 日期選擇器：查特定某天的價格 ----
    st.subheader("📅 查特定日期的價格")

    date_list = daily_avg["交易日期"].tolist()
    selected_date = st.selectbox("選擇日期", options=date_list, index=len(date_list) - 1)

    date_price = daily_avg.loc[daily_avg["交易日期"] == selected_date, price_col].iloc[0]
    st.metric(label=f"{selected_date} {selected_crop} 平均價", value=f"${date_price:.1f} /{unit_label}")

    # ---- 折線圖：趨勢，滑鼠移上去可看到每天數字 ----
    st.subheader("📈 近期價格趨勢")
    st.caption("滑鼠移到圖上的點，可以看到當天日期與價格；淺色區塊代表當天上價～下價的波動範圍")

    # 準備上價、下價的資料（要跟公斤/台斤單位一致）
    if unit == "公斤":
        high_col, low_col = "上價", "下價"
    else:
        filtered["上價_台斤"] = (filtered["上價"] * 0.6).round(2)
        filtered["下價_台斤"] = (filtered["下價"] * 0.6).round(2)
        high_col, low_col = "上價_台斤", "下價_台斤"

    daily_range = filtered.groupby("交易日期")[[high_col, low_col]].mean().reset_index()
    daily_avg = daily_avg.merge(daily_range, on="交易日期")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=daily_avg["交易日期"], y=daily_avg[high_col],
        line=dict(width=0), showlegend=False, hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=daily_avg["交易日期"], y=daily_avg[low_col],
        fill='tonexty', fillcolor='rgba(0, 123, 255, 0.15)',
        line=dict(width=0), name="價格波動範圍",
        hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=daily_avg["交易日期"], y=daily_avg[price_col],
        mode="lines+markers", name="平均價",
        line=dict(color="royalblue", width=2),
        hovertemplate="日期: %{x}<br>價格: %{y:.1f} 元<extra></extra>"
    ))

    fig.update_layout(yaxis_title=axis_label, xaxis_title="交易日期")
    st.plotly_chart(fig, width='stretch', config={'displayModeBar': False})

    # ---- 資料表格：可捲動查看所有日期 ----
    st.subheader("📋 每日價格明細")

    table_df = daily_avg.rename(columns={
        "交易日期": "日期",
        price_col: f"平均價 (元/{unit_label})"
    }).sort_values("日期", ascending=False)

    st.dataframe(table_df, width='stretch', hide_index=True)

    st.caption(f"資料來源：農業部台北一、台北二批發市場｜目前顯示「{selected_market}」數據，僅供趨勢參考，非零售實際售價")
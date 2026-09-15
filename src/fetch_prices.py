from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import pandas as pd
import requests
from urllib.parse import quote

base_dir = Path(__file__).resolve().parent.parent
csv_path = base_dir / "vegetables.csv"
df = pd.read_csv(csv_path)

db_path = base_dir / "data" / "prices.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS prices (
    口語名稱 TEXT,
    交易日期 TEXT,
    作物名稱 TEXT,
    市場名稱 TEXT,
    上價 REAL,
    中價 REAL,
    下價 REAL,
    平均價 REAL,
    平均價_台斤 REAL,
    交易量 REAL,
    UNIQUE(口語名稱, 交易日期, 作物名稱, 市場名稱)
)
""")
conn.commit()
print("成功讀取菜品主檔！")

markets = ["台北一", "台北二"]

# 只抓最近4天（今天往前推），民國年 = 西元年 - 1911
today = datetime.today()
start_date = f"{today.year - 1911}.{(today - timedelta(days=4)).strftime('%m.%d')}"
end_date = f"{today.year - 1911}.{today.strftime('%m.%d')}"

new_count = 0
skip_count = 0


def insert_row(chinese_name, trade_date, crop_name, market_name, high, mid, low, avg, volume):
    """寫入一筆資料，並自動算好台斤價"""
    avg_taijin = round(avg * 0.6, 2) if avg is not None else None
    try:
        cursor.execute("""
            INSERT INTO prices (口語名稱, 交易日期, 作物名稱, 市場名稱, 上價, 中價, 下價, 平均價, 平均價_台斤, 交易量)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chinese_name, trade_date, crop_name, market_name,
            high, mid, low, avg, avg_taijin, volume
        ))
        return True
    except sqlite3.IntegrityError:
        return False


for _, row in df.iterrows():
    chinese_name = row["name_zh"]
    official_name = row["api_name"]

    # 存放兩個市場抓回來的原始資料，用 (交易日期, 作物名稱) 當 key 分組，方便之後算雙北綜合
    combined = {}

    for market in markets:
        url = (
            "https://data.moa.gov.tw/Service/OpenData/FromM/FarmTransData.aspx"
            f"?$top=100&$skip=0"
            f"&Market={quote(market)}"
            f"&Crop={quote(str(official_name))}"
            f"&StartDate={start_date}&EndDate={end_date}"
        )

        try:
            response = requests.get(url, timeout=15)
            print(f"{chinese_name}({official_name}) [{market}] - 狀態碼: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                for item in data:
                    # 先把這個市場的原始資料存進資料庫（跟原本邏輯一樣）
                    ok = insert_row(
                        chinese_name, item["交易日期"], item["作物名稱"], item["市場名稱"],
                        item["上價"], item["中價"], item["下價"], item["平均價"], item["交易量"]
                    )
                    if ok:
                        new_count += 1
                    else:
                        skip_count += 1

                    # 同時把資料收集起來，準備算雙北綜合
                    key = (item["交易日期"], item["作物名稱"])
                    combined.setdefault(key, []).append(item)

        except requests.exceptions.RequestException as e:
            print(f"{chinese_name}({official_name}) [{market}] - 連線失敗，跳過這項: {e}")

    # 計算「雙北綜合」加權平均，並寫入資料庫
    for (trade_date, crop_name), items in combined.items():
        total_volume = sum(it["交易量"] for it in items)

        if total_volume > 0:
            weighted_high = sum(it["上價"] * it["交易量"] for it in items) / total_volume
            weighted_mid = sum(it["中價"] * it["交易量"] for it in items) / total_volume
            weighted_low = sum(it["下價"] * it["交易量"] for it in items) / total_volume
            weighted_avg = sum(it["平均價"] * it["交易量"] for it in items) / total_volume
        else:
            # 交易量都是0（例如休市），直接用簡單平均避免除以0
            weighted_high = sum(it["上價"] for it in items) / len(items)
            weighted_mid = sum(it["中價"] for it in items) / len(items)
            weighted_low = sum(it["下價"] for it in items) / len(items)
            weighted_avg = sum(it["平均價"] for it in items) / len(items)

        ok = insert_row(
            chinese_name, trade_date, crop_name, "雙北綜合",
            round(weighted_high, 2), round(weighted_mid, 2), round(weighted_low, 2),
            round(weighted_avg, 2), total_volume
        )
        if ok:
            new_count += 1
        else:
            skip_count += 1

conn.commit()
conn.close()
print(f"\n完成！新增 {new_count} 筆資料，略過 {skip_count} 筆重複資料。")
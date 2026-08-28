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

# 建立資料表（如果不存在），設定唯一鍵避免重複
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
    交易量 REAL,
    UNIQUE(口語名稱, 交易日期, 作物名稱, 市場名稱)
)
""")
conn.commit()
print("成功讀取菜品主檔！")

market = "台北一"

# 只抓最近4天（今天往前推），民國年 = 西元年 - 1911
today = datetime.today()
start_date = f"{today.year - 1911}.{(today - timedelta(days=4)).strftime('%m.%d')}"
end_date = f"{today.year - 1911}.{today.strftime('%m.%d')}"

new_count = 0
skip_count = 0

for _, row in df.iterrows():
    chinese_name = row["name_zh"]
    official_name = row["api_name"]

    url = (
        "https://data.moa.gov.tw/Service/OpenData/FromM/FarmTransData.aspx"
        f"?$top=100&$skip=0"
        f"&Market={quote(market)}"
        f"&Crop={quote(str(official_name))}"
        f"&StartDate={start_date}&EndDate={end_date}"
    )

    try:
        response = requests.get(url, timeout=15)
        print(f"{chinese_name}({official_name}) - 狀態碼: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            for item in data:
                try:
                    cursor.execute("""
                        INSERT INTO prices (口語名稱, 交易日期, 作物名稱, 市場名稱, 上價, 中價, 下價, 平均價, 交易量)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        chinese_name, item["交易日期"], item["作物名稱"], item["市場名稱"],
                        item["上價"], item["中價"], item["下價"], item["平均價"], item["交易量"]
                    ))
                    new_count += 1
                except sqlite3.IntegrityError:
                    # 已經存在同一筆資料，跳過
                    skip_count += 1

    except requests.exceptions.RequestException as e:
        print(f"{chinese_name}({official_name}) - 連線失敗，跳過這項: {e}")

conn.commit()
conn.close()
print(f"\n完成！新增 {new_count} 筆資料，略過 {skip_count} 筆重複資料。")
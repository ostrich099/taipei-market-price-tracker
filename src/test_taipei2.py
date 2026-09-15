from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import requests
from urllib.parse import quote
import time

base_dir = Path(__file__).resolve().parent.parent
csv_path = base_dir / "vegetables.csv"
df = pd.read_csv(csv_path)

# 測試最近4天的資料
today = datetime.today()
start_date = f"{today.year - 1911}.{(today - timedelta(days=4)).strftime('%m.%d')}"
end_date = f"{today.year - 1911}.{today.strftime('%m.%d')}"

markets = ["台北一", "台北二"]

print(f"測試期間：{start_date} ~ {end_date}\n")
print(f"{'菜名':<10} {'台北一筆數':<12} {'台北二筆數':<12}")
print("-" * 40)

for _, row in df.iterrows():
    chinese_name = row["name_zh"]
    official_name = row["api_name"]

    result_counts = {}

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
            if response.status_code == 200:
                data = response.json()
                result_counts[market] = len(data)
            else:
                result_counts[market] = f"錯誤({response.status_code})"
        except requests.exceptions.RequestException as e:
            result_counts[market] = "連線失敗"

        time.sleep(0.3)  # 避免對 API 打太快

    print(f"{chinese_name:<10} {str(result_counts.get('台北一', 0)):<12} {str(result_counts.get('台北二', 0)):<12}")

print("\n測試完成！")
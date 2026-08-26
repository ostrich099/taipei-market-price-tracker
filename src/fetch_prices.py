from pathlib import Path
import pandas as pd
import requests
from urllib.parse import quote

# 找到專案根目錄
base_dir = Path(__file__).resolve().parent.parent

# 讀取 vegetables.csv
csv_path = base_dir / "vegetables.csv"
df = pd.read_csv(csv_path)

print("成功讀取菜品主檔！")

market = "台北一"
start_date = "115.08.20"
end_date = "115.08.25"

all_rows = []

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
                all_rows.append({
                    "口語名稱": chinese_name,
                    "交易日期": item["交易日期"],
                    "作物名稱": item["作物名稱"],
                    "市場名稱": item["市場名稱"],
                    "上價": item["上價"],
                    "中價": item["中價"],
                    "下價": item["下價"],
                    "平均價": item["平均價"],
                    "交易量": item["交易量"],
                })
    except requests.exceptions.RequestException as e:
        print(f"{chinese_name}({official_name}) - 連線失敗，跳過這項: {e}")

        
# 存成CSV
result_df = pd.DataFrame(all_rows)
output_path = base_dir / "data" / "prices_raw.csv"
result_df.to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"\n完成！共存了 {len(all_rows)} 筆資料到 {output_path}")
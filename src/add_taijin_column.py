import sqlite3
from pathlib import Path

# 跟 fetch_prices.py 一樣的寫法：因為在 src 裡，要跳兩層才到專案根目錄
base_dir = Path(__file__).resolve().parent.parent
db_path = base_dir / "data" / "prices.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. 檢查欄位是否已存在，避免重複執行時報錯
cursor.execute("PRAGMA table_info(prices)")
columns = [col[1] for col in cursor.fetchall()]

if "平均價_台斤" not in columns:
    cursor.execute("ALTER TABLE prices ADD COLUMN 平均價_台斤 REAL")
    print("已新增欄位：平均價_台斤")
else:
    print("欄位已存在，略過新增")

# 2. 把舊資料的平均價，換算成台斤價並填入
cursor.execute("""
    UPDATE prices
    SET 平均價_台斤 = ROUND(平均價 * 0.6, 2)
    WHERE 平均價 IS NOT NULL
""")
conn.commit()

updated_rows = cursor.rowcount
print(f"已更新 {updated_rows} 筆資料的台斤價")

conn.close()
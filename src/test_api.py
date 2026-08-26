import requests

url = "https://data.moa.gov.tw/Service/OpenData/FromM/FarmTransData.aspx?$top=10&$skip=0&Market=%E5%8F%B0%E5%8C%97%E4%B8%80&Crop=%E7%94%98%E8%97%8D&StartDate=115.08.20&EndDate=115.08.25%"


response = requests.get(url)

print("狀態碼:", response.status_code)
print("---")
data = response.json()


for item in data:
    if "甘藍" in item["作物名稱"]:
        print(item["作物名稱"], item["平均價"])

import json
from datetime import date

# ETF 清單
etfs = [
    {"id": "0050", "name": "0050"},
    {"id": "0051", "name": "0051"},
    {"id": "0056", "name": "0056"},
    {"id": "00713", "name": "00713"},
    {"id": "00878", "name": "00878"},
    {"id": "00900", "name": "00900"},
    {"id": "00918", "name": "00918"},
    {"id": "00919_May", "name": "00919 五月定審版"},
    {"id": "00919_Dec", "name": "00919 十二月定審版"},
    {"id": "00929", "name": "00929"},
]

# 讀取 JSON 檔
with open("etf_dates.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 產生 HTML 表格列
rows = []
for etf in etfs:
    info = data.get(etf["id"], {"deadline": "-", "effective": "-"})
    row = f"""
    <tr>
        <td>{etf["name"]}</td>
        <td>{info.get("deadline", "-")}</td>
        <td>{info.get("effective", "-")}</td>
        <td><a href="http://172.16.8.210/web/etf/{etf['id']}/alpha/diff.html">搶先版</a></td>
        <td><a href="http://172.16.8.210/web/etf/{etf['id']}/beta/diff.html">凌晨版</a></td>
        <td><a href="http://172.16.8.210/web/etf/{etf['id']}/prod/diff.html">正式版</a></td>
    </tr>
    """
    rows.append(row)

# HTML 模板
html_template = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{
    font-family: "微軟正黑體", sans-serif;
    background-color: #f9f9f9;
    margin: 40px;
}}
h2 {{
    text-align: center;
    color: #0070C0;
    font-weight: bold;
    font-size: 24pt;
    margin-bottom: 30px;
}}
table {{
    border-collapse: collapse;
    width: 90%;
    margin: 0 auto;
    background-color: #ffffff;
    box-shadow: 0 0 12px rgba(0,0,0,0.1);
}}
th, td {{
    border: 1px solid #cccccc;
    padding: 12px;
    font-size: 14pt;
    text-align: center;
}}
th {{
    background-color: #FFE599;
    color: #000000;
    font-size: 16pt;
    font-weight: bold;
}}
a {{
    color: #0070C0;
    text-decoration: none;
    font-weight: bold;
}}
a:hover {{
    text-decoration: underline;
    color: #005292;
}}
.top-left-button {{
    position: absolute;
    top: 10px;
    left: 10px;
    font-size: 10pt;
    background-color: #eeeeee;
    color: #0070C0;
    padding: 4px 8px;
    border-radius: 4px;
    text-decoration: none;
    border: 1px solid #cccccc;
    opacity: 0.7;
}}
.top-left-button:hover {{
    opacity: 1.0;
    background-color: #dddddd;
}}
</style>
</head>
<body>
<a class="top-left-button" href="http://172.16.8.210/web/etf/statistics/"></a>
<h2>ETF 機率日報表首頁</h2>

<table>
<tr>
    <th>ETF</th>
    <th>資料截止日</th>
    <th>生效日</th>
    <th>搶先版</th>
    <th>凌晨版</th>
    <th>正式版</th>
</tr>
{''.join(rows)}
</table>

</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)

print("已更新 index.html（已移除即時股價）")
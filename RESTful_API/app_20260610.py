"""
ETF RESTful API Server
提供 ETF 報告查詢、CSV 上傳、調整期狀態等端點。
啟動指令：nohup python3 ./RESTful_API/app.py > ./RESTful_API/output.log 2>&1 &
"""

from flask import Flask, request, jsonify
from datetime import datetime
import os
import json
import re
import csv
import io
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允許跨來源請求（前端開發環境使用）

# 報告檔案根目錄；路徑驗證以此為基準，防止路徑穿越攻擊
BASE_DIR = "/var/www/html/web/etf"
verStr = "prod"  # 報告目錄版本子路徑，切換測試環境時改此值

UPLOAD_FOLDER      = '/home/webuser/etf/showdown_csv/'
UPLOAD_TIMES_PATH  = '/var/www/html/web/etf/home/upload_times.json'
ETF_DATES_PATH     = '/home/webuser/etf/etf_calculator/report_generator/dateData/etf_dates.json'
ADJUST_PERIODS_PATH = '/home/webuser/etf/etf_calculator/etfDbImporter/adjust_periods.json'

TARGET_ETF_LIST = {
    '0050', 
    '0051', 
    '0056', 
    '00713', 
    '00878', 
    '00900', 
    '00918',
    '00919_May', 
    '00919_Dec', 
    '00929'
}

REQUIRED_COLUMNS = {'etf_code', 'stock_code', 'stock_name', 'action'}
VALID_ACTIONS = {'addition', 'deletion'}

# 00919 依半年度分成兩份報告檔，以月份區間決定使用哪一份
FEBRUARY = 2
AUGUST   = 8


def check_etf_id(etf_id, date_str):
    """將特殊 ETF（00919）依查詢日期映射至對應的半年度子資料夾。

    00919 每年有兩個調整週期：
      - 2月 ~ 7月 → 00919_May（五月調整版）
      - 8月 ~ 隔年1月 → 00919_Dec（十二月調整版）
    其餘 ETF 直接回傳原 ID。
    """
    if str(etf_id) == "00919":
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        month = date_obj.month
        if FEBRUARY <= month < AUGUST:
            etf_id = "00919_May"
        else:
            etf_id = "00919_Dec"
    return etf_id


def is_valid_date(date_str):
    """檢查日期字串是否合法：格式須為 YYYY-MM-DD，且不得為未來日期。"""
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return False
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return False
    # 未來日期尚無報告資料，直接拒絕
    if date_obj > datetime.today().date():
        return False
    return True

@app.route("/etf_report/<etf_id>", methods=["GET"])
def get_etf_report(etf_id):
    """回傳指定 ETF 在特定日期的 baseline 報告。

    Query param:
      date (str): 查詢日期，格式 YYYY-MM-DD。
    回傳報告 JSON 中的 "baseline" 區塊。
    """
    date = request.args.get("date")

    if not date:
        return jsonify({"status": "error", "message": "Missing 'date' parameter"}), 400

    if not is_valid_date(date):
        return jsonify({"status": "error", "message": "Invalid 'date' format. Use YYYY-MM-DD."}), 400

    try:
        etf_id = check_etf_id(etf_id, date)
        file_path = os.path.join(BASE_DIR, etf_id, verStr, f"{date}.json")

        # 防止 etf_id 夾帶 "../" 等路徑穿越序列
        if not os.path.realpath(file_path).startswith(os.path.realpath(BASE_DIR)):
            return jsonify({"status": "error", "message": "Access denied."}), 403

        if not os.path.exists(file_path):
            return jsonify({
                "status": "error",
                "message": f"No data found for ETF {etf_id} on {date}"
            }), 404

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return jsonify({"status": "success", "data": data.get("baseline", {})})

    except json.JSONDecodeError as e:
        return jsonify({"status": "error", "message": f"Invalid JSON format: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": f"Unexpected server error: {str(e)}"}), 500


@app.route("/api/upload_times", methods=["GET"])
def get_upload_times():
    """回傳本次調整期間內有效的 ETF 上傳時間。
    需同時滿足：今天在調整期內，且 upload_time 本身也落在本次調整期區間。
    """
    try:
        with open(UPLOAD_TIMES_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return jsonify({}), 200

    try:
        with open(ADJUST_PERIODS_PATH, 'r', encoding='utf-8') as f:
            periods = json.load(f)
    except Exception:
        return jsonify({}), 200

    today = datetime.today().date()
    filtered = {}
    for etf_id, upload_time in data.items():
        if etf_id not in periods:
            continue
        try:
            adj_begin   = datetime.strptime(periods[etf_id]['adjust_begin'], '%Y-%m-%d').date()
            adj_end     = datetime.strptime(periods[etf_id]['adjust_end'],   '%Y-%m-%d').date()
            upload_date = datetime.strptime(upload_time, '%Y-%m-%d %H:%M:%S').date()
            if adj_begin <= today <= adj_end and adj_begin <= upload_date <= adj_end:
                filtered[etf_id] = upload_time
        except Exception:
            continue

    return jsonify(filtered)


@app.route("/api/etf_adjust_status", methods=["GET"])
def get_etf_adjust_status():
    """回傳各 ETF 的調整期狀態。

    判斷條件：adjust_begin < today <= adjust_end 為 in_period=True。
    單筆資料格式錯誤時跳過該筆，不影響其他 ETF 的結果。
    """
    try:
        with open(ADJUST_PERIODS_PATH, 'r', encoding='utf-8') as f:
            periods = json.load(f)
    except Exception:
        return jsonify({}), 200

    try:
        with open(UPLOAD_TIMES_PATH, 'r', encoding='utf-8') as f:
            upload_times = json.load(f)
    except Exception:
        upload_times = {}

    today = datetime.today().date()
    result = {}
    for etf_id, info in periods.items():
        try:
            adj_begin = datetime.strptime(info['adjust_begin'], '%Y-%m-%d').date()
            adj_end   = datetime.strptime(info['adjust_end'],   '%Y-%m-%d').date()
            in_period = adj_begin <= today <= adj_end

            uploaded_in_period = False
            if in_period and etf_id in upload_times:
                try:
                    upload_date = datetime.strptime(upload_times[etf_id], '%Y-%m-%d %H:%M:%S').date()
                    uploaded_in_period = adj_begin <= upload_date <= adj_end
                except Exception:
                    pass

            result[etf_id] = {
                'in_period':          in_period,
                'adjust_begin':       info['adjust_begin'],
                'adjust_end':         info['adjust_end'],
                'uploaded_in_period': uploaded_in_period,
            }
        except Exception:
            continue
    return jsonify(result)


@app.route("/api/etf_dates", methods=["GET"])
def get_etf_dates():
    """回傳外部 etf_dates.json 內容給前端"""
    try:
        with open(ETF_DATES_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/sample_csv/<etf_id>", methods=["GET"])
def download_sample_csv(etf_id):
    """產生指定 ETF 的範例 CSV（生效日預填，供使用者對照格式）"""
    from flask import Response

    etf_code = etf_id  # etf_code 須與 TARGET_ETF_LIST 一致（00919_May / 00919_Dec 保留後綴）

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['etf_code', 'stock_code', 'stock_name', 'action', 'estimated_shares'])
    writer.writerow([etf_code, '2892', '第一金', 'addition', ''])
    writer.writerow([etf_code, '1402', '遠東新', 'deletion', ''])

    return Response(
        '﻿' + output.getvalue(),  # UTF-8 BOM，確保 Excel 開啟不亂碼
        mimetype='text/csv; charset=utf-8-sig',
        headers={'Content-Disposition': f'attachment; filename=sample_{etf_code}.csv'}
    )


@app.route("/api/upload_csv", methods=["POST"])
def upload_csv():
    """接收前端上傳的 CSV 並儲存至 UPLOAD_FOLDER。

    Form fields:
      file     (FileStorage): 必須為 .csv，編碼 UTF-8 / UTF-8 BOM。
      etfName  (str): ETF 顯示名稱，作為檔名使用。
      etfId    (str): ETF 代碼，用於更新 upload_times.json。

    成功後同時寫入主檔（覆蓋）與帶時間戳的備份檔。
    """
    # 1. 檢查必要欄位是否齊全
    if 'file' not in request.files:
        return jsonify({"error": "沒有找到檔案"}), 400

    file     = request.files['file']
    etf_name = request.form.get('etfName', '').strip()
    etf_id   = request.form.get('etfId',   '').strip()

    if file.filename == '':
        return jsonify({"error": "沒有選擇檔案"}), 400
    if not etf_name:
        return jsonify({"error": "缺少 ETF 名稱"}), 400

    # 2. 限制副檔名，避免上傳非 CSV 檔案
    if not file.filename.lower().endswith('.csv'):
        return jsonify({"error": "只允許上傳 CSV 檔案"}), 400

    # 3. 讀取內容並驗證必要欄位（支援 Excel 存出的 UTF-8 BOM 格式）
    try:
        content = file.read()
        reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            return jsonify({"error": f"CSV 缺少必要欄位：{', '.join(sorted(missing))}"}), 400
    except UnicodeDecodeError:
        return jsonify({"error": "CSV 編碼錯誤，請使用 UTF-8 編碼"}), 400
    except Exception as e:
        return jsonify({"error": f"CSV 解析失敗：{str(e)}"}), 400

    # 4. 逐 row 驗證欄位值
    try:
        reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
        invalid_codes, invalid_actions = set(), set()
        for row in reader:
            code   = (row.get('etf_code') or '').strip()
            action = (row.get('action')   or '').strip()

            if code not in TARGET_ETF_LIST:
                invalid_codes.add(code)
            if action not in VALID_ACTIONS:
                invalid_actions.add(action)

        errors = []
        if invalid_codes:
            errors.append(f"不允許的 etf_code：{', '.join(sorted(invalid_codes))}")
        if invalid_actions:
            errors.append(f"無效的 action（須為 addition 或 deletion）：{', '.join(sorted(invalid_actions))}")
        if errors:
            return jsonify({"error": "；".join(errors) + "，請確認後重新上傳。"}), 400
    except Exception as e:
        return jsonify({"error": f"資料驗證失敗：{str(e)}"}), 400

    # 5. 確保儲存目錄存在
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 主檔：覆蓋最新版本，供下游程式直接讀取
        with open(os.path.join(UPLOAD_FOLDER, f"{etf_id}.csv"), "wb") as f:
            f.write(content)

        # 備份檔：保留歷史版本供稽核追蹤
        with open(os.path.join(UPLOAD_FOLDER, f"{etf_id}_{timestamp}.csv"), "wb") as f:
            f.write(content)

        # 記錄上傳時間至 upload_times.json（與 etf_dates.json 分離，避免互相覆蓋）
        now = datetime.now()
        last_upload = now.strftime('%Y-%m-%d %H:%M:%S')

        # 計算生效時間提示：7:10 前 → 今日生效；7:10 含後 → 明日生效
        cutoff = now.replace(hour=7, minute=10, second=0, microsecond=0)
        if now < cutoff:
            effective_date = now.strftime('%Y-%m-%d')
        else:
            from datetime import timedelta
            effective_date = (now + timedelta(days=1)).strftime('%Y-%m-%d')
        effective_hint = f"CSV 資料將於 {effective_date} 6:10 後生效"

        try:
            if os.path.exists(UPLOAD_TIMES_PATH):
                with open(UPLOAD_TIMES_PATH, 'r', encoding='utf-8') as f:
                    times_data = json.load(f)
            else:
                times_data = {}
            times_data[etf_id] = last_upload
            with open(UPLOAD_TIMES_PATH, 'w', encoding='utf-8') as f:
                json.dump(times_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 時間記錄失敗不影響檔案已成功儲存的事實

        return jsonify({"message": f"{etf_id} 上傳成功", "last_upload": last_upload,
                        "effective_hint": effective_hint}), 200

    except Exception as e:
        return jsonify({"error": f"存檔失敗: {str(e)}"}), 500

if __name__ == "__main__":
    # 直接執行時啟動開發伺服器；正式環境請透過 nohup 或 systemd 啟動
    app.run(host="0.0.0.0", port=5050, debug=False)

# Kill 已存在 porcess:
# ps -ef | grep app.py | grep -v grep
# kill 545542 574631
# 啟動指令（選擇其中一種）：
#   nohup /var/www/html/web/venv/bin/python3 /var/www/html/web/etf/RESTful_API/app.py > /var/www/html/web/etf/RESTful_API/output.log 2>&1 &
#   nohup python3 ./RESTful_API/app.py > ./RESTful_API/output.log 2>&1 &
#
# 查詢是否在執行：ps -ef | grep app.py
# 測試端點範例：http://172.16.8.210:5050/etf_report/00713?date=2025-07-29

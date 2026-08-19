from flask import Flask, request, jsonify
from datetime import datetime
import os
import json
import re

app = Flask(__name__)

BASE_DIR = "/var/www/html/web/etf"
verStr = "prod"

def get_etf_date(etf_id, date_str, etf_name_list, key = "deadline"):
    json_path = os.path.join(BASE_DIR, "RESTful_API/dateData", str(etf_id) + ".json")
    with open(json_path, "r", encoding="utf-8") as f:
        etf_dates = json.load(f)

    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    year_cur = int(date_obj.year)  # 先取年份
    candidates = etf_name_list
    closest_id = None
    closest_diff = None

    for cid in candidates:
        if cid in etf_dates:
            for year in [year_cur, year_cur + 1]:
                year = str(year)
                if year in etf_dates[cid]:
                    deadline_str = etf_dates[cid][year][key]
                    deadline_date = datetime.fromisoformat(deadline_str).date()
                    diff = (deadline_date - date_obj).days
                    if diff >= 0:  # 只考慮當年度未來的 deadline
                        if closest_diff is None or diff < closest_diff:
                            closest_diff = diff
                            closest_id = cid

    if closest_id is not None:
        return closest_id
    else:
        return etf_id

def check_etf_id(etf_id, date_str):
    if str(etf_id) == "00919":
        etf_id = get_etf_date(etf_id, date_str, ["00919_May", "00919_Dec"])

    return etf_id

def is_valid_date(date_str):
    # 格式
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return False
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return False
    today = datetime.today().date()
    # 不能是未來
    if date_obj > today:
        return False
    return True

@app.route("/etf_report/<etf_id>", methods=["GET"])
def get_etf_report(etf_id):
    date = request.args.get("date")

    if not date:
        return jsonify({
            "status": "error", 
            "message": "Missing 'date' parameter"
        }), 400
    
    if not is_valid_date(date):
        return jsonify({
            "status": "error", 
            "message": "Invalid 'date' format. Use YYYY-MM-DD."
        }), 400

    try:
        etf_id = check_etf_id(etf_id, date)
        file_path = os.path.join(BASE_DIR, etf_id, verStr, f"{date}.json")

        # 預防不合法etf_id (帶路徑)
        if not os.path.realpath(file_path).startswith(os.path.realpath(BASE_DIR)):
            return jsonify({
                "status": "error", 
                "message": "Access denied."
            }), 403

        if not os.path.exists(file_path):
            return jsonify({
                "status": "error",
                "message": f"No data found for ETF {etf_id} on {date}"
            }), 404

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        baseline = data.get("baseline", {})
        return jsonify({
            "status": "success",
            "data": baseline
        })

    except json.JSONDecodeError as e:
        return jsonify({
            "status": "error",
            "message": f"Invalid JSON format: {str(e)}"
        }), 500

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Unexpected server error: {str(e)}"
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)



# nohup python3 ./RESTful_API/app.py > ./RESTful_API/output.log 2>&1 &
# ps -ef | grep app.py
# http://172.16.8.210:5050/etf_report/00713?date=2025-07-29
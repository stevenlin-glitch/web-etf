"""
ETF RESTful API Server
提供 ETF 報告查詢、CSV 上傳、調整期狀態等端點。
啟動指令：nohup python3 ./RESTful_API/app.py > ./RESTful_API/output.log 2>&1 &
"""

from flask import Flask, request, jsonify, send_file
from datetime import datetime, timedelta
import os
import json
import re
import csv
import io
import time
import subprocess
from flask_cors import CORS

app = Flask(__name__)
# 允許跨來源請求（前端開發環境使用）；expose_headers 讓前端 JS 讀得到自訂 header
CORS(app, expose_headers=['X-Data-Warning'])

# 報告檔案根目錄；路徑驗證以此為基準，防止路徑穿越攻擊
BASE_DIR = "/var/www/html/web/etf"
verStr = "prod"  # 報告目錄版本子路徑，切換測試環境時改此值

UPLOAD_FOLDER      = '/home/webuser/etf/showdown_csv/dev/'
UPLOAD_TIMES_PATH  = '/var/www/html/web/etf/home/dev/upload_times.json'
ETF_DATES_PATH     = '/var/www/html/web/etf/home/dev/etf_dates.json'
GENDATEDATA_SH     = '/home/webuser/etf/etf_calculator/dateData/genDateData_dev.sh'
# 使用者手動覆蓋的調整期間；DAO_dev.py 會在算完自動區間後套用這份覆蓋
USER_DATES_PATH    = '/home/webuser/etf/etf_calculator/report_generator/dateData/dev/dates_update_by_user.json'

# 反單策略 CSV（sitcRebalanceTracker）相關路徑
ETF_VENV_PY        = '/home/webuser/etf/venv/bin/python'
TRACKER_PY         = '/home/webuser/etf/etf_calculator/sitcRebalanceTracker/dev/tracker.py'
TRACKER_OUTPUT_DIR = '/home/webuser/etf/etf_calculator/sitcRebalanceTracker/dev/output_csv'
TRACKER_LOG_DIR = '/home/webuser/etf/etf_calculator/sitcRebalanceTracker/dev/logs'
TRADING_DAYS_PY    = '/home/webuser/etf/etf_calculator/dateData/src/TradingDaysRange.py'

# tracker DAO._warnIfDailyDataMissing 的 warning 標記；DAO.py 改訊息文字時須同步
DAILY_DATA_WARNING_MARK = '(休市或 DB 尚未匯入?)'

# 當日反向單 CSV 的開放時間（小時，24 制）。這個時間之前不提供「今天」的 CSV，
# 因為當日盤後資料大概率還沒進 DB。日期選單、下載端點、前端提示文字都用這個值，
# 要調整開放時間只改這裡（前端經 /reverse_csv_dates 的 ready_hour 取得，不另外寫死）。
REVERSE_CSV_READY_HOUR = 22

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

REQUIRED_COLUMNS = {'etf_code', 'stock_code', 'action', 'estimated_shares'}
VALID_ACTIONS = {'addition', 'deletion', 'weight'}

# Debug: 模擬日期／時間（None = 使用系統真實值）；模擬時間為「凍結」語意
_mock_today = None  # type: date | None  (from datetime module)
_mock_time  = None  # type: time | None  (from datetime module)

# 啟動時從 upload_times.json 還原 mock date / mock time（若有對應欄位）
try:
    if os.path.exists(UPLOAD_TIMES_PATH):
        with open(UPLOAD_TIMES_PATH, 'r', encoding='utf-8') as _f:
            _startup_times = json.load(_f)
        _today_str = _startup_times.get('today')
        if _today_str:
            _mock_today = datetime.strptime(_today_str, '%Y-%m-%d').date()
        _time_str = _startup_times.get('mock_time')
        if _time_str:
            _mock_time = datetime.strptime(_time_str, '%H:%M').time()
except Exception:
    pass


def get_today():
    """回傳模擬日期（debug 模式）或真實系統日期。"""
    from datetime import date as _date
    return _mock_today if _mock_today is not None else datetime.today().date()


def get_now():
    """回傳模擬的 datetime（debug 模式）或真實 now。

    日期與時間可分別模擬：
      - 只設日期：模擬日期 + 真實時鐘（原行為）
      - 有設時間：時間凍結在設定的 HH:MM:00，不隨真實時鐘前進
    """
    real = datetime.now()
    d = _mock_today if _mock_today is not None else real.date()
    if _mock_time is not None:
        return datetime.combine(d, _mock_time)
    return real.replace(year=d.year, month=d.month, day=d.day)

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
    if date_obj > get_today():
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


@app.route("/api_dev/upload_times", methods=["GET"])
def get_upload_times():
    """回傳本次可上傳期間內有效的 ETF 上傳時間。
    需同時滿足：今天在可上傳期間內（adj_begin ~ adjust_end），
    且 upload_time 本身也落在同一區間。
    """
    try:
        with open(UPLOAD_TIMES_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return jsonify({}), 200

    try:
        with open(ETF_DATES_PATH, 'r', encoding='utf-8') as f:
            periods = json.load(f)
    except Exception:
        return jsonify({}), 200

    today = get_today()
    filtered = {}
    for etf_id, upload_time in data.items():
        if etf_id not in periods:
            continue
        try:
            adj_begin    = datetime.strptime(periods[etf_id]['adjust_begin'], '%Y-%m-%d').date()
            adj_end     = datetime.strptime(periods[etf_id]['adjust_end'],       '%Y-%m-%d').date()
            upload_date = datetime.strptime(upload_time, '%Y-%m-%d %H:%M:%S').date()
            if adj_begin <= today <= adj_end and adj_begin <= upload_date <= adj_end:
                filtered[etf_id] = upload_time
        except Exception:
            continue

    return jsonify(filtered)


@app.route("/api_dev/etf_adjust_status", methods=["GET"])
def get_etf_adjust_status():
    """回傳各 ETF 的可上傳期狀態。

    in_period 判斷條件：adjust_begin <= today <= adjust_end。
    uploaded_in_period 判斷條件：upload_time 落在 adjust_begin ~ adjust_end 區間內。
    單筆資料格式錯誤時跳過該筆，不影響其他 ETF 的結果。
    """
    try:
        with open(ETF_DATES_PATH, 'r', encoding='utf-8') as f:
            periods = json.load(f)
    except Exception:
        return jsonify({}), 200

    try:
        with open(UPLOAD_TIMES_PATH, 'r', encoding='utf-8') as f:
            upload_times = json.load(f)
    except Exception:
        upload_times = {}

    today = get_today()
    result = {}
    for etf_id, info in periods.items():
        try:
            adj_begin  = datetime.strptime(info['adjust_begin'], '%Y-%m-%d').date()
            adj_end   = datetime.strptime(info['adjust_end'],       '%Y-%m-%d').date()
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
                'effective_date':     info['adjust_effective'],
                'adjust_begin':       info['adjust_begin'],
                'adjust_end':         info['adjust_end'],
                'uploaded_in_period': uploaded_in_period,
            }
        except Exception:
            continue
    return jsonify(result)


@app.route("/api_dev/etf_dates", methods=["GET"])
def get_etf_dates():
    """回傳外部 etf_dates.json 內容給前端"""
    try:
        with open(ETF_DATES_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api_dev/mock_date", methods=["GET"])
def get_mock_date():
    """回傳目前設定的模擬日期／時間；null 表示使用真實值。"""
    return jsonify({
        "mock_date": str(_mock_today) if _mock_today is not None else None,
        "mock_time": _mock_time.strftime('%H:%M') if _mock_time is not None else None,
    })


@app.route("/api_dev/mock_date", methods=["POST"])
def set_mock_date():
    """設定或清除模擬日期／時間（僅限 dev 環境使用）。

    模擬時間為「凍結」語意：get_now() 固定回傳設定的 HH:MM:00。
    today（日期）有變動時才同步執行 genDateData_dev.sh --from-upload-times
    重新產生 etf_dates.json；只改時間不重算。

    Body JSON:
      date (str | null): YYYY-MM-DD 格式或 null（清除模擬日期）
      time (str | null): HH:MM 格式或 null（清除模擬時間）
    """
    global _mock_today, _mock_time
    body = request.get_json(silent=True) or {}
    date_str = body.get("date")
    time_str = body.get("time")

    try:
        new_today = (datetime.strptime(date_str, '%Y-%m-%d').date()
                     if date_str is not None else None)
    except ValueError:
        return jsonify({"status": "error", "message": "日期格式錯誤，請使用 YYYY-MM-DD"}), 400
    try:
        new_time = (datetime.strptime(time_str, '%H:%M').time()
                    if time_str is not None else None)
    except ValueError:
        return jsonify({"status": "error", "message": "時間格式錯誤，請使用 HH:MM"}), 400

    old_today_str = str(get_today())
    _mock_today = new_today
    _mock_time = new_time
    _write_today_to_upload_times()

    # etf_dates.json 只和日期有關：today 沒變（例如只改時間）就不重算
    if str(get_today()) != old_today_str:
        gen = _run_gendatedata()
    else:
        gen = {"success": True, "skipped": True}

    return jsonify({
        "status": "ok",
        "mock_date": str(_mock_today) if _mock_today is not None else None,
        "mock_time": _mock_time.strftime('%H:%M') if _mock_time is not None else None,
        "gendatedata": gen,
    })


def _run_gendatedata(skip_trading_day_check=False):
    """執行 genDateData_dev.sh --from-upload-times，同步等待完成後回傳結果。

    以 upload_times.json 的 today 重新產生 etf_dates.json；
    today 非交易日時腳本會拒絕更新（returncode != 0）。

    skip_trading_day_check=True 時額外帶 --skip-trading-day-check 跳過該檢查——
    使用者手動修改調整期間必須隨時能立即生效，不能因為今天是假日就不更新。
    """
    args = [GENDATEDATA_SH, "--from-upload-times"]
    if skip_trading_day_check:
        args.append("--skip-trading-day-check")
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "執行超時（>120s）"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def _write_today_to_upload_times():
    """將 get_today() 寫入 upload_times.json 的 'today'；模擬時間寫入／移除 'mock_time'。"""
    try:
        if os.path.exists(UPLOAD_TIMES_PATH):
            with open(UPLOAD_TIMES_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
        data['today'] = str(get_today())
        if _mock_time is not None:
            data['mock_time'] = _mock_time.strftime('%H:%M')
        else:
            data.pop('mock_time', None)
        with open(UPLOAD_TIMES_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _clear_today_from_upload_times():
    """從 upload_times.json 移除 'today' 欄位（清除模擬日期時使用）。"""
    try:
        if os.path.exists(UPLOAD_TIMES_PATH):
            with open(UPLOAD_TIMES_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data.pop('today', None)
            with open(UPLOAD_TIMES_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _get_trading_days(begin_str, end_str):
    """回傳 [begin, end] 區間內的交易日清單（list[str]）；失敗時拋例外。"""
    result = subprocess.run(
        [TRADING_DAYS_PY, begin_str, end_str],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "查詢交易日失敗")
    return json.loads(result.stdout)


def _get_upload_epoch(etf_id):
    """回傳該 ETF 最後上傳 CSV 的真實檔案 mtime（epoch 秒）；讀不到時回傳 0（視所有快取為有效）。

    以 showdown 主檔的 mtime 為準，不用 upload_times.json 的時間字串——
    dev 的 mock date 會讓該字串停在模擬時間，與輸出檔真實 mtime 比對時永遠判定快取有效，
    導致重新上傳後仍下載到舊資料。
    """
    try:
        return os.path.getmtime(os.path.join(UPLOAD_FOLDER, f"{etf_id}.csv"))
    except OSError:
        return 0

def _start_reverse_csv_backfill(etf_id):
    """上傳成功後呼叫：背景回算 adjust_begin ~ 昨天的反單策略 CSV（今天之後交給排程）。

    回傳 dict 描述結果（started / reason / dates），僅供前端顯示參考；
    任何失敗都不影響「上傳本身已成功」的事實，一律不拋例外。
    """
    try:
        with open(ETF_DATES_PATH, 'r', encoding='utf-8') as f:
            periods = json.load(f)
        info = periods.get(etf_id) or {}
        adj_begin = info.get('adjust_begin')
        adj_end   = info.get('adjust_end')
        if not adj_begin or not adj_end:
            return {"started": False, "reason": f"{etf_id} 尚無調整期間資料，跳過回算"}

        yesterday = str(get_today() - timedelta(days=1))
        end = min(yesterday, adj_end)
        if end < adj_begin:
            return {"started": False, "reason": "調整期尚無「昨天以前」的日子，跳過回算"}
        
        days = _get_trading_days(adj_begin, end)
        if not days:
            return {"started": False, "reason": "區間內無交易日，跳過回算"}
        
        # 背景執行不等待；tracker 自身有 log，這裡再兜一層捕捉啟動失敗類錯誤
        os.makedirs(TRACKER_LOG_DIR, exist_ok=True)
        log_path = os.path.join(
            TRACKER_LOG_DIR,
            f"backfill_{etf_id}_{get_now().strftime('%Y%m%d_%H%M%S')}.log")
        with open(log_path, 'ab') as log_f:
            subprocess.Popen(
                [ETF_VENV_PY, TRACKER_PY, '--etf', etf_id, '--dates', ','.join(days)],
                stdout=log_f,
                stderr=subprocess.STDOUT,
            )
        return {"started": True, "dates": days}
    except Exception as e:
        return {"started": False, "reason": str(e)}


# =========================================================================
# 調整期間手動修改（dates_update_by_user.json）
# =========================================================================

def _parse_iso_date(value):
    """把 YYYY-MM-DD 字串轉成 date；格式錯或非合法日期回 None。

    不沿用 is_valid_date()——那支會一併拒絕未來日期，
    而調整期間本來就常常是未來日期（例如 0050 的 2026-09-18）。
    """
    if not isinstance(value, str) or not re.match(r'^\d{4}-\d{2}-\d{2}$', value):
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def _has_showdown_csv(etf_id):
    """該 ETF 是否有 tracker 認得、且檔名日期落在本期調整期間內的 showdown CSV。

    regex 與期間過濾規則必須與 tracker.py 的 findLatestShowdownCsv 一致，
    否則會出現「API 判定有 CSV 但 tracker 找不到」的落差。
    期間比對用檔名日期不用 mtime，理由同 tracker（mock date 的時間基準）。
    """
    try:
        with open(ETF_DATES_PATH, 'r', encoding='utf-8') as f:
            info = json.load(f).get(etf_id) or {}
    except Exception:
        return False
    begin = info.get('adjust_begin')
    end   = info.get('adjust_end')
    if not begin or not end:
        return False
    begin8, end8 = begin.replace('-', ''), end.replace('-', '')
    pattern = re.compile(rf'^{re.escape(etf_id)}_(\d{{8}})(_\d{{6}})?\.csv$')
    try:
        for name in os.listdir(UPLOAD_FOLDER):
            m = pattern.match(name)
            if m and begin8 <= m.group(1) <= end8:
                return True
        return False
    except OSError:
        return False


def _validate_adjust_period(begin, end):
    """驗證使用者填的調整期間；通過回 None，否則回錯誤訊息字串（直接給前端顯示）。"""
    beginDate = _parse_iso_date(begin)
    endDate   = _parse_iso_date(end)
    if beginDate is None or endDate is None:
        return "日期格式錯誤，須為 YYYY-MM-DD"
    if beginDate > endDate:
        return f"開始日不能晚於調整期結束日 {end}"
    try:
        if not _get_trading_days(begin, end):
            return f"{begin} ~ {end} 區間內沒有交易日"
    except subprocess.TimeoutExpired:
        return "查詢交易日超時（>60s）"
    except Exception as e:
        return f"查詢交易日失敗：{e}"
    return None


def _read_user_dates():
    """讀 dates_update_by_user.json；檔案不存在回 {}。

    內容毀損時直接拋 JSONDecodeError——寧可整支失敗，也不要用空 dict 覆寫壞檔，
    那會把其他 ETF 既有的覆蓋值一起清掉。
    """
    if not os.path.exists(USER_DATES_PATH):
        return {}
    with open(USER_DATES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def _write_user_dates(data):
    """寫回 dates_update_by_user.json，維持原檔的 4 空格縮排與中文原樣輸出。"""
    with open(USER_DATES_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def _post_adjust_period_refresh(etf_id):
    """調整期間變更後重算該 ETF 的反向單 CSV；回傳 dict 描述結果，不拋例外。

    tracker 的累計欄位（累計調整張／累計調整進度）從 adjust_begin 起累加，
    adjust_begin 一改，同一天的 CSV 內容就跟著變。backfill 只回算到「昨天」，
    今天那份得靠下載時重算，所以要先把今天的快取檔刪掉讓它失效
    （固定檔名檔而已，時間戳備份保留）。
    """
    if not _has_showdown_csv(etf_id):
        return {"started": False, "reason": f"{etf_id} 沒有 showdown CSV，跳過重算"}

    todayCsv = os.path.join(TRACKER_OUTPUT_DIR, etf_id, f"{etf_id}_{get_today()}.csv")
    try:
        os.remove(todayCsv)
    except OSError:
        pass  # 本來就沒有，或已被清掉

    return _start_reverse_csv_backfill(etf_id)


def _apply_adjust_period_change(etf_id, new_entry):
    """寫入覆蓋 → 重算 etf_dates → 重算反向單 CSV。回傳 (body, http_status)。

    genDateData 失敗時把 dates_update_by_user.json 還原回呼叫前的內容：
    否則畫面沒更新但覆蓋值已經落地，隔天早上排程一跑會突然套上去，
    使用者當下以為「沒存成功」，結果隔天自己變了。
    """
    try:
        old = _read_user_dates()
    except Exception as e:
        return {"status": "error",
                "message": f"dates_update_by_user.json 讀取失敗：{e}"}, 500

    new = dict(old)          # entry 是整個替換，不是就地修改，淺拷貝即可
    new[etf_id] = new_entry
    try:
        _write_user_dates(new)
    except Exception as e:
        return {"status": "error",
                "message": f"dates_update_by_user.json 寫入失敗：{e}"}, 500

    gen = _run_gendatedata(skip_trading_day_check=True)
    if not gen.get("success"):
        try:
            _write_user_dates(old)
        except Exception as e:
            return {"status": "error",
                    "message": f"重算 etf_dates 失敗，且還原 dates_update_by_user.json 也失敗：{e}",
                    "gendatedata": gen}, 500
        detail = ((gen.get("stdout") or '') + (gen.get("stderr") or '')
                  + (gen.get("message") or '')).strip()
        return {"status": "error",
                "message": "重算 etf_dates 失敗，修改已還原",
                "detail": detail[-2000:],
                "gendatedata": gen}, 500

    backfill = _post_adjust_period_refresh(etf_id)

    # 讀回實際生效的區間：清除覆蓋時前端才拿得到自動計算回來的值。
    # 讀失敗不影響成功狀態——檔案已寫、gen 已跑完，前端還會再打一次 /api_dev/etf_dates。
    applied = {}
    try:
        with open(ETF_DATES_PATH, 'r', encoding='utf-8') as f:
            applied = json.load(f).get(etf_id) or {}
    except Exception:
        pass

    return {
        "status":       "ok",
        "etf_id":       etf_id,
        "adjust_begin": applied.get("adjust_begin"),
        "adjust_end":   applied.get("adjust_end"),
        "gendatedata":  gen,
        "backfill":     backfill,
    }, 200


@app.route("/api_dev/adjust_period/<etf_id>", methods=["POST"])
def set_adjust_period(etf_id):
    """手動指定該 ETF 調整期間的開始日，立即重算 etf_dates.json 與反向單 CSV。

    Body JSON:
      adjust_begin (str): YYYY-MM-DD
    adjust_end 不由使用者指定——固定用 DAO 自動計算的現值。這裡把它一起寫進覆蓋檔，
    純粹當作「這筆覆蓋屬於哪一期」的到期標記，DAO_dev.py 會在 today 超過它時自動清除。
    """
    if etf_id not in TARGET_ETF_LIST:
        return jsonify({"status": "error", "message": f"未知的 ETF：{etf_id}"}), 400

    payload = request.get_json(silent=True) or {}
    begin   = payload.get("adjust_begin")
    if not begin:
        return jsonify({"status": "error",
                        "message": "請填寫調整期間的開始日"}), 400

    # 結束日一律取自動計算的現值，忽略 body 帶進來的 adjust_end
    try:
        with open(ETF_DATES_PATH, 'r', encoding='utf-8') as f:
            end = (json.load(f).get(etf_id) or {}).get('adjust_end')
    except Exception as e:
        return jsonify({"status": "error",
                        "message": f"讀取 etf_dates.json 失敗：{e}"}), 500
    if not end:
        return jsonify({"status": "error",
                        "message": f"{etf_id} 目前沒有調整期間，無法設定開始日"}), 400

    # 已結束的調整期不接受設定：寫進去也會被 DAO 立刻判為過期清掉
    endDate = _parse_iso_date(end)
    if endDate is not None and endDate < get_today():
        return jsonify({"status": "error",
                        "message": f"{etf_id} 的調整期已於 {end} 結束，無法設定"}), 400

    error = _validate_adjust_period(begin, end)
    if error:
        return jsonify({"status": "error", "message": error}), 400

    respBody, status = _apply_adjust_period_change(
        etf_id, {"adjust_begin": begin, "adjust_end": end})
    return jsonify(respBody), status


@app.route("/api_dev/adjust_period/<etf_id>", methods=["DELETE"])
def clear_adjust_period(etf_id):
    """清除該 ETF 的調整期間覆蓋，回到 DAO_dev.py 自動計算的結果。"""
    if etf_id not in TARGET_ETF_LIST:
        return jsonify({"status": "error", "message": f"未知的 ETF：{etf_id}"}), 400

    respBody, status = _apply_adjust_period_change(etf_id, {})
    return jsonify(respBody), status


@app.route("/api_dev/sample_csv/<etf_id>", methods=["GET"])
def download_sample_csv(etf_id):
    """產生指定 ETF 的範例 CSV（生效日預填，供使用者對照格式）"""
    from flask import Response

    etf_code = etf_id  # etf_code 須與 TARGET_ETF_LIST 一致（00919_May / 00919_Dec 保留後綴）

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['etf_code', 'stock_code', 'action', 'estimated_shares'])
    writer.writerow([etf_code, '2892', 'addition', '1000'])
    writer.writerow([etf_code, '1402', 'deletion', '-1000'])
    writer.writerow([etf_code, '2330', 'weight', '0'])

    return Response(
        '﻿' + output.getvalue(),  # UTF-8 BOM，確保 Excel 開啟不亂碼
        mimetype='text/csv; charset=utf-8-sig',
        headers={'Content-Disposition': f'attachment; filename=sample_{etf_code}.csv'}
    )


@app.route("/api_dev/upload_csv", methods=["POST"])
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
            return jsonify({"error": "資料格式有誤", "details": [
                {"row": None, "errors": [f"CSV 缺少必要欄位：{', '.join(sorted(missing))}"]}
            ]}), 400
    except UnicodeDecodeError:
        return jsonify({"error": "資料格式有誤", "details": [
            {"row": None, "errors": ["CSV 編碼錯誤，請使用 UTF-8 編碼"]}
        ]}), 400
    except Exception as e:
        return jsonify({"error": "資料格式有誤", "details": [
            {"row": None, "errors": [f"CSV 解析失敗：{str(e)}"]}
        ]}), 400

    # 4. 逐 row 驗證欄位值，所有錯誤依行號分組
    try:
        reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
        row_errors = {}  # {row_num: [error_message, ...]}
        for i, row in enumerate(reader, start=2):  # 第 1 行為標題，資料從第 2 行起
            errs = []
            code   = (row.get('etf_code') or '').strip()
            action = (row.get('action')   or '').strip()

            if code != etf_id:
                errs.append(f"etf_code {code!r} 與上傳目標 {etf_id!r} 不符")
            if action not in VALID_ACTIONS:
                errs.append(f"無效的 action：{action}（須為 addition、deletion 或 weight）")

            shares_raw = (row.get('estimated_shares') or '').strip()
            if not shares_raw:
                errs.append("estimated_shares 不可為空值")
            else:
                try:
                    shares_val = float(shares_raw)
                    if action != 'weight':
                        if shares_val == 0:
                            errs.append("action 為 addition 或 delection 時，estimated_shares 不可為 0")
                        elif action == 'addition' and shares_val < 0:
                            errs.append("action 為 addition，estimated_shares 須為正數")
                        elif action == 'deletion' and shares_val > 0:
                            errs.append("action 為 deletion，estimated_shares 須為負數")
                except ValueError:
                    errs.append(f"estimated_shares 非有效數字（{shares_raw!r}）")

            if errs:
                row_errors[i] = errs

        if row_errors:
            details = [{"row": r, "errors": e} for r, e in sorted(row_errors.items())]
            return jsonify({"error": "資料格式有誤", "details": details}), 400
    except Exception as e:
        return jsonify({"error": "資料格式有誤", "details": [
            {"row": None, "errors": [f"資料驗證失敗：{str(e)}"]}
        ]}), 400

    # 5. 確保儲存目錄存在
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    try:
        timestamp = get_now().strftime('%Y%m%d_%H%M%S')

        # 主檔：覆蓋最新版本，供下游程式直接讀取
        with open(os.path.join(UPLOAD_FOLDER, f"{etf_id}.csv"), "wb") as f:
            f.write(content)

        # 備份檔：保留歷史版本供稽核追蹤
        with open(os.path.join(UPLOAD_FOLDER, f"{etf_id}_{timestamp}.csv"), "wb") as f:
            f.write(content)

        # 記錄上傳時間至 upload_times.json（與 etf_dates.json 分離，避免互相覆蓋）
        now = get_now()
        last_upload = now.strftime('%Y-%m-%d %H:%M:%S')

        # 計算生效時間提示：7:10 前 → 今日生效；7:10 含後 → 明日生效
        cutoff = now.replace(hour=7, minute=10, second=0, microsecond=0)
        if now < cutoff:
            effective_date = now.strftime('%Y-%m-%d')
        else:
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
        
        backfill = _start_reverse_csv_backfill(etf_id)

        return jsonify({"message": f"{etf_id} 上傳成功", "last_upload": last_upload,
                        "effective_hint": effective_hint, "backfill": backfill}), 200

    except Exception as e:
        return jsonify({"error": f"存檔失敗: {str(e)}"}), 500

@app.route("/api_dev/reverse_csv_dates/<etf_id>", methods=["GET"])
def get_reverse_csv_dates(etf_id):
    """回傳指定 ETF 可選的反單策略 CSV 日期：[adjust_begin, today] 內的所有交易日。"""
    if etf_id not in TARGET_ETF_LIST:
        return jsonify({"status": "error", "message": f"未知的 ETF：{etf_id}"}), 400

    try:
        with open(ETF_DATES_PATH, 'r', encoding='utf-8') as f:
            periods = json.load(f)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    info = periods.get(etf_id) or {}
    adj_begin = info.get('adjust_begin')
    adj_end   = info.get('adjust_end')
    if not adj_begin or not adj_end:
        return jsonify({"status": "error", "message": f"{etf_id} 尚無調整期間資料"}), 404

    # ISO 日期字串可直接比大小；today 超出調整期時以 adjust_end 為上限
    end = min(str(get_today()), adj_end)
    if end < adj_begin:
        return jsonify({"dates": []})

    try:
        days = _get_trading_days(adj_begin, end)
        # REVERSE_CSV_READY_HOUR 前不提供「今天」：當日盤後資料大概率尚未進 DB。
        # ready_hour 一併回給前端，讓提示文字不用另外寫死時間。
        today_str = str(get_today())
        resp = {"dates": days, "ready_hour": REVERSE_CSV_READY_HOUR}
        if today_str in days and get_now().hour < REVERSE_CSV_READY_HOUR:
            resp["dates"] = [d for d in days if d != today_str]
            resp["today_blocked"] = today_str
        return jsonify(resp)
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "查詢交易日超時（>60s）"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api_dev/reverse_csv/<etf_id>", methods=["GET"])
def download_reverse_csv(etf_id):
    """下載指定 ETF 在指定日期的反單策略 CSV。

    先找 output_csv 現成檔（上傳回算或排程產出）直接回傳；
    檔案不存在、或比該 ETF 最後上傳時間舊（交易員重傳過）時，
    才重跑 tracker.py 現算後回傳。
    Query param:
      date (str): 目標日期 YYYY-MM-DD。
    """
    if etf_id not in TARGET_ETF_LIST:
        return jsonify({"status": "error", "message": f"未知的 ETF：{etf_id}"}), 400

    date_str = request.args.get("date", "")
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return jsonify({"status": "error", "message": "date 格式錯誤，須為 YYYY-MM-DD"}), 400

    # 與日期選單規則一致：REVERSE_CSV_READY_HOUR 前不提供「今天」的反向單 CSV
    if date_str == str(get_today()) and get_now().hour < REVERSE_CSV_READY_HOUR:
        return jsonify({"status": "error",
                        "message": f"{REVERSE_CSV_READY_HOUR}:00 前不提供 {date_str} 的反向單CSV"}), 403

    # tracker 輸出在 output_csv/{etf_id}/ 子資料夾（固定檔名版，時間戳檔為歷史備份）
    out_path = os.path.join(TRACKER_OUTPUT_DIR, etf_id, f"{etf_id}_{date_str}.csv")

    # 檔案存在、且不早於該 ETF 最後上傳時間（重傳過就視為過期，走重算）
    if os.path.exists(out_path) and os.path.getmtime(out_path) >= _get_upload_epoch(etf_id):
        return send_file(out_path, as_attachment=True,
                         download_name=f"{etf_id}_{date_str}.csv",
                         mimetype='text/csv')

    started = time.time()
    try:
        result = subprocess.run(
            [ETF_VENV_PY, TRACKER_PY, "--etf", etf_id, "--date", date_str],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "產生反單策略 CSV 超時（>300s）"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    # tracker 失敗時不會產檔（或只留舊檔），用 mtime 確認這次真的有重新產出
    if (result.returncode != 0 or not os.path.exists(out_path)
            or os.path.getmtime(out_path) < started - 1):
        detail = ((result.stdout or '') + (result.stderr or '')).strip()
        return jsonify({"status": "error",
                        "message": "產生反單策略 CSV 失敗",
                        "detail": detail[-2000:]}), 500

    resp = send_file(out_path, as_attachment=True,
                     download_name=f"{etf_id}_{date_str}.csv",
                     mimetype='text/csv')
    # 這次執行的輸出若含「當日資料整批為空」的 warning（tracker logging 走 stderr），
    # 以自訂 header 通知前端：檔案照給，但內容可能缺當日資料
    if DAILY_DATA_WARNING_MARK in (result.stdout or '') + (result.stderr or ''):
        resp.headers['X-Data-Warning'] = '1'
    return resp


@app.route("/api_dev/run_db_importer", methods=["POST"])
def run_db_importer():
    """執行 etfDbImporter.py --from-upload-times，同步等待完成後回傳結果。"""
    try:
        result = subprocess.run(
            [
                "/home/webuser/etf/venv/bin/python",
                "/home/webuser/etf/etf_calculator/etfDbImporter/dev/etfDbImporter.py",
                "--from-upload-times",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        return jsonify({
            "status": "success" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        })
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "執行超時（>300s）"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    # 直接執行時啟動開發伺服器；正式環境請透過 nohup 或 systemd 啟動
    app.run(host="0.0.0.0", port=5051, debug=False)

# Kill 已存在 porcess:
# ps -ef | grep app_dev.py | grep -v grep
# kill 545542 574631
# 啟動指令（選擇其中一種）：
#   nohup /var/www/html/web/venv/bin/python3 /var/www/html/web/etf/RESTful_API/app_dev.py > /var/www/html/web/etf/RESTful_API/output_dev.log 2>&1 &
#   nohup python3 ./RESTful_API/app_dev.py > ./RESTful_API/output_dev.log 2>&1 &
#
# 查詢是否在執行：ps -ef | grep app_dev.py
# 測試端點範例：http://172.16.8.210:5050/etf_report/00713?date=2025-07-29

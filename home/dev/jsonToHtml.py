import json

# =========================
# ETF 清單
# =========================
NO_UPLOAD_ETFS = {'0050', '0051', '00900'}

etfs = [
    {"id": "0050", "name": "0050"},
    {"id": "0051", "name": "0051"},
    {"id": "0056", "name": "0056"},
    {"id": "00713", "name": "00713"},
    {"id": "00878", "name": "00878"},
    {"id": "00900", "name": "00900"},
    {"id": "00918", "name": "00918"},
    {"id": "00919_May", "name": "00919 \u4e94\u6708\u5b9a\u5be9\u7248"},
    {"id": "00919_Dec", "name": "00919 \u5341\u4e8c\u6708\u5b9a\u5be9\u7248"},
    {"id": "00929", "name": "00929"},
]

# =========================
# \u8b80\u53d6\u65e5\u671f\u8cc7\u8a0a JSON
# =========================
# \u4f7f\u7528\u7d55\u5c0d\u8def\u5f91\uff0c\u907f\u514d\u5f9e\u4e0d\u540c\u76ee\u9304\u57f7\u884c\u6642\u975c\u9ed8\u5931\u6557\u7522\u51fa\u5168 "-" \u7684 HTML
_ETF_DATES_PATH = "/var/www/html/web/etf/home/dev/etf_dates.json"
try:
    with open(_ETF_DATES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    raise SystemExit(f"[\u932f\u8aa4] \u627e\u4e0d\u5230 {_ETF_DATES_PATH}\uff0c\u8acb\u78ba\u8a8d\u8def\u5f91\u5f8c\u518d\u57f7\u884c")

# =========================
# \u7522\u751f table rows\uff08\u7d14\u5b57\u4e32\uff09
# =========================
rows = []
for etf in etfs:
    info = data.get(etf["id"], {"deadline": "-", "effective": "-"})

    if etf["id"] in NO_UPLOAD_ETFS:
        upload_cell = "<td></td>"
        reverse_cell = "<td></td>"
    else:
        upload_cell = (
            '<td>'
            '<button class="upload-btn" data-etf-id="{id}" data-etf-name="{name}">\u4e0a\u50b3 CSV</button>'
            '<br>'
            '<small class="upload-time" data-etf-id="{id}"></small>'
            '<small class="not-in-period" data-etf-id="{id}">\u73fe\u5728\u975e\u8abf\u6574\u671f</small>'
            '</td>'
        ).format(id=etf["id"], name=etf["name"])
        # \u53cd\u5411\u55ae\u4e0b\u8f09\uff1a\u9810\u8a2d disabled\uff0c\u7531 toggleReverseCsvBtn() \u4f9d\u8abf\u6574\u671f\u72c0\u614b\u89e3\u9396
        reverse_cell = (
            '<td>'
            '<button class="reverse-csv-btn" disabled data-etf-id="{id}" data-etf-name="{name}">\u4e0b\u8f09CSV</button>'
            '</td>'
        ).format(id=etf["id"], name=etf["name"])

    # \u8abf\u6574\u671f\u9593\uff1a\u5169\u7aef\u7686\u6709\u503c\u624d\u986f\u793a\u5340\u9593\u8207\u7de8\u8f2f\u6309\u9215
    # \uff0800900 \u5728 DAO_dev.py \u7684 ADJUST_DAYS \u672a\u5b9a\u7fa9\uff0c\u6c38\u9060\u662f null\uff09\u3002
    # \u6309\u9215\u5c0d\u5341\u6a94\u5168\u90e8\u6e32\u67d3\u9032 DOM\uff0c\u53ef\u898b\u6027\u4ea4\u7d66 JS \u5207 display\u2014\u2014
    # \u9019\u6a23\u300c\u6e05\u9664\u8986\u84cb\u300d\u5f8c\u5340\u9593\u6709\u7121\u8b8a\u5316\u90fd\u4e0d\u7528\u91cd\u5efa DOM\u3002
    adj_begin = info.get("adjust_begin")
    adj_end = info.get("adjust_end")
    has_period = bool(adj_begin and adj_end)
    period_cell = (
        '<td class="etf-adjust-period" data-etf-id="{id}">'
        '<span class="period-text" data-etf-id="{id}">{text}</span>'
        '<button class="edit-period-btn" data-etf-id="{id}" data-etf-name="{name}"'
        ' title="\u4fee\u6539\u8abf\u6574\u671f\u9593" style="display:{disp}">&#9998;</button>'
        '</td>'
    ).format(
        id=etf["id"],
        name=etf["name"],
        text="{} ~ {}".format(adj_begin, adj_end) if has_period else "-",
        disp="inline-block" if has_period else "none",
    )

    rows.append("""
        <tr>
            <td>{name}</td>
            <td class="etf-deadline" data-etf-id="{id}">{deadline}</td>
            <td class="etf-effective" data-etf-id="{id}">{effective}</td>
            {period_cell}
            <td><a href="https://ai.uccapital.com.tw/etfdailyreportweb/etf/{id}/alpha/diff.html">\u6436\u5148\u7248</a></td>
            <td><a href="https://ai.uccapital.com.tw/etfdailyreportweb/etf/{id}/beta/diff.html">\u51cc\u6668\u7248</a></td>
            <td><a href="https://ai.uccapital.com.tw/etfdailyreportweb/etf/{id}/prod/diff.html">\u6b63\u5f0f\u7248</a></td>
            <!--<td><a class="immed-link" data-etf-id="{id}">\u5373\u6642\u80a1\u50f9</a></td>-->
            {upload_cell}
            {reverse_cell}
        </tr>
    """.format(
        name=etf["name"],
        id=etf["id"],
        deadline=info.get("deadline", "-"),
        effective=info.get("effective", "-"),
        period_cell=period_cell,
        upload_cell=upload_cell,
        reverse_cell=reverse_cell,
    ))

# =========================
# HTML Template
# =========================
# \u6a21\u677f\u7531\u90e8\u7f72\u7248 index.html \u53cd\u63a8\u800c\u4f86\uff0c\u5df2\u542b\u53cd\u5411\u55ae\u4e0b\u8f09 UI \u8207 debug \u9762\u677f\u5b8c\u6574\u529f\u80fd\u3002
# \u7528 r-string\uff1a\u88e1\u9762 JS \u7684 '\\t' \u7b49\u53cd\u659c\u7dda\u8981\u539f\u6a23\u8f38\u51fa\uff0c\u4e0d\u80fd\u88ab Python \u7576\u8df3\u8131\u5b57\u5143\u5403\u6389\u3002
# \u975e f-string\uff1b{ROWS} \u4ee5 str.replace() \u586b\u5165\u3002
html = r"""<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <style>
        body {
            font-family: "微軟正黑體", sans-serif;
            background-color: #f9f9f9;
            margin: 40px;
        }

        h2 {
            text-align: center;
            color: #0070C0;
            font-size: 24pt;
            margin-bottom: 30px;
        }

        table {
            border-collapse: collapse;
            width: 90%;
            margin: 0 auto;
            background-color: #ffffff;
        }

        th,
        td {
            border: 1px solid #cccccc;
            padding: 12px;
            font-size: 14pt;
            text-align: center;
        }

        th {
            background-color: #FFE599;
            font-size: 16pt;
        }

        a {
            color: #0070C0;
            font-weight: bold;
            text-decoration: none;
        }

        a.disabled {
            color: #999;
            pointer-events: none;
        }

        /* ════ 上傳 CSV 按鈕（表格內）════ */
        .upload-btn {
            padding: 6px 14px;
            background-color: #27ae60;
            color: White;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-family: "微軟正黑體", sans-serif;
            transition: background-color 0.2s;
        }

        .upload-btn:hover {
            background-color: #219a52;
        }

        .upload-btn.not-uploaded {
            background-color: #e74c3c;
        }

        .upload-btn.not-uploaded:hover {
            background-color: #c0392b;
        }

        .upload-btn:disabled {
            background-color: #bdc3c7;
            color: #fff;
            cursor: not-allowed;
            opacity: 0.7;
        }

        /* ════ 下載反向單策略 CSV 按鈕（表格內）════
           可下載（調整期內且已上傳）時藍色，否則反灰 disabled，由 JS 切換 */
        .reverse-csv-btn {
            padding: 6px 14px;
            background-color: #0070C0;
            color: White;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-family: "微軟正黑體", sans-serif;
            transition: background-color 0.2s;
        }

        .reverse-csv-btn:hover {
            background-color: #005A9E;
        }

        .reverse-csv-btn:disabled {
            background-color: #bdc3c7;
            color: #fff;
            cursor: not-allowed;
            opacity: 0.7;
        }

        #reverse-download-btn {
            padding: 10px 24px;
            background-color: #0070C0;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-family: "微軟正黑體", sans-serif;
            transition: background-color 0.2s;
        }

        #reverse-download-btn:hover {
            background-color: #005A9E;
        }

        #reverse-download-btn:disabled {
            background-color: #a0c4e8;
            cursor: not-allowed;
        }

        #reverse-date-select {
            padding: 8px 12px;
            font-size: 14px;
            font-family: "微軟正黑體", sans-serif;
            border: 1px solid #ccc;
            border-radius: 4px;
            min-width: 180px;
        }

        /* 轉圈圈 loading（下載按鈕內） */
        .btn-spinner {
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid rgba(255, 255, 255, 0.4);
            border-top-color: #fff;
            border-radius: 50%;
            animation: btn-spin 0.8s linear infinite;
            vertical-align: -2px;
            margin-right: 6px;
        }

        @keyframes btn-spin {
            to {
                transform: rotate(360deg);
            }
        }

        /* ════ 調整期間欄位（表格內）════ */
        .etf-adjust-period {
            position: relative;
            padding-right: 26px;
            white-space: nowrap;
        }

        .edit-period-btn {
            position: absolute;
            top: 2px;
            right: 2px;
            border: none;
            background: transparent;
            cursor: pointer;
            font-size: 13px;
            line-height: 1;
            padding: 3px;
            color: #7f8c8d;
        }

        .edit-period-btn:hover {
            color: #0070C0;
        }

        .edit-period-btn:disabled {
            color: #ccc;
            cursor: not-allowed;
        }

        /* ════ 調整期間彈窗 ════ */
        /* 結束日欄位隱藏後只剩一個欄位，space-between 會把 label 和輸入框推到彈窗左右兩端，
           改成整組置中並用 gap 控制間距 */
        .period-field {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin: 12px 0;
            font-size: 14px;
        }

        .period-field input[type="date"] {
            font-family: "微軟正黑體", sans-serif;
            font-size: 14px;
            padding: 4px 6px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }

        .period-error {
            color: #e74c3c;
            font-size: 13px;
            min-height: 18px;
            margin: 10px 0 0;
            text-align: left;
            white-space: pre-wrap;
        }

        .period-btn-row {
            margin-top: 18px;
            display: flex;
            gap: 8px;
            justify-content: center;
        }

        .period-btn-row button {
            padding: 8px 18px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-family: "微軟正黑體", sans-serif;
            color: #fff;
        }

        #period-save-btn {
            background-color: #0070C0;
        }

        #period-clear-btn {
            background-color: #e67e22;
        }

        #period-cancel-btn {
            background-color: #95a5a6;
        }

        .period-btn-row button:disabled {
            opacity: 0.55;
            cursor: not-allowed;
        }

        /* ════ Modal 遮罩 ════ */
        /*  display 由 JS 控制，這裡不設 display:flex，
    否則加上 .show 時 opacity transition 不會動  */
        .modal-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .modal-overlay.show {
            opacity: 1;
        }

        /* ════ Modal 彈窗本體 ════ */
        .modal-content {
            background: #fff;
            padding: 30px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
            width: 400px;
            max-width: 90vw;
            position: relative;
            transform: translateY(-20px);
            opacity: 0;
            transition: transform 0.3s ease, opacity 0.3s ease;
        }

        .modal-overlay.show .modal-content {
            transform: translateY(0);
            opacity: 1;
        }

        .modal-close {
            position: absolute;
            top: 12px;
            right: 16px;
            cursor: pointer;
            font-size: 20px;
            font-weight: bold;
            color: #aaa;
            line-height: 1;
        }

        .modal-close:hover {
            color: #000;
        }

        .file-input-wrapper {
            margin: 20px 0;
        }

        #modal-upload-btn {
            padding: 10px 24px;
            background-color: #0070C0;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-family: "微軟正黑體", sans-serif;
            transition: background-color 0.2s;
        }

        #modal-upload-btn:hover {
            background-color: #005A9E;
        }

        #modal-upload-btn:disabled {
            background-color: #a0c4e8;
            cursor: not-allowed;
        }

        #sample-csv-link {
            display: inline-block;
            margin-top: 8px;
            font-size: 12px;
            color: #0070C0;
            text-decoration: underline;
            cursor: pointer;
        }

        .upload-time {
            color: #888;
            font-size: 11px;
            margin-top: 4px;
            display: block;
        }

        .not-in-period {
            color: #999;
            font-size: 11px;
            margin-top: 2px;
            display: none;
        }

        /* ════ 錯誤詳情 hover 標示 ════ */
        .err-detail-badge {
            cursor: help;
            color: #0070C0;
            text-decoration: underline dotted;
            font-size: 11px;
            position: relative;
            display: block;
            margin-top: 2px;
        }

        .err-detail-box {
            display: none;
            position: absolute;
            top: calc(100% + 6px);
            left: 50%;
            transform: translateX(-50%);
            background: #2c2c2c;
            color: #fff;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 11px;
            text-align: left;
            z-index: 9999;
            line-height: 1.8;
            max-width: 380px;
            width: max-content;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }

        .err-detail-badge:hover .err-detail-box {
            display: block;
        }

        /* ════ DEV 模擬日期面板（右下角固定） ════ */
        #debug-panel {
            position: absolute;
            top: 10px;
            right: 20px;
            background: #2c2c2c;
            color: #fff;
            padding: 14px 16px;
            border-radius: 8px;
            z-index: 9999;
            font-size: 13px;
            font-family: "微軟正黑體", monospace, sans-serif;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.5);
            min-width: 240px;
        }

        #debug-panel .debug-title {
            font-size: 12px;
            color: #f0a500;
            font-weight: bold;
            margin-bottom: 8px;
            letter-spacing: 1px;
            margin-right: 24px;
            /* 避開右上角收合按鈕 */
        }

        /* ════ 面板收合／展開 ════ */
        #debug-toggle-btn {
            position: absolute;
            top: 10px;
            right: 12px;
            width: 20px;
            height: 20px;
            padding: 0;
            background: #3a3a3a;
            color: #fff;
            border: 1px solid #555;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            line-height: 1;
        }

        #debug-toggle-btn:hover {
            background: #555;
        }

        #debug-panel.collapsed {
            min-width: 0;
        }

        #debug-panel.collapsed #debug-body {
            display: none;
        }

        #debug-panel.collapsed .debug-title {
            margin-bottom: 0;
        }

        #debug-panel .debug-current {
            font-size: 11px;
            color: #aaa;
            margin-bottom: 8px;
        }

        #debug-panel .debug-current span {
            font-weight: bold;
        }

        /* 模擬日期轉換完成後的高亮（維持 1 秒） */
        #debug-current-date {
            border-radius: 3px;
            padding: 1px 4px;
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        #debug-current-date.flash {
            background-color: #f0a500;
            color: #000 !important;
        }

        #debug-panel .debug-apply-btn:disabled,
        #debug-panel .debug-clear-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        #debug-panel input[type="date"],
        #debug-panel input[type="time"] {
            padding: 4px 6px;
            border-radius: 4px;
            border: 1px solid #555;
            background: #3a3a3a;
            color: #fff;
            font-size: 12px;
            width: 128px;
        }

        /* 中文語系顯示「上午/下午 hh:mm」+ 時鐘圖示，需要比日期框更寬 */
        #debug-panel input[type="time"] {
            width: 150px;
        }

        #debug-panel .debug-apply-btn {
            padding: 4px 10px;
            background: #f0a500;
            color: #000;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-family: "微軟正黑體", sans-serif;
            font-weight: bold;
        }

        #debug-panel .debug-apply-btn:hover {
            background: #d49200;
        }

        #debug-panel .debug-clear-btn {
            padding: 4px 10px;
            background: #555;
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-family: "微軟正黑體", sans-serif;
        }

        #debug-panel .debug-clear-btn:hover {
            background: #777;
        }

        #debug-panel .debug-row {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        #debug-panel .debug-divider {
            border: none;
            border-top: 1px solid #555;
            margin: 10px 0;
        }

        #debug-panel .debug-write-db-btn {
            padding: 4px 10px;
            background: #c0392b;
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-family: "微軟正黑體", sans-serif;
            font-weight: bold;
        }

        #debug-panel .debug-write-db-btn:hover {
            background: #a93226;
        }

        #debug-panel .debug-write-db-btn:disabled {
            background: #555;
            cursor: not-allowed;
        }

        #debug-db-result {
            margin-top: 6px;
            font-size: 11px;
            max-height: 80px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
            display: none;
            line-height: 1.5;
        }
    </style>
</head>

<body>
    <h2>ETF 機率日報表首頁</h2>

    <table>
        <tr>
            <th>ETF</th>
            <th>資料截止日</th>
            <th>生效日</th>
            <th>調整期間</th>
            <th>搶先版</th>
            <th>凌晨版</th>
            <th>正式版</th>
            <!--<th>即時股價</th>-->
            <th>上傳 CSV </th>
            <th>反向單策略</th>
        </tr>
{ROWS}
    </table>

    <!-- DEV ONLY: 模擬日期面板（右下角） -->
    <div id="debug-panel">
        <button id="debug-toggle-btn" title="收合／展開面板">&minus;</button>
        <div class="debug-title">&#9881; DEV 模擬日期／時間</div>
        <div id="debug-body">
            <div class="debug-current">目前：<span id="debug-current-date">真實日期</span></div>
            <div class="debug-row">
                <input type="date" id="debug-date-input">
                <input type="time" id="debug-time-input">
            </div>
            <div class="debug-row" style="margin-top:6px;">
                <button class="debug-apply-btn" id="debug-apply-btn">套用</button>
                <button class="debug-clear-btn" id="debug-clear-btn">清除</button>
            </div>
            <hr class="debug-divider">
            <div class="debug-row">
                <button class="debug-write-db-btn" id="debug-write-db-btn">寫入DB</button>
            </div>
            <div id="debug-db-result"></div>
        </div>
    </div>

    <div class="modal-overlay" id="uploadModal">
        <div class="modal-content">
            <span class="modal-close" id="modal-close">&times;</span>
            <h3 id="modal-title">請上傳 ETF 開牌後的 CSV</h3>
            <div class="file-input-wrapper">
                <input type="file" id="csvFileInput" accept=".csv">
                <br>
                <a id="sample-csv-link" href="#" download>下載範例 CSV</a>
            </div>
            <button id="modal-upload-btn">上傳 CSV</button>
            <p id="upload-status" style="margin-top: 15px; font-size: 12px;"></p>
        </div>
    </div>

    <div class="modal-overlay" id="successModal">
        <div class="modal-content" style="width:360px;">
            <div style="font-size:40px; color:#27ae60; margin-bottom:12px;">&#10003;</div>
            <h3 id="success-etf-name" style="margin:0 0 8px; color:#27ae60;"></h3>
            <p style="margin:0 0 12px; font-size:14px;">CSV 上傳成功！</p>
            <p id="success-effective-hint" style="margin:0 0 20px; font-size:13px; color:red; font-weight:bold;"></p>
            <button id="success-ok-btn"
                style="padding:8px 28px; background:#0070C0; color:#fff; border:none; border-radius:4px; cursor:pointer; font-size:14px; font-family:'微軟正黑體',sans-serif;">確定</button>
        </div>
    </div>

    <div class="modal-overlay" id="reverseCsvModal">
        <div class="modal-content" style="width:360px;">
            <span class="modal-close" id="reverse-modal-close">&times;</span>
            <h3 id="reverse-modal-title">下載反單策略 CSV</h3>
            <p style="margin:0 0 10px; font-size:13px; color:#555;">選擇日期（調整期起日 ~ 今天的交易日）</p>
            <select id="reverse-date-select"></select>
            <p id="reverse-date-note" style="display:none; margin:8px 0 0; font-size:12px; color:#e67e22;"></p>
            <br>
            <button id="reverse-download-btn" style="margin-top:18px;">下載</button>
            <p id="reverse-status" style="margin-top: 12px; font-size: 12px;"></p>
        </div>
    </div>

    <div class="modal-overlay" id="periodModal">
        <div class="modal-content" style="width:340px;">
            <span class="modal-close" id="period-close">&times;</span>
            <h3 id="period-modal-title" style="margin:0 0 4px;">修改調整期間</h3>
            <div class="period-field">
                <label for="period-begin">開始日</label>
                <input type="date" id="period-begin">
            </div>
            <div class="period-field" id="period-end-field" style="display:none">
                <label for="period-end">結束日</label>
                <input type="date" id="period-end">
            </div>
            <p id="period-end-hint" style="margin:2px 0 0; font-size:12px; color:#555;"></p>
            <p class="period-error" id="period-error"></p>
            <div class="period-btn-row">
                <button id="period-save-btn">儲存</button>
                <button id="period-clear-btn" style="display:none">清除覆蓋</button>
                <button id="period-cancel-btn">取消</button>
            </div>
        </div>
    </div>

    <script>
        // API 位址：依頁面來源自動切換
        // - https（經 gateway，如 ai.uccapital.com.tw/etfdailyreportweb/...）→ 走同源反代 /<第一段路徑>/api_dev/...
        // - http （內網直連 172.16.253.156/web/...）→ 直接打 5051 埠
        const DEV_API = location.protocol === 'https:'
            ? `${location.origin}/${location.pathname.split('/')[1]}`
            : 'http://172.16.253.156:5051';

        (function () {
            function formatDate(d) {
                const y = d.getFullYear();
                const m = String(d.getMonth() + 1).padStart(2, '0');
                const day = String(d.getDate()).padStart(2, '0');
                return `${y}-${m}-${day}`;
            }

            async function exists(url) {
                try {
                    const r = await fetch(url, { method: 'HEAD' });
                    return r.ok;
                } catch {
                    return false;
                }
            }

            /*
            document.querySelectorAll('.immed-link').forEach(async a => {
                const etfId = a.dataset.etfId;
                const dateStr = formatDate(new Date());
                const url = `https://ai.uccapital.com.tw/etfdailyreportweb/etf/${etfId}/immed/${dateStr}.DailyReport.htm`;
        
                if (await exists(url)) {
                    a.href = url;
                } else {
                    a.classList.add('disabled');
                    a.textContent = '尚無資料';
                }
            });
            */
        })();

        // ════ Modal 開關 + CSV 上傳邏輯 ════
        let currentETFName = "";
        let currentETFId = "";

        // 開啟 Modal，帶入 ETF 名稱
        function openModal(etfId, etfName) {
            currentETFId = etfId;
            currentETFName = etfName;
            document.getElementById("modal-title").textContent = `請上傳 ${etfName} 開牌後的 CSV`;
            document.getElementById("sample-csv-link").href = `${DEV_API}/api_dev/sample_csv/${etfId}`;
            document.getElementById("upload-status").textContent = "";
            document.getElementById("upload-status").style.color = "";
            document.getElementById("csvFileInput").value = "";
            document.getElementById("modal-upload-btn").disabled = false;

            const modal = document.getElementById("uploadModal");
            modal.style.display = 'flex';
            requestAnimationFrame(() => modal.classList.add('show'));
        }

        // 關閉 Modal，等動畫結束再隱藏
        function closeModal() {
            const modal = document.getElementById("uploadModal");
            modal.classList.remove('show');
            setTimeout(() => modal.style.display = 'none', 300);
        }

        // 關閉按鈕
        document.getElementById("modal-close").addEventListener("click", closeModal);

        // 成功彈窗：確定按鈕 / 背景點擊 皆關閉
        function closeSuccessModal() {
            const sm = document.getElementById("successModal");
            sm.classList.remove('show');
            setTimeout(() => sm.style.display = 'none', 300);
        }
        document.getElementById("success-ok-btn").addEventListener("click", closeSuccessModal);
        document.getElementById("successModal").addEventListener("click", function (e) {
            if (e.target === this) closeSuccessModal();
        });

        // 點擊遮罩背景關閉 (點甜窗內部不觸發)
        document.getElementById("uploadModal").addEventListener("click", function (e) {
            if (e.target === this) closeModal();
        });

        // 表格 "上傳 CSV" 按鈕: 綁定事件，從 data-* 取 ETF 資訊
        document.querySelectorAll('.upload-btn').forEach(btn => {
            btn.addEventListener("click", () => {
                openModal(btn.dataset.etfId, btn.dataset.etfName);
            });
        });

        // 確認上傳，POST 到後端 API
        document.getElementById("modal-upload-btn").addEventListener("click", async () => {
            const fileInput = document.getElementById("csvFileInput");
            const statusMsg = document.getElementById("upload-status");
            const uploadBtn = document.getElementById("modal-upload-btn");

            if (fileInput.files.length == 0) {
                statusMsg.style.color = "red";
                statusMsg.textContent = "請先選擇一個 CSV 檔案";
                return;
            }

            const formData = new FormData();
            formData.append("file", fileInput.files[0]);
            formData.append("etfName", currentETFName);
            formData.append("etfId", currentETFId);

            uploadBtn.disabled = true; // 防止重複點擊
            statusMsg.style.color = "#000";
            statusMsg.textContent = "上傳中...";

            try {
                const response = await fetch(`${DEV_API}/api_dev/upload_csv`, {
                    method: "POST",
                    body: formData
                });

                if (response.ok) {
                    const result = await response.json();

                    const timeEl = document.querySelector(`.upload-time[data-etf-id="${currentETFId}"]`);
                    if (timeEl && result.last_upload) timeEl.textContent = `上次上傳：${result.last_upload}`;

                    const uploadedBtn = document.querySelector(`.upload-btn[data-etf-id="${currentETFId}"]`);
                    if (uploadedBtn) uploadedBtn.classList.remove('not-uploaded');

                    // 上傳成功後（調整期內）啟用「下載CSV」按鈕
                    const reverseBtn = document.querySelector(`.reverse-csv-btn[data-etf-id="${currentETFId}"]`);
                    if (reverseBtn) reverseBtn.disabled = false;

                    closeModal();
                    document.getElementById("success-etf-name").textContent = currentETFName;
                    document.getElementById("success-effective-hint").textContent = result.effective_hint || '';
                    const sm = document.getElementById("successModal");
                    sm.style.display = 'flex';
                    requestAnimationFrame(() => sm.classList.add('show'));
                } else {
                    const errResult = await response.json().catch(() => ({}));
                    statusMsg.style.color = "red";
                    statusMsg.innerHTML = "";
                    if (errResult.details && errResult.details.length > 0) {
                        const summary = document.createElement("span");
                        summary.textContent = "資料格式有誤";
                        statusMsg.appendChild(summary);

                        const badge = document.createElement("span");
                        badge.className = "err-detail-badge";
                        badge.textContent = "詳細錯誤訊息";

                        const box = document.createElement("div");
                        box.className = "err-detail-box";
                        errResult.details.forEach((item, idx) => {
                            if (idx > 0) {
                                const gap = document.createElement("div");
                                gap.style.marginTop = "4px";
                                box.appendChild(gap);
                            }
                            if (item.row != null) {
                                const rowHeader = document.createElement("div");
                                rowHeader.textContent = `第${item.row}行：`;
                                box.appendChild(rowHeader);
                            }
                            item.errors.forEach(e => {
                                const line = document.createElement("div");
                                line.textContent = `* ${e}`;
                                if (item.row != null) line.style.paddingLeft = "8px";
                                box.appendChild(line);
                            });
                        });
                        badge.appendChild(box);
                        statusMsg.appendChild(badge);
                    } else {
                        statusMsg.textContent = errResult.error || `${currentETFName} CSV 上傳失敗，請稍後再試。`;
                    }
                    uploadBtn.disabled = false; // 失敗時允許重試
                }
            } catch (error) {
                statusMsg.style.color = "red";
                statusMsg.textContent = `上傳過程中發生錯誤，請稍後再試。`;
                uploadBtn.disabled = false; // 失敗時允許重試
                console.error("上傳錯誤:", error);
            }
        });

        // 動態更新資料截止日、生效日與調整期間。
        // 抽成具名函式，調整期間彈窗存檔後要能再呼叫一次刷新畫面。
        // 順手把整份 etf_dates 存進 window.__etfDates，供彈窗預帶當前值。
        async function refreshEtfDates() {
            try {
                const res = await fetch(`${DEV_API}/api_dev/etf_dates`);
                const data = await res.json();
                window.__etfDates = data;
                for (const [etfId, info] of Object.entries(data)) {
                    const deadlineEl = document.querySelector(`.etf-deadline[data-etf-id="${etfId}"]`);
                    const effectiveEl = document.querySelector(`.etf-effective[data-etf-id="${etfId}"]`);
                    if (deadlineEl && info.deadline) deadlineEl.innerHTML = info.deadline;
                    if (effectiveEl && info.effective) effectiveEl.innerHTML = info.effective;

                    const periodEl = document.querySelector(`.period-text[data-etf-id="${etfId}"]`);
                    const editBtn = document.querySelector(`.edit-period-btn[data-etf-id="${etfId}"]`);
                    const hasPeriod = !!(info.adjust_begin && info.adjust_end);
                    if (periodEl) periodEl.textContent = hasPeriod
                        ? `${info.adjust_begin} ~ ${info.adjust_end}` : '-';
                    if (editBtn) editBtn.style.display = hasPeriod ? 'inline-block' : 'none';
                }
            } catch (e) {
                // 後端未啟動時靜默略過，保留靜態值
            }
        }
        refreshEtfDates();

        // 頁面載入時從後端取回所有 ETF 的上次上傳時間
        (async function () {
            try {
                const res = await fetch(`${DEV_API}/api_dev/upload_times`);
                const times = await res.json();
                for (const [etfId, uploadTime] of Object.entries(times)) {
                    const timeEl = document.querySelector(`.upload-time[data-etf-id="${etfId}"]`);
                    if (timeEl && uploadTime) timeEl.textContent = `上次上傳：${uploadTime}`;
                }
            } catch (e) {
                // 後端未啟動時靜默略過，不影響頁面顯示
            }
        })();

        // 顯示非調整期紅字，並鎖定非調整期的上傳按鈕
        (async function () {
            try {
                const res = await fetch(`${DEV_API}/api_dev/etf_adjust_status`);
                const status = await res.json();
                for (const [etfId, info] of Object.entries(status)) {
                    const el = document.querySelector(`.not-in-period[data-etf-id="${etfId}"]`);
                    const btn = document.querySelector(`.upload-btn[data-etf-id="${etfId}"]`);
                    if (!info.in_period) {
                        if (el) el.style.display = 'block';
                        if (btn) btn.disabled = true;
                        const timeEl = document.querySelector(`.upload-time[data-etf-id="${etfId}"]`);
                        if (timeEl) timeEl.textContent = '';
                    } else {
                        if (btn) {
                            btn.disabled = false;
                            if (info.uploaded_in_period) {
                                btn.classList.remove('not-uploaded');
                            } else {
                                btn.classList.add('not-uploaded');
                            }
                        }
                    }
                    toggleReverseCsvBtn(etfId, info);
                }
            } catch (e) {
                // 後端未啟動時靜默略過
            }
        })();

        // ════ DEV: 模擬日期控制 ════
        // DEV_API 已於 <script> 開頭定義（依 http/https 自動切換）

        async function loadMockDate() {
            try {
                const res = await fetch(`${DEV_API}/api_dev/mock_date`);
                const data = await res.json();
                const el = document.getElementById('debug-current-date');
                if (data.mock_date || data.mock_time) {
                    const parts = [];
                    if (data.mock_date) parts.push(data.mock_date);
                    if (data.mock_time) parts.push(`${data.mock_time}（凍結）`);
                    el.textContent = `模擬 ${parts.join(' ')}`;
                    el.style.color = '#ff6b6b';
                    document.getElementById('debug-date-input').value = data.mock_date || '';
                    document.getElementById('debug-time-input').value = data.mock_time || '';
                } else {
                    el.textContent = '真實日期';
                    el.style.color = '#7ec8e3';
                }
            } catch (e) { /* 靜默略過 */ }
        }

        async function refreshAdjustStatus() {
            try {
                const [timesRes, statusRes] = await Promise.all([
                    fetch(`${DEV_API}/api_dev/upload_times`),
                    fetch(`${DEV_API}/api_dev/etf_adjust_status`)
                ]);
                const times = await timesRes.json();
                const status = await statusRes.json();
                for (const [etfId, uploadTime] of Object.entries(times)) {
                    const timeEl = document.querySelector(`.upload-time[data-etf-id="${etfId}"]`);
                    if (timeEl && uploadTime) timeEl.textContent = `上次上傳：${uploadTime}`;
                }
                for (const [etfId, info] of Object.entries(status)) {
                    const el = document.querySelector(`.not-in-period[data-etf-id="${etfId}"]`);
                    const btn = document.querySelector(`.upload-btn[data-etf-id="${etfId}"]`);
                    if (!info.in_period) {
                        if (el) el.style.display = 'block';
                        if (btn) btn.disabled = true;
                        const timeEl = document.querySelector(`.upload-time[data-etf-id="${etfId}"]`);
                        if (timeEl) timeEl.textContent = '';
                    } else {
                        if (el) el.style.display = 'none';
                        if (btn) {
                            btn.disabled = false;
                            btn.classList.toggle('not-uploaded', !info.uploaded_in_period);
                        }
                    }
                    toggleReverseCsvBtn(etfId, info);
                }
            } catch (e) { /* 靜默略過 */ }
        }

        // 套用/清除模擬日期／時間：日期有變時後端會同步重算 etf_dates.json（約數秒），
        // 期間顯示轉圈圈與「正在轉換中」，完成後高亮轉換後的時間 5 秒
        async function switchMockDate(dateVal, timeVal) {
            const applyBtn = document.getElementById('debug-apply-btn');
            const clearBtn = document.getElementById('debug-clear-btn');
            const el = document.getElementById('debug-current-date');
            applyBtn.disabled = true;
            clearBtn.disabled = true;
            el.classList.remove('flash');
            el.innerHTML = '<span class="btn-spinner"></span>正在轉換中...';
            el.style.color = '#f0a500';

            try {
                await fetch(`${DEV_API}/api_dev/mock_date`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ date: dateVal, time: timeVal })
                });
                // 重整讓整頁資訊（截止日/生效日、調整期狀態等）跟著新日期更新；
                // 高亮由重整後的頁面依 sessionStorage 旗標接手顯示
                try { sessionStorage.setItem('mockDateJustChanged', '1'); } catch (e) { /* 靜默略過 */ }
                location.reload();
            } catch (e) {
                el.textContent = '轉換失敗';
                el.style.color = '#ff6b6b';
                applyBtn.disabled = false;
                clearBtn.disabled = false;
            }
        }

        document.getElementById('debug-apply-btn').addEventListener('click', async () => {
            const dateVal = document.getElementById('debug-date-input').value;
            const timeVal = document.getElementById('debug-time-input').value;
            if (!dateVal && !timeVal) return;
            // 以輸入框的完整狀態為準：留空的欄位代表清除該項模擬
            await switchMockDate(dateVal || null, timeVal || null);
        });

        document.getElementById('debug-clear-btn').addEventListener('click', async () => {
            await switchMockDate(null, null);
            document.getElementById('debug-date-input').value = '';
            document.getElementById('debug-time-input').value = '';
        });

        // 頁面載入時顯示目前模擬狀態；若是剛轉換完成後的自動重整，補做高亮 5 秒
        loadMockDate().then(() => {
            try {
                if (sessionStorage.getItem('mockDateJustChanged') === '1') {
                    sessionStorage.removeItem('mockDateJustChanged');
                    const el = document.getElementById('debug-current-date');
                    el.classList.add('flash');
                    setTimeout(() => el.classList.remove('flash'), 5000);
                }
            } catch (e) { /* 靜默略過 */ }
        });

        // ════ DEV 面板收合／展開（狀態記在 localStorage，重新整理後保留） ════
        (function () {
            const panel = document.getElementById('debug-panel');
            const toggleBtn = document.getElementById('debug-toggle-btn');
            function setCollapsed(collapsed) {
                panel.classList.toggle('collapsed', collapsed);
                toggleBtn.innerHTML = collapsed ? '+' : '&minus;';
                toggleBtn.title = collapsed ? '展開面板' : '收合面板';
                try { localStorage.setItem('debugPanelCollapsed', collapsed ? '1' : '0'); } catch (e) { /* 靜默略過 */ }
            }
            toggleBtn.addEventListener('click', () => {
                setCollapsed(!panel.classList.contains('collapsed'));
            });
            try {
                if (localStorage.getItem('debugPanelCollapsed') === '1') setCollapsed(true);
            } catch (e) { /* 靜默略過 */ }
        })();

        // ════ DEV: 寫入DB ════
        document.getElementById('debug-write-db-btn').addEventListener('click', async () => {
            if (!confirm('確定要執行寫入DB嗎？')) return;

            const btn = document.getElementById('debug-write-db-btn');
            const resultEl = document.getElementById('debug-db-result');

            btn.disabled = true;
            btn.textContent = '執行中...';
            resultEl.style.display = 'block';
            resultEl.style.color = '#aaa';
            resultEl.textContent = '執行中，請稍候...';

            try {
                const res = await fetch(`${DEV_API}/api_dev/run_db_importer`, { method: 'POST' });
                const data = await res.json();

                if (data.status === 'success') {
                    resultEl.style.color = '#27ae60';
                    resultEl.textContent = '✓ 寫入成功' + (data.stdout ? '\t' + data.stdout.trim() : '');
                } else {
                    resultEl.style.color = '#ff6b6b';
                    const msg = data.stderr || data.message || '';
                    resultEl.textContent = '✗ 失敗' + (msg ? '\t' + msg.trim() : '');
                }
            } catch (e) {
                resultEl.style.color = '#ff6b6b';
                resultEl.textContent = '✗ 連線失敗';
            }

            btn.disabled = false;
            btn.textContent = '寫入DB';
        });

        // ════ 下載反單策略 CSV ════
        // 依調整期狀態切換表格內按鈕：調整期內且已上傳才顯示
        function toggleReverseCsvBtn(etfId, info) {
            const btn = document.querySelector(`.reverse-csv-btn[data-etf-id="${etfId}"]`);
            if (btn) btn.disabled = !(info.in_period && info.uploaded_in_period);
        }

        let currentReverseEtfId = "";

        function closeReverseModal() {
            const modal = document.getElementById("reverseCsvModal");
            modal.classList.remove('show');
            setTimeout(() => modal.style.display = 'none', 300);
        }
        document.getElementById("reverse-modal-close").addEventListener("click", closeReverseModal);
        document.getElementById("reverseCsvModal").addEventListener("click", function (e) {
            if (e.target === this) closeReverseModal();
        });

        async function openReverseModal(etfId, etfName) {
            currentReverseEtfId = etfId;
            document.getElementById("reverse-modal-title").textContent = `下載 ${etfName} 反單策略 CSV`;
            const select = document.getElementById("reverse-date-select");
            const dlBtn = document.getElementById("reverse-download-btn");
            const statusEl = document.getElementById("reverse-status");
            const noteEl = document.getElementById("reverse-date-note");
            select.innerHTML = '<option>日期載入中...</option>';
            select.disabled = true;
            dlBtn.disabled = true;
            dlBtn.textContent = '下載';
            statusEl.textContent = '';
            statusEl.style.color = '';
            noteEl.style.display = 'none';

            const modal = document.getElementById("reverseCsvModal");
            modal.style.display = 'flex';
            requestAnimationFrame(() => modal.classList.add('show'));

            try {
                const res = await fetch(`${DEV_API}/api_dev/reverse_csv_dates/${etfId}`);
                const data = await res.json();
                if (!res.ok || !data.dates) {
                    select.innerHTML = '<option>—</option>';
                    statusEl.style.color = 'red';
                    statusEl.textContent = data.message || '日期載入失敗';
                    return;
                }
                // 18:00 前後端會把「今天」從清單排除，於選單下方註記原因
                if (data.today_blocked) {
                    noteEl.textContent = `18:00 前不提供 ${data.today_blocked} 的反向單CSV`;
                    noteEl.style.display = 'block';
                }
                if (data.dates.length === 0) {
                    select.innerHTML = '<option>—</option>';
                    statusEl.style.color = 'red';
                    statusEl.textContent = data.today_blocked ? '目前沒有其他可下載的日期' : '區間內沒有交易日';
                    return;
                }
                // 新的日期排前面，預設選最新一天
                select.innerHTML = data.dates.slice().reverse()
                    .map(d => `<option value="${d}">${d}</option>`).join('');
                select.disabled = false;
                dlBtn.disabled = false;
            } catch (e) {
                select.innerHTML = '<option>—</option>';
                statusEl.style.color = 'red';
                statusEl.textContent = '連線失敗，日期載入失敗';
            }
        }

        document.querySelectorAll('.reverse-csv-btn').forEach(btn => {
            btn.addEventListener("click", () => {
                openReverseModal(btn.dataset.etfId, btn.dataset.etfName);
            });
        });

        // 點下載：後端重跑 tracker 現算該日反單 CSV，期間按鈕反灰 + 轉圈圈
        document.getElementById("reverse-download-btn").addEventListener("click", async () => {
            const select = document.getElementById("reverse-date-select");
            const dlBtn = document.getElementById("reverse-download-btn");
            const statusEl = document.getElementById("reverse-status");
            const dateVal = select.value;
            if (!dateVal) return;

            dlBtn.disabled = true;
            select.disabled = true;
            dlBtn.innerHTML = '<span class="btn-spinner"></span>產生中...';
            statusEl.style.color = '#000';
            statusEl.textContent = '正在產出資料，請稍候...';

            try {
                const res = await fetch(`${DEV_API}/api_dev/reverse_csv/${currentReverseEtfId}?date=${dateVal}`);
                const contentType = res.headers.get('Content-Type') || '';
                if (res.ok && !contentType.includes('application/json')) {
                    const blob = await res.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${currentReverseEtfId}_${dateVal}.csv`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    URL.revokeObjectURL(url);
                    // 後端在該次 tracker 輸出偵測到「當日資料整批為空」時會帶此 header
                    if (res.headers.get('X-Data-Warning')) {
                        statusEl.style.color = '#e67e22';
                        statusEl.textContent = '⚠ 已下載，但當日 DB 資料不全，CSV 內容可能缺漏';
                    } else {
                        statusEl.style.color = '#27ae60';
                        statusEl.textContent = '✓ 已開始下載';
                    }
                } else {
                    const err = await res.json().catch(() => ({}));
                    statusEl.style.color = 'red';
                    statusEl.textContent = '✗ ' + (err.detail || err.message || '產生失敗，請稍後再試');
                }
            } catch (e) {
                statusEl.style.color = 'red';
                statusEl.textContent = '✗ 連線失敗，請稍後再試';
            }

            dlBtn.disabled = false;
            select.disabled = false;
            dlBtn.textContent = '下載';
        });

        // ════ 調整期間修改 ════
        // 存檔流程在後端是同步的（寫覆蓋檔 → 重算 etf_dates → 重算反向單 CSV，最壞 120 秒），
        // 期間鎖住三顆按鈕避免重複送出。錯誤訊息一律用後端回的 message，前端不自己編。
        (function () {
            const modal = document.getElementById('periodModal');
            const titleEl = document.getElementById('period-modal-title');
            const beginEl = document.getElementById('period-begin');
            const endEl = document.getElementById('period-end');
            const errorEl = document.getElementById('period-error');
            const saveBtn = document.getElementById('period-save-btn');
            const clearBtn = document.getElementById('period-clear-btn');
            const cancelBtn = document.getElementById('period-cancel-btn');
            let currentPeriodEtfId = null;

            function setBusy(busy) {
                [saveBtn, clearBtn, cancelBtn].forEach(b => b.disabled = busy);
                saveBtn.textContent = busy ? '重算中…' : '儲存';
            }

            function openPeriodModal(etfId, etfName) {
                currentPeriodEtfId = etfId;
                const info = (window.__etfDates || {})[etfId] || {};
                let begin = info.adjust_begin || '';
                let end = info.adjust_end || '';
                if (!begin || !end) {
                    // __etfDates 還沒載到（後端曾短暫失聯）時，退回讀畫面上的靜態值
                    const textEl = document.querySelector(`.period-text[data-etf-id="${etfId}"]`);
                    const parts = (textEl ? textEl.textContent : '').split(' ~ ');
                    if (parts.length === 2) { begin = parts[0].trim(); end = parts[1].trim(); }
                }
                titleEl.textContent = `修改調整期間 - ${etfName}`;
                beginEl.value = begin;
                endEl.value = end;
                document.getElementById('period-end-hint').textContent =
                    end ? `結束日 ${end}（固定，由系統計算）` : '';
                errorEl.textContent = '';
                setBusy(false);
                modal.style.display = 'flex';
                requestAnimationFrame(() => modal.classList.add('show'));
            }

            function closePeriodModal() {
                modal.classList.remove('show');
                setTimeout(() => modal.style.display = 'none', 300);
            }

            async function submitPeriod(method, payload) {
                errorEl.textContent = '';
                setBusy(true);
                try {
                    const opts = { method };
                    if (payload) {
                        opts.headers = { 'Content-Type': 'application/json' };
                        opts.body = JSON.stringify(payload);
                    }
                    const res = await fetch(`${DEV_API}/api_dev/adjust_period/${currentPeriodEtfId}`, opts);
                    const data = await res.json();
                    if (!res.ok || data.status !== 'ok') {
                        errorEl.textContent = data.message || '修改失敗';
                        setBusy(false);
                        return;
                    }
                    closePeriodModal();
                    await refreshEtfDates();      // 調整期間 / 截止日 / 生效日
                    await refreshAdjustStatus();  // 非調整期紅字、上傳按鈕、下載CSV 按鈕
                } catch (e) {
                    errorEl.textContent = '連線失敗，請稍後再試';
                    setBusy(false);
                }
            }

            document.querySelectorAll('.edit-period-btn').forEach(btn => {
                btn.addEventListener('click', () => openPeriodModal(btn.dataset.etfId, btn.dataset.etfName));
            });

            saveBtn.addEventListener('click', () => {
                if (!beginEl.value) {
                    errorEl.textContent = '請填寫調整期間的開始日';
                    return;
                }
                submitPeriod('POST', { adjust_begin: beginEl.value });
            });

            clearBtn.addEventListener('click', () => {
                if (!confirm('確定要清除覆蓋，回到自動計算的調整期間？')) return;
                submitPeriod('DELETE', null);
            });

            cancelBtn.addEventListener('click', closePeriodModal);
            document.getElementById('period-close').addEventListener('click', closePeriodModal);
            modal.addEventListener('click', function (e) { if (e.target === this) closePeriodModal(); });
        })();
    </script>

</body>

</html>"""

# =========================
# \u8f38\u51fa index.html
# =========================
html = html.replace("{ROWS}", "".join(rows))

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("index.html \u5df2\u6210\u529f\u7522\u751f")



# 執行
# cd /var/www/html/web/etf/home/dev && /home/webuser/etf/venv/bin/python jsonToHtml.py
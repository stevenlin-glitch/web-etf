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
    {"id": "00919_May", "name": "00919 五月定審版"},
    {"id": "00919_Dec", "name": "00919 十二月定審版"},
    {"id": "00929", "name": "00929"},
]

# =========================
# 讀取日期資訊 JSON
# =========================
# 使用絕對路徑，避免從不同目錄執行時靜默失敗產出全 "-" 的 HTML
_ETF_DATES_PATH = "/home/webuser/etf/etf_calculator/report_generator/dateData/etf_dates.json"
try:
    with open(_ETF_DATES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    raise SystemExit(f"[錯誤] 找不到 {_ETF_DATES_PATH}，請確認路徑後再執行")

# =========================
# 產生 table rows（純字串）
# =========================
rows = []
for etf in etfs:
    info = data.get(etf["id"], {"deadline": "-", "effective": "-"})
    if etf["id"] in NO_UPLOAD_ETFS:
        upload_cell = "<td></td>"
    else:
        upload_cell = (
            '<td>'
            '<button class="upload-btn" data-etf-id="{id}" data-etf-name="{name}">上傳 CSV</button>'
            '<br>'
            '<small class="upload-time" data-etf-id="{id}"></small>'
            '<small class="not-in-period" data-etf-id="{id}">現在非調整期</small>'
            '</td>'
        ).format(id=etf["id"], name=etf["name"])
    rows.append("""
    <tr>
        <td>{name}</td>
        <td class="etf-deadline" data-etf-id="{id}">{deadline}</td>
        <td class="etf-effective" data-etf-id="{id}">{effective}</td>
        <td><a href="http://172.16.8.210/web/etf/{id}/alpha/diff.html">搶先版</a></td>
        <td><a href="http://172.16.8.210/web/etf/{id}/beta/diff.html">凌晨版</a></td>
        <td><a href="http://172.16.8.210/web/etf/{id}/prod/diff.html">正式版</a></td>
        <!--<td><a class="immed-link" data-etf-id="{id}">即時股價</a></td>-->
        {upload_cell}
    </tr>
    """.format(
        name=etf["name"],
        id=etf["id"],
        deadline=info.get("deadline", "-"),
        effective=info.get("effective", "-"),
        upload_cell=upload_cell,
    ))

# =========================
# HTML Template（⚠️ 非 f-string）
# =========================
html = """<!DOCTYPE html>
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
th, td {
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
.upload-btn:hover { background-color: #219a52; }
.upload-btn.not-uploaded { background-color: #e74c3c; }
.upload-btn.not-uploaded:hover { background-color: #c0392b; }
.upload-btn:disabled {
    background-color: #bdc3c7;
    color: #fff;
    cursor: not-allowed;
    opacity: 0.7;
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
.modal-overlay.show { opacity: 1; }

/* ════ Modal 彈窗本體 ════ */
.modal-content {
    background: #fff;
    padding: 30px;
    border-radius: 8px;
    text-align: center;
    box-shadow: 0 4px 16px rgba(0,0,0,0.2);
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
.modal-close:hover { color: #000; }
.file-input-wrapper {margin: 20px 0; }
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
#modal-upload-btn:hover { background-color: #005A9E; }
#modal-upload-btn:disabled { background-color: #a0c4e8; cursor: not-allowed; }

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
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.err-detail-badge:hover .err-detail-box { display: block; }

</style>
</head>

<body>
<h2>ETF 機率日報表首頁</h2>

<table>
<tr>
    <th>ETF</th>
    <th>資料截止日</th>
    <th>生效日</th>
    <th>搶先版</th>
    <th>凌晨版</th>
    <th>正式版</th>
    <!--<th>即時股價</th>-->
    <th>上傳 CSV </th>
</tr>
{ROWS}
</table>

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
        <button id="success-ok-btn" style="padding:8px 28px; background:#0070C0; color:#fff; border:none; border-radius:4px; cursor:pointer; font-size:14px; font-family:'微軟正黑體',sans-serif;">確定</button>
    </div>
</div>

<script>
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
        const url = `http://172.16.8.210/web/etf/${etfId}/immed/${dateStr}.DailyReport.htm`;

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
    document.getElementById("sample-csv-link").href = `http://172.16.8.210:5050/api/sample_csv/${etfId}`;
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
document.getElementById("successModal").addEventListener("click", function(e) {
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

    if(fileInput.files.length == 0) {
        statusMsg.style.color = "red";
        statusMsg.textContent = "請先選擇一個 CSV 檔案";
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("etfName", currentETFName);
    formData.append("etfId",   currentETFId);

    uploadBtn.disabled = true; // 防止重複點擊
    statusMsg.style.color = "#000";
    statusMsg.textContent = "上傳中...";

    try {
        const response = await fetch("http://172.16.8.210:5050/api/upload_csv", {
            method: "POST",
            body: formData
        });

        if(response.ok) {
            const result = await response.json();

            const timeEl = document.querySelector(`.upload-time[data-etf-id="${currentETFId}"]`);
            if (timeEl && result.last_upload) timeEl.textContent = `上次上傳：${result.last_upload}`;

            const uploadedBtn = document.querySelector(`.upload-btn[data-etf-id="${currentETFId}"]`);
            if (uploadedBtn) uploadedBtn.classList.remove('not-uploaded');

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

// 頁面載入時動態更新資料截止日與生效日
(async function () {
    try {
        const res  = await fetch('http://172.16.8.210:5050/api/etf_dates');
        const data = await res.json();
        for (const [etfId, info] of Object.entries(data)) {
            const deadlineEl  = document.querySelector(`.etf-deadline[data-etf-id="${etfId}"]`);
            const effectiveEl = document.querySelector(`.etf-effective[data-etf-id="${etfId}"]`);
            if (deadlineEl  && info.deadline)  deadlineEl.innerHTML  = info.deadline;
            if (effectiveEl && info.effective) effectiveEl.innerHTML = info.effective;
        }
    } catch (e) {
        // 後端未啟動時靜默略過，保留靜態值
    }
})();

// 頁面載入時從後端取回所有 ETF 的上次上傳時間
(async function () {
    try {
        const res   = await fetch('http://172.16.8.210:5050/api/upload_times');
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
        const res    = await fetch('http://172.16.8.210:5050/api/etf_adjust_status');
        const status = await res.json();
        for (const [etfId, info] of Object.entries(status)) {
            const el  = document.querySelector(`.not-in-period[data-etf-id="${etfId}"]`);
            const btn = document.querySelector(`.upload-btn[data-etf-id="${etfId}"]`);
            if (!info.in_period) {
                if (el)  el.style.display = 'block';
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
        }
    } catch (e) {
        // 後端未啟動時靜默略過
    }
})();

</script>

</body>
</html>
"""

# =========================
# 輸出 index.html
# =========================
html = html.replace("{ROWS}", "".join(rows))

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("index.html 已成功產生")


# 記得讓 app.py 跑起來
# /var/www/html/web/venv/bin/python3 /var/www/html/web/etf/RESTful_API/app.py
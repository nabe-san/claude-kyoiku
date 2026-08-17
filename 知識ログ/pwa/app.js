// 調べものログ PWA — 送信ロジック + オフラインキュー（retry-on-load方式）
//
// GAS Web AppへPOSTする際、Content-Type: application/jsonを指定するとブラウザが
// CORSプリフライト(OPTIONS)を発行し、GAS側がそれに応答できず失敗する。
// text/plainを指定するとプリフライトが発生しないため、ここではtext/plainで送り、
// GAS側でe.postData.contentsをJSON.parseして読む。

const STORAGE_KEYS = {
  webAppUrl: "chosaresu_webAppUrl",
  token: "chosaresu_token",
  queue: "chosaresu_queue",
};

function getSetting(key) {
  return localStorage.getItem(STORAGE_KEYS[key]) || "";
}

function setSetting(key, value) {
  localStorage.setItem(STORAGE_KEYS[key], value);
}

function loadQueue() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEYS.queue) || "[]");
  } catch (e) {
    return [];
  }
}

function saveQueue(queue) {
  localStorage.setItem(STORAGE_KEYS.queue, JSON.stringify(queue));
}

function updateQueueBadge() {
  const queue = loadQueue();
  const el = document.getElementById("queueBadge");
  el.textContent = queue.length > 0 ? `未送信: ${queue.length}件（自動で再送信します）` : "";
}

async function sendQuery(query) {
  const url = getSetting("webAppUrl");
  const token = getSetting("token");
  if (!url || !token) {
    throw new Error("設定未完了");
  }

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "text/plain;charset=utf-8" },
    body: JSON.stringify({ token, query }),
  });

  if (!res.ok) throw new Error("HTTP " + res.status);
  const data = await res.json();
  if (!data.ok) throw new Error(data.error || "送信失敗");
  return data;
}

async function flushQueue() {
  const queue = loadQueue();
  if (queue.length === 0) return;

  const remaining = [];
  for (const query of queue) {
    try {
      await sendQuery(query);
    } catch (e) {
      remaining.push(query);
    }
  }
  saveQueue(remaining);
  updateQueueBadge();
}

function setStatus(message, kind) {
  const el = document.getElementById("statusMsg");
  el.textContent = message;
  el.className = "status" + (kind ? " " + kind : "");
}

function openSettingsDialog() {
  document.getElementById("webAppUrlInput").value = getSetting("webAppUrl");
  document.getElementById("tokenInput").value = getSetting("token");
  document.getElementById("settingsDialog").showModal();
}

function initSettingsIfMissing() {
  if (!getSetting("webAppUrl") || !getSetting("token")) {
    openSettingsDialog();
  }
}

document.getElementById("openSettings").addEventListener("click", openSettingsDialog);

document.getElementById("settingsCancel").addEventListener("click", () => {
  document.getElementById("settingsDialog").close();
});

document.getElementById("settingsSave").addEventListener("click", () => {
  const url = document.getElementById("webAppUrlInput").value.trim();
  const token = document.getElementById("tokenInput").value.trim();
  if (!url || !token) return;
  setSetting("webAppUrl", url);
  setSetting("token", token);
  document.getElementById("settingsDialog").close();
});

document.getElementById("captureForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.getElementById("queryInput");
  const query = input.value.trim();
  if (!query) return;

  const submitBtn = document.getElementById("submitBtn");
  submitBtn.disabled = true;

  if (!getSetting("webAppUrl") || !getSetting("token")) {
    submitBtn.disabled = false;
    openSettingsDialog();
    return;
  }

  try {
    await sendQuery(query);
    setStatus("送信しました", "ok");
    input.value = "";
  } catch (e) {
    const queue = loadQueue();
    queue.push(query);
    saveQueue(queue);
    setStatus("オフラインのため保存しました（次回起動時に自動送信）", "pending");
    input.value = "";
  }

  updateQueueBadge();
  submitBtn.disabled = false;
});

// 起動時・フォアグラウンド復帰時にキューのフラッシュを試みる
window.addEventListener("load", () => {
  initSettingsIfMissing();
  updateQueueBadge();
  flushQueue();
});

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    flushQueue();
  }
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./service-worker.js").catch(() => {
    // オフライン用シェルキャッシュが使えなくても送信機能自体には影響しない
  });
}

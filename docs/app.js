const DATA_URL = "./data/status.json";
const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

const statusMessageEl = document.querySelector("#status-message");
const statusPillEl = document.querySelector("#status-pill");
const updatedAtEl = document.querySelector("#updated-at");
const countdownEl = document.querySelector("#countdown");
const detailListEl = document.querySelector("#detail-list");
const fromStopEl = document.querySelector("#from-stop");
const toStopEl = document.querySelector("#to-stop");
const sourceLinkEl = document.querySelector("#source-link");

let nextRefreshAt = Date.now() + REFRESH_INTERVAL_MS;

function formatDateTime(value) {
  if (!value) {
    return "--";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "--";
  }

  return new Intl.DateTimeFormat("ja-JP", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(date);
}

function formatCountdown(deadline) {
  const remaining = Math.max(0, deadline - Date.now());
  const totalSeconds = Math.floor(remaining / 1000);
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function setTone(className, label) {
  statusPillEl.classList.remove("tone-ok", "tone-warn", "tone-error");
  statusPillEl.classList.add(className);
  statusPillEl.textContent = label;
}

function renderDetails(items) {
  detailListEl.innerHTML = "";

  if (!items?.length) {
    const item = document.createElement("li");
    item.textContent = "表示できる明細はありません。";
    detailListEl.append(item);
    return;
  }

  for (const entry of items) {
    const item = document.createElement("li");
    item.textContent = entry;
    detailListEl.append(item);
  }
}

function renderPayload(payload) {
  fromStopEl.textContent = payload.route?.fromStop?.name ?? "伊勢山（平塚市）";
  toStopEl.textContent = payload.route?.toStop?.name ?? "大野農協前（平塚市）";
  sourceLinkEl.href = payload.source?.url ?? "https://real.kanachu.jp/pc/top";

  statusMessageEl.textContent = payload.message ?? "情報を取得できませんでした。";
  updatedAtEl.textContent = formatDateTime(payload.fetchedAt);

  if (payload.status === "error") {
    setTone("tone-error", "取得失敗");
  } else if (payload.hasLiveData) {
    setTone("tone-ok", "運行情報あり");
  } else {
    setTone("tone-warn", "接近情報なし");
  }

  renderDetails(payload.details);
}

async function loadData() {
  const url = `${DATA_URL}?t=${Date.now()}`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const payload = await response.json();
  renderPayload(payload);
  nextRefreshAt = Date.now() + REFRESH_INTERVAL_MS;
}

async function refresh() {
  try {
    await loadData();
  } catch (error) {
    renderPayload({
      status: "error",
      message: "status.json を読めませんでした。",
      fetchedAt: null,
      hasLiveData: false,
      route: {
        fromStop: { name: "伊勢山（平塚市）" },
        toStop: { name: "大野農協前（平塚市）" },
      },
      source: { url: "https://real.kanachu.jp/pc/top" },
      details: [error instanceof Error ? error.message : String(error)],
    });
    nextRefreshAt = Date.now() + REFRESH_INTERVAL_MS;
  }
}

setInterval(() => {
  countdownEl.textContent = formatCountdown(nextRefreshAt);
}, 1000);

setInterval(() => {
  refresh();
}, REFRESH_INTERVAL_MS);

refresh();
const DATA_URL = "./data/status.json";
const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

const statusMessageEl = document.querySelector("#status-message");
const statusPillEl = document.querySelector("#status-pill");
const updatedAtEl = document.querySelector("#updated-at");
const sourceUpdatedEl = document.querySelector("#source-updated");
const journeyCountEl = document.querySelector("#journey-count");
const countdownEl = document.querySelector("#countdown");
const detailListEl = document.querySelector("#detail-list");
const overviewTextEl = document.querySelector("#overview-text");
const scheduledArrivalTimeEl = document.querySelector("#scheduled-arrival-time");
const delayMinutesEl = document.querySelector("#delay-minutes");
const expectedArrivalTimeEl = document.querySelector("#expected-arrival-time");
const quickPeekNextTimeEl = document.querySelector("#quick-peek-next-time");
const quickPeekNextRouteEl = document.querySelector("#quick-peek-next-route");
const quickPeekNextMetaEl = document.querySelector("#quick-peek-next-meta");
const quickPeekLaterTimeEl = document.querySelector("#quick-peek-later-time");
const quickPeekLaterRouteEl = document.querySelector("#quick-peek-later-route");
const quickPeekLaterMetaEl = document.querySelector("#quick-peek-later-meta");
const nextJourneySectionEl = document.querySelector("#next-journey-section");
const nextJourneyNoteEl = document.querySelector("#next-journey-note");
const nextJourneyEl = document.querySelector("#next-journey");
const journeyListSectionEl = document.querySelector("#journey-list-section");
const journeyCountInlineEl = document.querySelector("#journey-count-inline");
const journeyGridEl = document.querySelector("#journey-grid");
const noticeListEl = document.querySelector("#notice-list");
const fromStopEl = document.querySelector("#from-stop");
const toStopEl = document.querySelector("#to-stop");
const sourceLinkEl = document.querySelector("#source-link");
const directionSwitchEl = document.querySelector("#direction-switch");
const routeDirectionLabelEl = document.querySelector("#route-direction-label");

let nextRefreshAt = Date.now() + REFRESH_INTERVAL_MS;
let currentPayload = null;
let activeDirectionKey = null;

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

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function normalizeText(value) {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

function displayText(value) {
  return normalizeText(value);
}

function normalizePayload(payload) {
  if (payload?.directions && typeof payload.directions === "object") {
    return payload;
  }

  return {
    schemaVersion: 1,
    fetchedAt: payload?.fetchedAt ?? null,
    status: payload?.status ?? "error",
    message: payload?.message ?? "情報を取得できませんでした。",
    directionOrder: ["default"],
    defaultDirection: "default",
    directions: {
      default: {
        direction: {
          key: "default",
          label: "固定ルート",
          shortLabel: "固定",
        },
        ...(payload ?? {}),
      },
    },
  };
}

function getDirectionEntries(payload) {
  const keys = Array.isArray(payload?.directionOrder) && payload.directionOrder.length
    ? payload.directionOrder
    : Object.keys(payload?.directions ?? {});

  return keys
    .map((key) => [key, payload?.directions?.[key]])
    .filter(([, directionPayload]) => Boolean(directionPayload));
}

function getSelectedDirectionPayload(payload) {
  const entries = getDirectionEntries(payload);
  if (!entries.length) {
    return [null, null];
  }

  const validKey = entries.some(([key]) => key === activeDirectionKey)
    ? activeDirectionKey
    : payload.defaultDirection;
  const selectedKey = entries.some(([key]) => key === validKey) ? validKey : entries[0][0];
  activeDirectionKey = selectedKey;
  return [selectedKey, payload.directions[selectedKey]];
}

function renderDirectionSwitch(payload) {
  directionSwitchEl.innerHTML = "";
  const entries = getDirectionEntries(payload);

  if (entries.length <= 1) {
    directionSwitchEl.hidden = true;
    return;
  }

  directionSwitchEl.hidden = false;

  for (const [key, directionPayload] of entries) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = key === activeDirectionKey ? "direction-button active" : "direction-button";
    button.textContent = directionPayload.direction?.label ?? key;
    button.addEventListener("click", () => {
      activeDirectionKey = key;
      renderPayload(currentPayload);
    });
    directionSwitchEl.append(button);
  }
}

function formatSourceUpdated(value) {
  const text = displayText(value);
  return text || "--";
}

function formatDelayMinutes(value) {
  if (typeof value === "number") {
    return value === 0 ? "ほぼ定刻" : `${value}分遅れ`;
  }
  return "遅れ情報なし";
}

function formatTimeValue(value) {
  const text = displayText(value);
  return text || "--:--";
}

function buildQuickPeekMeta(journey) {
  if (!journey) {
    return "便なし";
  }

  const parts = [];
  if (journey.destination) {
    parts.push(`${displayText(journey.destination)} 行`);
  }
  if (typeof journey.delayMinutes === "number") {
    parts.push(formatDelayMinutes(journey.delayMinutes));
  } else if (journey.departureScheduledTime) {
    parts.push(`${journey.departureScheduledTime} 発予定`);
  }

  return parts.join(" / ") || "--";
}

function renderQuickPeeks(items) {
  const nextJourney = items[0] ?? null;
  const laterJourney = items[1] ?? null;

  quickPeekNextTimeEl.textContent = formatTimeValue(nextJourney?.expectedArrivalTime ?? nextJourney?.scheduledArrivalTime);
  quickPeekNextRouteEl.textContent = nextJourney?.route ? `系統 ${displayText(nextJourney.route)}` : "--";
  quickPeekNextMetaEl.textContent = buildQuickPeekMeta(nextJourney);

  quickPeekLaterTimeEl.textContent = formatTimeValue(laterJourney?.expectedArrivalTime ?? laterJourney?.scheduledArrivalTime);
  quickPeekLaterRouteEl.textContent = laterJourney?.route ? `系統 ${displayText(laterJourney.route)}` : "--";
  quickPeekLaterMetaEl.textContent = buildQuickPeekMeta(laterJourney);
}

function buildPrimaryHeadline(journey, featured = false) {
  if (journey?.expectedArrivalTime) {
    return featured ? `${journey.expectedArrivalTime} 着見込み` : `${journey.expectedArrivalTime} 到着見込み`;
  }

  if (journey?.scheduledArrivalTime) {
    return featured ? `${journey.scheduledArrivalTime} 到着予定` : `${journey.scheduledArrivalTime} 着予定`;
  }

  return displayText(journey?.destination ?? "接近情報を確認中");
}

function buildStatusLine(journey) {
  const headline = displayText(journey?.headline);
  const parts = [];

  if (headline.includes("運行中")) {
    parts.push("現在運行中");
  } else if (journey?.departureScheduledTime) {
    parts.push(`${journey.departureScheduledTime} 発予定`);
  } else if (headline && !headline.includes("あと")) {
    parts.push(headline);
  }

  if (journey?.scheduledArrivalTime) {
    parts.push(`時刻表 ${journey.scheduledArrivalTime}`);
  }

  if (typeof journey?.delayMinutes === "number") {
    parts.push(formatDelayMinutes(journey.delayMinutes));
  }

  if (journey?.expectedArrivalTime) {
    parts.push(`到着見込み ${journey.expectedArrivalTime}`);
  }

  return parts.filter(Boolean).join(" / ");
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
    item.textContent = displayText(entry);
    detailListEl.append(item);
  }
}

function renderNoticeList(items) {
  noticeListEl.innerHTML = "";

  const notices = Array.isArray(items) ? items.filter(Boolean) : [];
  if (!notices.length) {
    const item = document.createElement("li");
    item.textContent = "追加の注意事項はありません。";
    noticeListEl.append(item);
    return;
  }

  for (const entry of notices) {
    const item = document.createElement("li");
    item.textContent = displayText(entry);
    noticeListEl.append(item);
  }
}

function buildJourneyCardMarkup(journey, featured = false) {
  const vehicleBadge = journey.vehicleMark && journey.accessibilityLabel
    ? `${journey.vehicleMark} ${journey.accessibilityLabel}`
    : journey.vehicleMark || "";
  const summary = [journey.destination ? `${displayText(journey.destination)} 行` : "", journey.via ? `${displayText(journey.via)} 経由` : ""]
    .filter(Boolean)
    .join(" / ");
  const primaryHeadline = buildPrimaryHeadline(journey, featured);
  const statusLine = buildStatusLine(journey);
  const stops = Array.isArray(journey.stops) ? journey.stops : [];
  const stopMarkup = stops
    .map((stop, index) => {
      const className = index === stops.length - 1 ? "stop-chip current" : "stop-chip";
      return `<span class="${className}">${escapeHtml(displayText(stop))}</span>`;
    })
    .join("");

  return `
    <article class="journey-card${featured ? " featured" : ""}">
      <div class="journey-bar">
        <span class="journey-rank">早い順 ${escapeHtml(journey.rank)}</span>
        <span class="journey-route">${escapeHtml(journey.route ?? "--")}</span>
        ${vehicleBadge ? `<span class="journey-vehicle">${escapeHtml(vehicleBadge)}</span>` : ""}
      </div>
      <${featured ? "h3" : "h4"} class="journey-headline">${escapeHtml(primaryHeadline)}</${featured ? "h3" : "h4"}>
      ${summary ? `<p class="journey-destination">${escapeHtml(summary)}</p>` : ""}
      ${statusLine ? `<p class="journey-subline">${escapeHtml(statusLine)}</p>` : ""}
      <dl class="journey-meta">
        <div><dt>到着見込み</dt><dd>${escapeHtml(formatTimeValue(journey.expectedArrivalTime))}</dd></div>
        <div><dt>遅れ見込み</dt><dd>${escapeHtml(formatDelayMinutes(journey.delayMinutes))}</dd></div>
        <div><dt>所要</dt><dd>${escapeHtml(normalizeText([journey.duration, journey.durationNote].filter(Boolean).join(" ")) || "--")}</dd></div>
        <div><dt>現金</dt><dd>${escapeHtml(journey.cashFare ?? "--")}</dd></div>
        <div><dt>IC</dt><dd>${escapeHtml(journey.icFare ?? "--")}</dd></div>
        <div><dt>車両</dt><dd>${escapeHtml(journey.vehicleNumber ?? "--")}</dd></div>
      </dl>
      ${stopMarkup ? `<div class="journey-stops">${stopMarkup}</div>` : ""}
      ${journey.updatedAtText ? `<p class="journey-updated">${escapeHtml(normalizeText(journey.updatedAtText))}</p>` : ""}
    </article>
  `;
}

function renderJourneys(journeys) {
  const items = Array.isArray(journeys) ? journeys : [];
  const featured = items[0];
  const remaining = items.slice(1);

  renderQuickPeeks(items);
  journeyCountEl.textContent = `${items.length}件`;
  journeyCountInlineEl.textContent = items.length > 0 ? `${items.length}件を表示` : "便なし";
  nextJourneyNoteEl.textContent = featured?.route ? `系統 ${displayText(featured.route)} / ${displayText(featured.destination ?? "行先不明")}` : "--";
  sourceUpdatedEl.textContent = formatSourceUpdated(featured?.updatedAtText);
  scheduledArrivalTimeEl.textContent = formatTimeValue(featured?.scheduledArrivalTime);
  delayMinutesEl.textContent = formatDelayMinutes(featured?.delayMinutes);
  expectedArrivalTimeEl.textContent = formatTimeValue(featured?.expectedArrivalTime);

  if (!featured) {
    nextJourneySectionEl.hidden = true;
    journeyListSectionEl.hidden = true;
    nextJourneyEl.textContent = "現在表示できる便はありません。";
    journeyGridEl.innerHTML = "";
    return;
  }

  nextJourneySectionEl.hidden = false;
  journeyListSectionEl.hidden = remaining.length === 0;
  nextJourneyEl.innerHTML = buildJourneyCardMarkup(featured, true);
  journeyGridEl.innerHTML = remaining.map((journey) => buildJourneyCardMarkup(journey)).join("");
}

function renderPayload(payload) {
  currentPayload = normalizePayload(payload);
  const [, selected] = getSelectedDirectionPayload(currentPayload);
  renderDirectionSwitch(currentPayload);

  if (!selected) {
    statusMessageEl.textContent = "表示できる方向がありません。";
    setTone("tone-error", "取得失敗");
    return;
  }

  const journeys = Array.isArray(selected.journeys) ? selected.journeys : [];
  const overview = Array.isArray(selected.overview) ? selected.overview : [];

  routeDirectionLabelEl.textContent = displayText(selected.direction?.shortLabel ?? selected.direction?.label ?? "固定ルート");
  fromStopEl.textContent = displayText(selected.route?.fromStop?.name ?? "出発停留所");
  toStopEl.textContent = displayText(selected.route?.toStop?.name ?? "目的停留所");
  sourceLinkEl.href = selected.source?.url ?? "https://real.kanachu.jp/pc/top";

  statusMessageEl.textContent = journeys[0]?.expectedArrivalTime
    ? `${journeys[0].expectedArrivalTime} 着見込み`
    : displayText(selected.message ?? currentPayload.message ?? "情報を取得できませんでした。");
  updatedAtEl.textContent = formatDateTime(selected.fetchedAt ?? currentPayload.fetchedAt);
  overviewTextEl.textContent = displayText(overview.join(" "));

  if (selected.status === "error") {
    setTone("tone-error", "取得失敗");
  } else if (selected.hasLiveData) {
    setTone("tone-ok", "運行情報あり");
  } else {
    setTone("tone-warn", "接近情報なし");
  }

  renderJourneys(journeys);
  renderNoticeList(selected.notices);
  renderDetails(selected.details);
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
      directionOrder: ["forward", "reverse"],
      defaultDirection: activeDirectionKey ?? "forward",
      directions: {
        forward: {
          status: "error",
          message: "status.json を読めませんでした。",
          fetchedAt: null,
          hasLiveData: false,
          direction: { key: "forward", label: "出発→目的", shortLabel: "順方向" },
          route: {
            fromStop: { name: "出発停留所" },
            toStop: { name: "目的停留所" },
          },
          source: { url: "https://real.kanachu.jp/pc/top" },
          overview: [],
          notices: [],
          journeys: [],
          details: [error instanceof Error ? error.message : String(error)],
        },
        reverse: {
          status: "error",
          message: "status.json を読めませんでした。",
          fetchedAt: null,
          hasLiveData: false,
          direction: { key: "reverse", label: "目的→出発", shortLabel: "逆方向" },
          route: {
            fromStop: { name: "目的停留所" },
            toStop: { name: "出発停留所" },
          },
          source: { url: "https://real.kanachu.jp/pc/top" },
          overview: [],
          notices: [],
          journeys: [],
          details: [error instanceof Error ? error.message : String(error)],
        },
      },
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
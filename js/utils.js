// Shared DOM + formatting utilities used across the app.

export function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

const STATUS_CLASS = {
  online: "badge-ok",
  degraded: "badge-warn",
  offline: "badge-down",
};

export function statusBadge(status) {
  const badge = el("span", `badge ${STATUS_CLASS[status] || "badge-warn"}`, status);
  return badge;
}

// Render a list of items into a <ul>, mapping each item to a `.card` <li>.
export function renderCards(listEl, items, toCard) {
  listEl.replaceChildren(...items.map(toCard));
}

export function setStatus(statusEl, count, label) {
  statusEl.textContent = `${count} ${label}`;
}

export function formatTime(date = new Date()) {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

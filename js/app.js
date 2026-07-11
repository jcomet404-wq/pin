import { el, statusBadge, renderCards, setStatus, formatTime } from "./utils.js";
import { nodes, signals } from "./data.js";

function nodeCard(node) {
  const li = el("li", "card");
  const left = el("div");
  left.append(el("div", "card-title", node.name), el("div", "card-meta", node.region));
  li.append(left, statusBadge(node.status));
  return li;
}

function signalCard(signal) {
  const li = el("li", "card");
  const left = el("div");
  left.append(el("div", "card-title", signal.type), el("div", "card-meta", signal.source));
  li.append(left, statusBadge(signal.status));
  return li;
}

function initSection(listId, statusId, items, toCard, label) {
  renderCards(document.getElementById(listId), items, toCard);
  setStatus(document.getElementById(statusId), items.length, label);
}

function startClock() {
  const clock = document.getElementById("clock");
  const tick = () => (clock.textContent = `Network time · ${formatTime()}`);
  tick();
  setInterval(tick, 1000);
}

initSection("nodes-list", "nodes-status", nodes, nodeCard, "nodes registered");
initSection("signals-list", "signals-status", signals, signalCard, "active signals");
startClock();

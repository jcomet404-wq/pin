const map = L.map("map", { center: [0.25, 32.75], zoom: 9, worldCopyJump: true });
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

// Region-of-interest drawing (rectangle).
const drawnItems = new L.FeatureGroup().addTo(map);
const drawControl = new L.Control.Draw({
  draw: {
    rectangle: { shapeOptions: { color: "#16a34a", weight: 2 } },
    polygon: false, polyline: false, circle: false, marker: false, circlemarker: false,
  },
  edit: { featureGroup: drawnItems, edit: false },
});
map.addControl(drawControl);

let bbox = null; // [minLon, minLat, maxLon, maxLat]
let overlay = null;

const $ = (id) => document.getElementById(id);
const computeBtn = $("compute");
const statusEl = $("status");

function setStatus(msg, kind) {
  statusEl.textContent = msg || "";
  statusEl.className = kind || "";
}

map.on(L.Draw.Event.CREATED, (e) => {
  drawnItems.clearLayers();
  drawnItems.addLayer(e.layer);
  const b = e.layer.getBounds();
  bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()];
  computeBtn.disabled = false;
  computeBtn.textContent = "Compute layer";
  setStatus(`Region: ${bbox.map((v) => v.toFixed(3)).join(", ")}`);
});

// Populate the layer dropdown from the API.
async function loadStyles() {
  const res = await fetch("/api/styles");
  const styles = await res.json();
  const sel = $("index");
  for (const [name, s] of Object.entries(styles)) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = s.label;
    sel.appendChild(opt);
  }
  togglePopFields();
}

function togglePopFields() {
  const isPop = $("index").value === "population";
  $("pop-fields").classList.toggle("hidden", !isPop);
}
$("index").addEventListener("change", togglePopFields);

$("opacity").addEventListener("input", (e) => {
  if (overlay) overlay.setOpacity(parseFloat(e.target.value));
});

computeBtn.addEventListener("click", async () => {
  if (!bbox) return;
  const index = $("index").value;
  const body = {
    index,
    bbox,
    datetime: $("datetime").value,
    resolution: parseFloat($("resolution").value),
    max_cloud_cover: parseFloat($("cloud").value),
    iso3: $("iso3").value || null,
    year: $("year").value ? parseInt($("year").value, 10) : null,
  };

  computeBtn.disabled = true;
  setStatus("Computing… fetching imagery and coloring the layer.", "loading");
  try {
    const res = await fetch("/api/compute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "request failed");
    }
    const data = await res.json();
    if (overlay) map.removeLayer(overlay);
    overlay = L.imageOverlay(data.image, data.bounds, {
      opacity: parseFloat($("opacity").value),
    }).addTo(map);
    map.fitBounds(data.bounds);
    showLegend(data);
    setStatus("Done.", "");
  } catch (e) {
    setStatus(e.message, "error");
  } finally {
    computeBtn.disabled = false;
  }
});

function showLegend(data) {
  $("legend").classList.remove("hidden");
  $("legend-title").textContent = data.label;
  $("legend-img").src = `/api/legend/${data.index}`;
  $("legend-min").textContent = data.vmin;
  $("legend-max").textContent = data.vmax;
  const s = data.stats || {};
  $("stats").textContent =
    s.mean == null
      ? "No valid pixels in region."
      : `min ${s.min.toFixed(2)} · mean ${s.mean.toFixed(2)} · max ${s.max.toFixed(2)}`;
}

loadStyles();

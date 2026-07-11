# pin

planetary inteligence network

A small static dashboard for the Planetary Intelligence Network. No build step or
dependencies — plain HTML, CSS, and ES modules.

## Run it

Because it uses ES modules, open it through a local web server (not `file://`):

```bash
# Python 3 (built in on most systems)
python3 -m http.server 8000
```

Then open http://localhost:8000 in your browser.

Any static server works, e.g. `npx serve` or `npx http-server`.

## Structure

- `index.html` — page markup
- `styles.css` — styling
- `js/utils.js` — shared DOM/formatting utilities (`el`, `statusBadge`, `renderCards`, …)
- `js/data.js` — mock node/signal data
- `js/app.js` — wires data into the page using the shared utilities

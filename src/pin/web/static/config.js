// Runtime configuration for the PIN web map.
//
// apiBase = base URL of the PIN compute backend.
//   - Leave "" when the backend serves this page itself (local `pin serve`).
//   - For a static deploy (e.g. Vercel), set it to your backend container URL,
//     e.g. "https://pin-backend.fly.dev".
// You can also override at runtime with a ?api=<url> query parameter.
window.PIN_CONFIG = {
  apiBase: "",
};

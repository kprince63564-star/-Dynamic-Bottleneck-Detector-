// In local development, Vite's dev-server proxy (see vite.config.js) forwards
// "/api/..." requests to http://localhost:8000, so a relative path works fine.
//
// Once deployed, the frontend (e.g. on Vercel) and backend (e.g. on Render)
// live on two different domains, so relative paths won't reach the backend
// anymore. VITE_API_URL is set as an environment variable on the hosting
// platform (see README's deployment section) to the backend's live URL,
// e.g. "https://dbd-backend.onrender.com".
const API_BASE = import.meta.env.VITE_API_URL || "";

export function apiUrl(path) {
  // path should start with "/api/..."
  return `${API_BASE}${path}`;
}

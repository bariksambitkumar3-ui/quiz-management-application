// When Django serves the site (port 8000), call the API on the same address.
// For a separate frontend deployment (Netlify/Vercel), put your API URL in the else branch.
window.API_BASE = location.port === "8000" ? "/api" : "http://127.0.0.1:8000/api";
window.QUIZ_API_BASE = window.API_BASE;

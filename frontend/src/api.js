// Both backend services are reached through RELATIVE paths -- /prompts
// and /reviews -- never a hardcoded host or port. In production, nginx
// is what decides where each prefix actually goes: /prompts/* -> 8000
// (prompt-service), /reviews/* -> 8001 (review-service). See nginx.conf.
//
// During local dev (npm run dev, no nginx yet), vite.config.js's proxy
// section does the same job, so this code works unchanged either way --
// exactly the same pattern as the notes app.

async function request(base, path, options) {
  const res = await fetch(base + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = Array.isArray(body.detail)
      ? body.detail.map(d => d.msg).join(", ")
      : body.detail;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const promptsApi = {
  list: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request("/prompts", query ? `?${query}` : "");
  },
  get: (id) => request("/prompts", `/${id}`),
  create: (data) => request("/prompts", "", { method: "POST", body: JSON.stringify(data) }),
  update: (id, data) => request("/prompts", `/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  remove: (id) => request("/prompts", `/${id}`, { method: "DELETE" }),
};

export const reviewsApi = {
  listForPrompt: (promptId) => request("/reviews", `?prompt_id=${promptId}`),
  create: (data) => request("/reviews", "", { method: "POST", body: JSON.stringify(data) }),
  summary: (promptId) => request("/reviews", `/${promptId}/summary`),
};

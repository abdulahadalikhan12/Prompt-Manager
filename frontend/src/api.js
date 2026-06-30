// Both backend services are reached through RELATIVE paths -- /prompts,
// /chats, and /reviews -- never a hardcoded host or port. In production,
// nginx decides where each prefix actually goes (see nginx.conf). During
// local dev, vite.config.js's proxy section does the same job.

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

// Week 2: chats live under prompt-service too (same backend, port 8000),
// just a different path prefix -- /chats rather than /prompts.
export const chatsApi = {
  execute: (promptId, model = null) =>
    request("/prompts", `/${promptId}/execute`, { method: "POST", body: JSON.stringify({ model }) }),
  followUp: (chatId, content, model = null) =>
    request("/chats", `/${chatId}/messages`, { method: "POST", body: JSON.stringify({ content, model }) }),
  list: (promptId = null) =>
    request("/chats", promptId ? `?prompt_id=${promptId}` : ""),
  get: (chatId) => request("/chats", `/${chatId}`),
  summarize: (chatId) => request("/chats", `/${chatId}/summary`, { method: "POST" }),
  remove: (chatId) => request("/chats", `/${chatId}`, { method: "DELETE" }),
};

export const reviewsApi = {
  listForPrompt: (promptId) => request("/reviews", `?prompt_id=${promptId}`),
  listForChat: (chatId) => request("/reviews", `?chat_id=${chatId}`),
  create: (data) => request("/reviews", "", { method: "POST", body: JSON.stringify(data) }),
  summaryForPrompt: (promptId) => request("/reviews", `/${promptId}/summary`),
  summaryForChat: (chatId) => request("/reviews", `/chat/${chatId}/summary`),
};

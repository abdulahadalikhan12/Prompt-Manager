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
      ? body.detail.map((d) => d.msg).join(", ")
      : body.detail;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// Prompts are still owned by prompt-service; the user just never sees
// them directly anymore -- every new chat auto-creates one under the
// hood (see chatsApi.start). These endpoints stay available for any
// admin/inspection tooling.
export const promptsApi = {
  list: () => request("/prompts", ""),
  get: (id) => request("/prompts", `/${id}`),
  remove: (id) => request("/prompts", `/${id}`, { method: "DELETE" }),
};

export const chatsApi = {
  // New: start a chat from a free-form first message. Backend auto-
  // creates the underlying prompt -- the frontend no longer asks the
  // user to pick one from a library. `attachments` (optional) lets
  // the caller seed the brand-new chat with PDFs/DOCX already uploaded
  // to document-service, so the very first LLM turn already sees them.
  start: (content, model = null, attachments = []) =>
    request("/chats", "", {
      method: "POST",
      body: JSON.stringify({ content, model, attachments }),
    }),
  followUp: (chatId, content, model = null) =>
    request("/chats", `/${chatId}/messages`, { method: "POST", body: JSON.stringify({ content, model }) }),
  list: () => request("/chats", ""),
  get: (chatId) => request("/chats", `/${chatId}`),
  summarize: (chatId) => request("/chats", `/${chatId}/summary`, { method: "POST" }),
  remove: (chatId) => request("/chats", `/${chatId}`, { method: "DELETE" }),
};

// document-service runs on a separate port (8003) and is proxied at
// /documents by both vite (dev) and nginx (prod). The upload endpoint
// is the only one we don't go through `request()` for, because it
// needs multipart/form-data instead of JSON.
export const documentsApi = {
  upload: async (file) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/documents", { method: "POST", body: form });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      const detail = Array.isArray(body.detail)
        ? body.detail.map((d) => d.msg).join(", ")
        : body.detail;
      throw new Error(detail || `Upload failed (${res.status})`);
    }
    return res.json();
  },
  list: () => request("/documents", ""),
  get: (id) => request("/documents", `/${id}`),
  remove: (id) => request("/documents", `/${id}`, { method: "DELETE" }),
};

// Per-chat attachment endpoints live on prompt-service (it owns the
// chat_documents table), NOT on document-service -- only the binary
// + extracted text live in document-service.
export const chatDocumentsApi = {
  list: (chatId) => request("/chats", `/${chatId}/documents`),
  attach: (chatId, body) =>
    request("/chats", `/${chatId}/documents`, { method: "POST", body: JSON.stringify(body) }),
  detach: (chatId, documentId) =>
    request("/chats", `/${chatId}/documents/${documentId}`, { method: "DELETE" }),
};

export const reviewsApi = {
  listForPrompt: (promptId) => request("/reviews", `?prompt_id=${promptId}`),
  listForChat: (chatId) => request("/reviews", `?chat_id=${chatId}`),
  listForMessage: (messageId) => request("/reviews", `?message_id=${messageId}`),
  create: (data) => request("/reviews", "", { method: "POST", body: JSON.stringify(data) }),
  summaryForPrompt: (promptId) => request("/reviews", `/${promptId}/summary`),
  summaryForChat: (chatId) => request("/reviews", `/chat/${chatId}/summary`),
  summaryForMessage: (messageId) => request("/reviews", `/message/${messageId}/summary`),
};

import { useState, useEffect } from "react";
import { chatsApi } from "./api";

// Lists every past chat across all prompts, with its auto-generated
// summary (if one exists) as the short description, so past
// conversations can be found without going through their originating
// prompt. Clicking a row opens that chat.
export default function HistoryPage({ onOpenChat }) {
  const [chats, setChats] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadChats();
  }, []);

  async function loadChats() {
    try {
      const data = await chatsApi.list();
      setChats(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(e, chatId) {
    e.stopPropagation();
    if (!window.confirm("Delete this chat?")) return;
    try {
      await chatsApi.remove(chatId);
      loadChats();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="history-page">
      <h2>Chat History</h2>
      {error && <div className="error-banner">{error}</div>}
      {chats.length === 0 && !error && <p className="empty-state">No chats yet -- execute a prompt to start one.</p>}

      {chats.map((c) => (
        <div className="history-row" key={c.id} onClick={() => onOpenChat(c.id)}>
          <div className="history-row-main">
            <strong>{c.title || "Untitled chat"}</strong>
            <p className="history-description">
              {c.summary || "No summary yet -- open the chat and click Summarize."}
            </p>
          </div>
          <div className="history-row-meta">
            <span className="token-badge">{c.total_tokens} tokens</span>
            <span className="history-date">{new Date(c.created_at).toLocaleDateString()}</span>
            <button onClick={(e) => handleDelete(e, c.id)}>Delete</button>
          </div>
        </div>
      ))}
    </div>
  );
}

import { useState, useEffect } from "react";
import { chatsApi } from "./api";
import ReviewBlock from "./ReviewBlock";

// Two screens stacked into one component (no router yet -- this is
// the only place in the app that has a drill-down, so a local view
// switch is leaner than wiring a router for one nav step):
//   - list mode: every chat as a row, with its chat-level review form
//   - detail mode: opened chat shown turn-by-turn; each user message
//     is labelled "Prompt 1, 2, 3..." and gets its own ReviewBlock
//     targeted at the message id (target_type = "message")
export default function ReviewerPage() {
  const [chats, setChats] = useState([]);
  const [openChat, setOpenChat] = useState(null);   // full ChatOut, null = list view
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => { loadChats(); }, []);

  async function loadChats() {
    try {
      const c = await chatsApi.list();
      setChats(c);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleOpen(chatId) {
    setLoadingDetail(true);
    setError(null);
    try {
      const data = await chatsApi.get(chatId);
      setOpenChat(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingDetail(false);
    }
  }

  if (openChat) {
    // index user messages 1..N so the labels match "Prompt 1, 2, 3..."
    let userIdx = 0;
    return (
      <div className="reviewer-page">
        <div className="reviewer-inner">
          <div className="library-header">
            <div>
              <button className="icon-btn" onClick={() => setOpenChat(null)}>← Back to chats</button>
              <h2 style={{ marginTop: 10 }}>{openChat.title || "Untitled chat"}</h2>
              <p className="desc" style={{ color: "var(--text-muted)" }}>
                {openChat.total_tokens} tokens · {openChat.messages.length} messages
              </p>
            </div>
          </div>

          {error && <div className="error-banner">{error}</div>}

          {openChat.messages
            .filter((m) => m.role === "user")
            .map((m) => {
              userIdx += 1;
              return (
                <ReviewBlock
                  key={m.id}
                  targetType="message"
                  targetId={m.id}
                  chatId={openChat.id}
                  title={`Prompt ${userIdx}`}
                  subtitle={m.content}
                  dense
                />
              );
            })}

          {openChat.messages.filter((m) => m.role === "user").length === 0 && (
            <div className="empty-state">No user prompts in this chat.</div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="reviewer-page">
      <div className="reviewer-inner">
        <div className="library-header">
          <h2>Reviewer</h2>
        </div>

        {error && <div className="error-banner">{error}</div>}
        {loadingDetail && <div className="empty-state">Loading…</div>}

        {chats.length === 0 ? (
          <div className="empty-state">No chats to review yet.</div>
        ) : (
          chats.map((c) => (
            <div key={c.id} className="reviewer-chat-card">
              <ReviewBlock
                targetType="chat"
                targetId={c.id}
                title={c.title || "Untitled chat"}
                subtitle={c.summary || `${c.total_tokens} tokens · ${new Date(c.created_at).toLocaleString()}`}
              />
              <button className="icon-btn open-chat-btn" onClick={() => handleOpen(c.id)}>
                Review individual prompts →
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

import { chatsApi } from "./api";

export default function Sidebar({
  chats,
  activeChatId,
  isNewChat,
  onSelectChat,
  onNewChat,
  onChatsChanged,
}) {
  async function handleDelete(e, chatId) {
    e.stopPropagation();
    if (!window.confirm("Delete this chat?")) return;
    try {
      await chatsApi.remove(chatId);
      onChatsChanged?.(chatId);
    } catch (err) {
      alert(err.message);
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-title">Conversations</div>
      </div>

      <button
        className={`new-chat-btn ${isNewChat ? "active" : ""}`}
        onClick={onNewChat}
      >
        <span className="plus">+</span>
        <span>New chat</span>
      </button>

      <div className="sidebar-section-label">Recent</div>

      <div className="chat-list">
        {chats.length === 0 && (
          <div className="chat-list-empty">No chats yet. Click "New chat" to begin.</div>
        )}
        {chats.map((c) => (
          <div
            key={c.id}
            className={`chat-row ${activeChatId === c.id ? "active" : ""}`}
            onClick={() => onSelectChat(c.id)}
            title={c.title || "Untitled"}
          >
            <span className="title">{c.title || "Untitled chat"}</span>
            <button className="row-del" onClick={(e) => handleDelete(e, c.id)}>
              ×
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}

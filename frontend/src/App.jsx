import { useState, useEffect } from "react";
import { chatsApi } from "./api";
import Sidebar from "./Sidebar";
import ChatView from "./ChatView";
import ReviewerPage from "./ReviewerPage";
import "./App.css";

export default function App() {
  const [tab, setTab] = useState("user");          // "user" | "reviewer"
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);  // null => "new chat" mode
  const [error, setError] = useState(null);

  useEffect(() => { refreshChats(); }, []);

  async function refreshChats() {
    try {
      const c = await chatsApi.list();
      setChats(c);
    } catch (err) {
      setError(err.message);
    }
  }

  function startNewChat() {
    setActiveChatId(null);  // null = empty composer; first send creates the chat
  }

  function handleChatCreated(chat) {
    setActiveChatId(chat.id);
    refreshChats();
  }

  function handleChatDeleted(deletedId) {
    refreshChats();
    if (deletedId === activeChatId) setActiveChatId(null);
  }

  return (
    <div className="app">
      <div className="top-tabs">
        <div className="brand">Prompt Manager</div>
        <button
          className={`tab ${tab === "user" ? "active" : ""}`}
          onClick={() => setTab("user")}
        >
          User
        </button>
        <button
          className={`tab ${tab === "reviewer" ? "active" : ""}`}
          onClick={() => setTab("reviewer")}
        >
          Reviewer
        </button>
      </div>

      <div className="app-body">
        {tab === "user" ? (
          <>
            <Sidebar
              chats={chats}
              activeChatId={activeChatId}
              isNewChat={activeChatId === null}
              onSelectChat={(id) => setActiveChatId(id)}
              onNewChat={startNewChat}
              onChatsChanged={handleChatDeleted}
            />

            {error && <div className="error-banner">{error}</div>}

            <ChatView
              key={activeChatId || "new"}
              chatId={activeChatId}
              onChatCreated={handleChatCreated}
              onChatChanged={refreshChats}
            />
          </>
        ) : (
          <ReviewerPage />
        )}
      </div>
    </div>
  );
}

import { useState, useEffect } from "react";
import { promptsApi, chatsApi } from "./api";
import PromptForm from "./PromptForm";
import ReviewBlock from "./ReviewBlock";
import ChatView from "./ChatView";
import HistoryPage from "./HistoryPage";
import "./App.css";

function App() {
  const [view, setView] = useState("prompts"); // "prompts" | "history"
  const [prompts, setPrompts] = useState([]);
  const [error, setError] = useState(null);
  const [openChatId, setOpenChatId] = useState(null);
  const [executingId, setExecutingId] = useState(null);

  useEffect(() => {
    loadPrompts();
  }, []);

  async function loadPrompts() {
    try {
      const data = await promptsApi.list();
      setPrompts(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCreate(payload) {
    try {
      await promptsApi.create(payload);
      loadPrompts();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this prompt?")) return;
    try {
      await promptsApi.remove(id);
      loadPrompts();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleExecute(promptId) {
    setExecutingId(promptId);
    setError(null);
    try {
      const chat = await chatsApi.execute(promptId);
      setOpenChatId(chat.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setExecutingId(null);
    }
  }

  return (
    <div className="app">
      <div className="app-header">
        <h1>Prompt Manager</h1>
        <div className="view-tabs">
          <button className={view === "prompts" ? "tab active" : "tab"} onClick={() => setView("prompts")}>
            Prompts
          </button>
          <button className={view === "history" ? "tab active" : "tab"} onClick={() => setView("history")}>
            History
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {openChatId && (
        <div className="chat-overlay">
          <ChatView chatId={openChatId} onClose={() => { setOpenChatId(null); loadPrompts(); }} />
        </div>
      )}

      {view === "prompts" && (
        <>
          <PromptForm onCreate={handleCreate} />

          {prompts.length === 0 && <p className="empty-state">No prompts yet.</p>}

          {prompts
            .slice()
            .reverse()
            .map((prompt) => (
              <div className="prompt-card" key={prompt.id}>
                <h3>{prompt.name}</h3>
                {prompt.description && <p>{prompt.description}</p>}
                <p>{prompt.content}</p>
                {prompt.tags && (
                  <div className="tags">
                    {prompt.tags.split(",").map((t) => (
                      <span className="tag" key={t}>{t.trim()}</span>
                    ))}
                  </div>
                )}
                <div className="card-actions">
                  <button
                    className="primary"
                    onClick={() => handleExecute(prompt.id)}
                    disabled={executingId === prompt.id}
                  >
                    {executingId === prompt.id ? "Running..." : "Execute"}
                  </button>
                  <button onClick={() => handleDelete(prompt.id)}>Delete</button>
                </div>
                <ReviewBlock promptId={prompt.id} />
              </div>
            ))}
        </>
      )}

      {view === "history" && <HistoryPage onOpenChat={(id) => setOpenChatId(id)} />}
    </div>
  );
}

export default App;

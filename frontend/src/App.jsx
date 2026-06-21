import { useState, useEffect } from "react";
import { promptsApi } from "./api";
import PromptForm from "./PromptForm";
import ReviewBlock from "./ReviewBlock";
import "./App.css";

function App() {
  const [prompts, setPrompts] = useState([]);
  const [error, setError] = useState(null);

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

  return (
    <div className="app">
      <h1>Prompt Manager</h1>

      {error && <div className="error-banner">{error}</div>}

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
              <button onClick={() => handleDelete(prompt.id)}>Delete</button>
            </div>
            <ReviewBlock promptId={prompt.id} />
          </div>
        ))}
    </div>
  );
}

export default App;

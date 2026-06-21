import { useState } from "react";

// A small, self-contained "create a prompt" form. It only knows how to
// collect input and call onCreate -- it has NO idea how that data
// actually reaches the backend. That's App.jsx's job. This separation
// means PromptForm could be reused or tested without any API involved.
export default function PromptForm({ onCreate }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");
  const [modelTarget, setModelTarget] = useState("");

  function handleSubmit() {
    if (!name.trim() || !content.trim()) return;
    onCreate({
      name,
      description: description || null,
      content,
      tags: tags || null,
      model_target: modelTarget || null,
    });
    setName(""); setDescription(""); setContent(""); setTags(""); setModelTarget("");
  }

  return (
    <div className="form-grid">
      <div>
        <label>Name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Cold Email Opener v2" />
      </div>
      <div>
        <label>Description</label>
        <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional one-line summary" />
      </div>
      <div>
        <label>Content</label>
        <textarea rows={3} value={content} onChange={(e) => setContent(e.target.value)} placeholder="The full prompt text..." />
      </div>
      <div>
        <label>Tags (comma-separated)</label>
        <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="sales,outbound" />
      </div>
      <div>
        <label>Model target</label>
        <input value={modelTarget} onChange={(e) => setModelTarget(e.target.value)} placeholder="gpt-4o, claude, etc." />
      </div>
      <button className="primary" onClick={handleSubmit}>Create Prompt</button>
    </div>
  );
}

import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { chatsApi, chatDocumentsApi, documentsApi } from "./api";

const MAX_ATTACHMENTS = 3;

// A single panel that does double duty:
//   1. When chatId is null, it's the "new chat" composer -- empty state
//      with a prompt that creates a chat on first send (POST /chats).
//      Attached docs in this state live ONLY in pendingAttachments
//      until the chat is created.
//   2. When chatId is set, it's the live conversation view. Attached
//      docs come from the chat itself (chat.documents) and new uploads
//      hit POST /chats/{id}/documents directly.
export default function ChatView({ chatId, onChatCreated, onChatChanged }) {
  const [chat, setChat] = useState(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [summarizing, setSummarizing] = useState(false);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState([]); // only used pre-chat
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    setError(null);
    setPendingAttachments([]);
    if (chatId) {
      loadChat();
    } else {
      setChat(null);
    }
  }, [chatId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat?.messages?.length, sending]);

  const isNew = !chatId;
  const attachedDocs = isNew ? pendingAttachments : (chat?.documents || []);

  function autoGrow(el) {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  }

  async function loadChat() {
    try {
      const data = await chatsApi.get(chatId);
      setChat(data);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleFilePicked(e) {
    const file = e.target.files?.[0];
    e.target.value = "";  // reset so the same file can be picked again later
    if (!file) return;

    if (attachedDocs.length >= MAX_ATTACHMENTS) {
      setError(`At most ${MAX_ATTACHMENTS} documents per chat.`);
      return;
    }

    setError(null);
    setUploading(true);
    try {
      const doc = await documentsApi.upload(file);
      // doc = { id, filename, kind, size_bytes, char_count, uploaded_at, text }
      if (isNew) {
        setPendingAttachments((prev) => [
          ...prev,
          {
            document_id: doc.id,
            filename: doc.filename,
            extracted_text: doc.text,
          },
        ]);
      } else {
        await chatDocumentsApi.attach(chatId, {
          document_id: doc.id,
          filename: doc.filename,
          extracted_text: doc.text,
        });
        await loadChat();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleDetach(documentId) {
    if (isNew) {
      setPendingAttachments((prev) => prev.filter((d) => d.document_id !== documentId));
      return;
    }
    try {
      await chatDocumentsApi.detach(chatId, documentId);
      await loadChat();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSend() {
    const content = draft.trim();
    if (!content || sending) return;
    setSending(true);
    setError(null);
    setDraft("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    try {
      if (!chatId) {
        const created = await chatsApi.start(content, null, pendingAttachments);
        setPendingAttachments([]);
        onChatCreated?.(created);
      } else {
        await chatsApi.followUp(chatId, content);
        await loadChat();
        onChatChanged?.();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  async function handleSummarize() {
    if (!chatId) return;
    setSummarizing(true);
    setError(null);
    try {
      await chatsApi.summarize(chatId);
      await loadChat();
      onChatChanged?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setSummarizing(false);
    }
  }

  const headerTitle = isNew ? "New chat" : (chat?.title || "Loading…");
  const tokenTotals = computeTotals(chat);

  return (
    <div className="main">
      <div className="main-header">
        <div>
          <span className="title">{headerTitle}</span>
          {chat && !isNew && tokenTotals && (
            <span className="meta">
              · sys {tokenTotals.system} · in {tokenTotals.input} · out {tokenTotals.output}
            </span>
          )}
        </div>
        {!isNew && chat && (
          <div className="header-actions">
            <button className="icon-btn" onClick={handleSummarize} disabled={summarizing}>
              {summarizing ? "Summarizing…" : "Summarize"}
            </button>
          </div>
        )}
      </div>

      {attachedDocs.length > 0 && (
        <div className="attachment-bar">
          {attachedDocs.map((d) => (
            <span className="attachment-pill" key={d.document_id || d.id}>
              <span className="att-icon">▤</span>
              <span className="att-name" title={d.filename}>{d.filename}</span>
              <button
                className="att-remove"
                onClick={() => handleDetach(d.document_id || d.id)}
                aria-label="Remove attachment"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {chat?.summary && (
        <div className="summary-panel">
          <strong>Summary</strong> · {chat.summary}
        </div>
      )}

      {error && <div className="error-banner">{error}</div>}

      <div className="chat-scroll">
        <div className="chat-inner">
          {isNew && (
            <div className="welcome" style={{ padding: "60px 20px" }}>
              <h2>What can I help with?</h2>
              <p>Attach PDFs with the paperclip, or type a message to start.</p>
            </div>
          )}

          {chat?.messages?.map((m) => (
            <div key={m.id} className={`message ${m.role}`}>
              <div className="message-meta">
                <span className="role">{m.role === "user" ? "You" : "Assistant"}</span>
                {m.role === "assistant" && m.total_tokens > 0 && (
                  <TokenBreakdown msg={m} />
                )}
              </div>
              <div className="bubble">
                {m.role === "assistant"
                  ? <MarkdownMessage content={m.content} />
                  : m.content}
              </div>
            </div>
          ))}
          {sending && (
            <div className="message assistant">
              <div className="message-meta"><span className="role">Assistant</span></div>
              <div className="bubble">
                <span className="typing-dots"><span /><span /><span /></span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="composer-wrap">
        <div className="composer">
          <textarea
            ref={textareaRef}
            rows={1}
            placeholder={isNew ? "Send a message to start a chat…" : "Send a follow-up message…"}
            value={draft}
            onChange={(e) => { setDraft(e.target.value); autoGrow(e.target); }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <div className="composer-row">
            <div className="composer-actions">
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf,.pdf"
                style={{ display: "none" }}
                onChange={handleFilePicked}
              />
              <button
                className="attach-btn"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading || attachedDocs.length >= MAX_ATTACHMENTS}
                title={attachedDocs.length >= MAX_ATTACHMENTS
                  ? `Maximum ${MAX_ATTACHMENTS} documents per chat`
                  : "Attach a PDF"}
              >
                {uploading ? "…" : "📎"}
              </button>
              <span className="composer-hint">
                {attachedDocs.length}/{MAX_ATTACHMENTS} attached · Enter to send · Shift+Enter newline
              </span>
            </div>
            <button
              className="send-btn"
              onClick={handleSend}
              disabled={sending || !draft.trim()}
              aria-label="Send"
            >
              ↑
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Per-message token breakdown shown in the message metadata row.
// input = prompt_tokens - system_tokens (rough but consistent with how
// prompt-service split them before the call).
function TokenBreakdown({ msg }) {
  const sys = msg.system_tokens || 0;
  const input = Math.max(0, (msg.prompt_tokens || 0) - sys);
  const output = msg.completion_tokens || 0;
  return (
    <span className="token-split">
      · sys {sys} · in {input} · out {output}
    </span>
  );
}

function MarkdownMessage({ content }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          const text = String(children).replace(/\n$/, "");
          if (inline) {
            return <code className="inline-code" {...props}>{children}</code>;
          }
          return <CodeBlock language={match?.[1]} text={text} />;
        },
        pre({ children }) { return <>{children}</>; },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

function CodeBlock({ language, text }) {
  const [copied, setCopied] = useState(false);
  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  }
  return (
    <div className="code-block">
      <div className="code-block-header">
        <span className="code-lang">{language || "code"}</span>
        <button className="code-copy" onClick={handleCopy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre><code>{text}</code></pre>
    </div>
  );
}

function computeTotals(chat) {
  if (!chat?.messages) return null;
  let system = 0, input = 0, output = 0;
  for (const m of chat.messages) {
    if (m.role !== "assistant") continue;
    const sys = m.system_tokens || 0;
    system += sys;
    input += Math.max(0, (m.prompt_tokens || 0) - sys);
    output += m.completion_tokens || 0;
  }
  return { system, input, output };
}

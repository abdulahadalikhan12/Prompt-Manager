import { useState, useEffect, useRef } from "react";
import { chatsApi, reviewsApi } from "./api";

// A full chat conversation view -- the "ChatGPT-type" piece. Takes a
// chatId (already created via Execute) and renders the message history,
// a follow-up input, a Summarize button, token totals, and a small
// review form for the whole conversation.
export default function ChatView({ chatId, onClose }) {
  const [chat, setChat] = useState(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [summarizing, setSummarizing] = useState(false);
  const [reviewerName, setReviewerName] = useState("");
  const [reviewScore, setReviewScore] = useState(5);
  const [reviewFeedback, setReviewFeedback] = useState("");
  const [reviewSummary, setReviewSummary] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    loadChat();
    loadReviewSummary();
  }, [chatId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat?.messages?.length]);

  async function loadChat() {
    try {
      const data = await chatsApi.get(chatId);
      setChat(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadReviewSummary() {
    try {
      const data = await reviewsApi.summaryForChat(chatId);
      setReviewSummary(data);
    } catch {
      // non-fatal -- review summary is supplementary, chat itself still works
    }
  }

  async function handleSend() {
    const content = draft.trim();
    if (!content || sending) return;
    setSending(true);
    setError(null);
    try {
      await chatsApi.followUp(chatId, content);
      setDraft("");
      await loadChat();
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  async function handleSummarize() {
    setSummarizing(true);
    setError(null);
    try {
      await chatsApi.summarize(chatId);
      await loadChat();
    } catch (err) {
      setError(err.message);
    } finally {
      setSummarizing(false);
    }
  }

  async function handleSubmitReview() {
    if (!reviewerName.trim() || !reviewFeedback.trim()) return;
    try {
      await reviewsApi.create({
        target_type: "chat",
        chat_id: chatId,
        reviewer_name: reviewerName,
        score: Number(reviewScore),
        feedback: reviewFeedback,
      });
      setReviewerName("");
      setReviewFeedback("");
      loadReviewSummary();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!chat) {
    return (
      <div className="chat-view">
        {error ? <div className="error-banner">{error}</div> : <p className="empty-state">Loading chat...</p>}
      </div>
    );
  }

  return (
    <div className="chat-view">
      <div className="chat-header">
        <div>
          <strong>{chat.title || "Chat"}</strong>
          <span className="token-badge">{chat.total_tokens} tokens total</span>
        </div>
        <div className="chat-header-actions">
          <button onClick={handleSummarize} disabled={summarizing}>
            {summarizing ? "Summarizing..." : "Summarize"}
          </button>
          <button onClick={onClose}>Close</button>
        </div>
      </div>

      {chat.summary && (
        <div className="summary-panel">
          <strong>Summary:</strong> {chat.summary}
        </div>
      )}

      {error && <div className="error-banner">{error}</div>}

      <div className="messages">
        {chat.messages.map((m) => (
          <div key={m.id} className={`message message-${m.role}`}>
            <div className="message-role">{m.role === "user" ? "You" : "Assistant"}</div>
            <div className="message-content">{m.content}</div>
            {m.role === "assistant" && m.total_tokens > 0 && (
              <div className="message-tokens">{m.total_tokens} tokens</div>
            )}
          </div>
        ))}
        {sending && (
          <div className="message message-assistant">
            <div className="message-role">Assistant</div>
            <div className="message-content loading-dots">Thinking...</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          rows={2}
          placeholder="Type a follow-up..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
        />
        <button className="primary" onClick={handleSend} disabled={sending}>
          Send
        </button>
      </div>

      <div className="review-block">
        <strong>Review this conversation</strong>
        {reviewSummary && reviewSummary.review_count > 0 && (
          <div className="summary-line">
            {reviewSummary.average_score.toFixed(1)} average ({reviewSummary.review_count} review{reviewSummary.review_count > 1 ? "s" : ""})
          </div>
        )}
        <div className="review-form-row">
          <input placeholder="Your name" value={reviewerName} onChange={(e) => setReviewerName(e.target.value)} />
          <select value={reviewScore} onChange={(e) => setReviewScore(e.target.value)}>
            {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
          <input placeholder="Feedback" value={reviewFeedback} onChange={(e) => setReviewFeedback(e.target.value)} />
          <button onClick={handleSubmitReview}>Submit Review</button>
        </div>
      </div>
    </div>
  );
}

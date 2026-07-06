import { useState, useEffect } from "react";
import { reviewsApi } from "./api";

// Generic review block. targetType drives which summary endpoint to
// hit and which id fields to include on submit:
//   "prompt"  -> targetId is the prompt id
//   "chat"    -> targetId is the chat id
//   "message" -> targetId is the message id; chatId is also required,
//                because review-service can only locate a message via
//                its parent chat (no GET /messages/{id} endpoint).
export default function ReviewBlock({ targetType, targetId, chatId, title, subtitle, dense }) {
  const [summary, setSummary] = useState(null);
  const [reviewerName, setReviewerName] = useState("");
  const [score, setScore] = useState(5);
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { loadSummary(); }, [targetId, targetType]);

  async function loadSummary() {
    try {
      let data;
      if (targetType === "chat") data = await reviewsApi.summaryForChat(targetId);
      else if (targetType === "message") data = await reviewsApi.summaryForMessage(targetId);
      else data = await reviewsApi.summaryForPrompt(targetId);
      setSummary(data);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSubmit() {
    if (!reviewerName.trim() || !feedback.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      let payload = {
        reviewer_name: reviewerName,
        score: Number(score),
        feedback,
        target_type: targetType,
      };
      if (targetType === "chat") payload.chat_id = targetId;
      else if (targetType === "message") {
        payload.chat_id = chatId;
        payload.message_id = targetId;
      } else payload.prompt_id = targetId;

      await reviewsApi.create(payload);
      setReviewerName("");
      setFeedback("");
      setScore(5);
      loadSummary();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={`review-row ${dense ? "dense" : ""}`}>
      <div className="review-row-head">
        <div>
          <h3>{title}</h3>
          {subtitle && <p className="desc">{subtitle}</p>}
        </div>
        {summary && summary.review_count > 0 && (
          <span className="stars">
            ★ {summary.average_score.toFixed(1)} · {summary.review_count} review{summary.review_count > 1 ? "s" : ""}
          </span>
        )}
      </div>

      {error && <div className="error-banner" style={{ margin: 0 }}>{error}</div>}

      {summary && summary.feedback && summary.feedback.length > 0 && (
        <div className="feedback-list">
          {summary.feedback.map((f, i) => (
            <div className="feedback-item" key={i}>{f}</div>
          ))}
        </div>
      )}

      <div className="review-form">
        <input
          placeholder="Your name"
          value={reviewerName}
          onChange={(e) => setReviewerName(e.target.value)}
        />
        <select value={score} onChange={(e) => setScore(e.target.value)}>
          {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n} ★</option>)}
        </select>
        <input
          placeholder="Feedback"
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
        />
        <button className="btn-primary" onClick={handleSubmit} disabled={submitting}>
          {submitting ? "…" : "Submit"}
        </button>
      </div>
    </div>
  );
}

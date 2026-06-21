import { useState, useEffect } from "react";
import { reviewsApi } from "./api";

// Handles everything review-related for ONE prompt: showing the score
// summary, listing feedback, and submitting a new review. Lives inside
// PromptCard but is its own component because it talks to a completely
// different backend service (review-service, not prompt-service) --
// keeping that boundary visible in the code structure too.
export default function ReviewBlock({ promptId }) {
  const [summary, setSummary] = useState(null);
  const [reviewerName, setReviewerName] = useState("");
  const [score, setScore] = useState(5);
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    loadSummary();
  }, [promptId]);

  async function loadSummary() {
    try {
      const data = await reviewsApi.summary(promptId);
      setSummary(data);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSubmitReview() {
    if (!reviewerName.trim() || !feedback.trim()) return;
    try {
      await reviewsApi.create({
        prompt_id: promptId,
        reviewer_name: reviewerName,
        score: Number(score),
        feedback,
      });
      setReviewerName("");
      setFeedback("");
      setError(null);
      loadSummary();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="review-block">
      {error && <div className="error-banner">{error}</div>}

      {summary && summary.review_count > 0 ? (
        <div className="summary-line">
          ⭐ {summary.average_score.toFixed(1)} average ({summary.review_count} review{summary.review_count > 1 ? "s" : ""})
          {summary.feedback.map((f, i) => (
            <div className="feedback-item" key={i}>{f}</div>
          ))}
        </div>
      ) : (
        <div className="summary-line empty-state">No reviews yet.</div>
      )}

      <div style={{ marginTop: 10, display: "flex", gap: 6, flexWrap: "wrap" }}>
        <input
          style={{ flex: "1 1 140px" }}
          placeholder="Your name"
          value={reviewerName}
          onChange={(e) => setReviewerName(e.target.value)}
        />
        <select value={score} onChange={(e) => setScore(e.target.value)} style={{ width: 70 }}>
          {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
        <input
          style={{ flex: "2 1 200px" }}
          placeholder="Feedback"
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
        />
        <button onClick={handleSubmitReview}>Submit Review</button>
      </div>
    </div>
  );
}

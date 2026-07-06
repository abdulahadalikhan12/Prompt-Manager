import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional


class ReviewStorage:
    """
    Stores each review as its OWN JSON file inside reviews/, named by
    the review's UUID. Deliberately different from prompt-service's
    Postgres table -- this contrast is the intentional teaching point
    from Week 1, still true in Week 2 even though reviews now also
    cover full chats.
    """

    def __init__(self, directory: str):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, review_id: str) -> Path:
        return self.dir / f"{review_id}.json"

    def save(self, review: dict) -> dict:
        path = self._path_for(review["id"])
        path.write_text(json.dumps(review, indent=2, default=str), encoding="utf-8")
        return review

    def get(self, review_id: str) -> Optional[dict]:
        path = self._path_for(review_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def get_all(self, prompt_id: Optional[str] = None, chat_id: Optional[str] = None,
                message_id: Optional[str] = None) -> List[dict]:
        reviews = []
        for file in self.dir.glob("*.json"):
            data = json.loads(file.read_text(encoding="utf-8"))
            if prompt_id is not None and data.get("prompt_id") != prompt_id:
                continue
            if chat_id is not None and data.get("chat_id") != chat_id:
                continue
            if message_id is not None and data.get("message_id") != message_id:
                continue
            reviews.append(data)
        return reviews

    def create(self, target_type: str, prompt_id: Optional[str], chat_id: Optional[str],
               message_id: Optional[str], snapshot: Any, reviewer_name: str, score: int,
               feedback: str) -> dict:
        """
        snapshot is Any rather than str -- a prompt or message review is
        plain text, a chat review is the full chat object (a dict with
        nested messages) copied verbatim from prompt-service. json.dumps
        handles either shape fine when writing to disk.
        """
        review = {
            "id": str(uuid.uuid4()),
            "target_type": target_type,
            "prompt_id": prompt_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "snapshot": snapshot,
            "reviewer_name": reviewer_name,
            "score": score,
            "feedback": feedback,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        return self.save(review)

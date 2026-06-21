import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


class ReviewStorage:
    """
    Stores each review as its OWN JSON file inside reviews/, named by
    the review's UUID -- e.g. reviews/7f96a48e-....json.

    This is deliberately different from prompt-service's single Postgres
    table. The spec wants the contrast: one service learns "everything
    in one relational table," the other learns "one file per record."
    Neither service imports or touches the other's storage at all --
    that boundary is what makes them genuinely independent services.
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

    def get_all(self, prompt_id: Optional[str] = None) -> List[dict]:
        reviews = []
        for file in self.dir.glob("*.json"):
            data = json.loads(file.read_text(encoding="utf-8"))
            if prompt_id is None or data["prompt_id"] == prompt_id:
                reviews.append(data)
        return reviews

    def create(self, prompt_id: str, prompt_snapshot: str, reviewer_name: str,
               score: int, feedback: str) -> dict:
        review = {
            "id": str(uuid.uuid4()),
            "prompt_id": prompt_id,
            "prompt_snapshot": prompt_snapshot,
            "reviewer_name": reviewer_name,
            "score": score,
            "feedback": feedback,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        return self.save(review)

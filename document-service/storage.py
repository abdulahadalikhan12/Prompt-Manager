"""
Per-document file storage -- mirrors review-service's "one JSON file per
record" pattern, but with a twist: we also keep the original uploaded
binary alongside its metadata, so the document can be re-downloaded
or re-extracted later if needed.

Layout under DATA_DIR:
    files/<uuid>.<ext>   -- the original PDF or DOCX, byte-for-byte
    meta/<uuid>.json     -- {id, filename, kind, size_bytes, text, uploaded_at}

The text body is stored on disk so subsequent /text reads don't have to
re-parse the PDF -- extraction happens exactly once, on upload.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


class DocumentStorage:
    def __init__(self, root_dir: str):
        self.root = Path(root_dir)
        self.files_dir = self.root / "files"
        self.meta_dir = self.root / "meta"
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def _meta_path(self, doc_id: str) -> Path:
        return self.meta_dir / f"{doc_id}.json"

    def _file_path(self, doc_id: str, kind: str) -> Path:
        return self.files_dir / f"{doc_id}.{kind}"

    def save(self, raw: bytes, filename: str, kind: str, text: str) -> dict:
        doc_id = str(uuid.uuid4())
        self._file_path(doc_id, kind).write_bytes(raw)

        meta = {
            "id": doc_id,
            "filename": filename,
            "kind": kind,
            "size_bytes": len(raw),
            "char_count": len(text),
            "text": text,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        self._meta_path(doc_id).write_text(
            json.dumps(meta, indent=2), encoding="utf-8",
        )
        return meta

    def get(self, doc_id: str) -> Optional[dict]:
        path = self._meta_path(doc_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_all(self) -> List[dict]:
        out = []
        for f in self.meta_dir.glob("*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            # Drop the heavy `text` field from list views -- callers fetch
            # it explicitly via GET /documents/{id}/text when they need it.
            data.pop("text", None)
            out.append(data)
        # Newest first, same convention as chats in prompt-service.
        out.sort(key=lambda d: d["uploaded_at"], reverse=True)
        return out

    def delete(self, doc_id: str) -> bool:
        meta = self.get(doc_id)
        if meta is None:
            return False
        self._meta_path(doc_id).unlink(missing_ok=True)
        self._file_path(doc_id, meta["kind"]).unlink(missing_ok=True)
        return True

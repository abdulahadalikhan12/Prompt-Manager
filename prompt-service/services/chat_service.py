import asyncio
from typing import Optional
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.config import settings
from models import Chat, Message, Prompt


class ChatService:
    """
    Owns chats and messages -- the Week 2 addition to prompt-service.
    prompt-service is the ORCHESTRATOR of execution: it is the only
    service that talks to llm-service directly (the frontend never
    calls llm-service itself), and it is the only writer to its own
    database, exactly as in Week 1.

    Every method that calls out to llm-service is async, because that
    network call can genuinely take many seconds -- a synchronous call
    here would freeze this entire service for every other concurrent
    request while waiting on one model response.
    """

    def __init__(self, db: Session, http_client: httpx.AsyncClient):
        self.db = db
        self.http_client = http_client

    def get_chat(self, chat_id: UUID) -> Optional[Chat]:
        return self.db.query(Chat).filter(Chat.id == chat_id).first()

    def list_chats(self, prompt_id: Optional[UUID] = None) -> list[Chat]:
        query = self.db.query(Chat)
        if prompt_id is not None:
            query = query.filter(Chat.prompt_id == prompt_id)
        return query.order_by(Chat.created_at.desc()).all()

    def delete_chat(self, chat_id: UUID) -> bool:
        chat = self.get_chat(chat_id)
        if chat is None:
            return False
        self.db.delete(chat)
        self.db.commit()
        return True

    async def execute_prompt(self, prompt_id: UUID, model: Optional[str] = None) -> Chat:
        prompt = self.db.query(Prompt).filter(Prompt.id == prompt_id).first()
        if prompt is None:
            raise HTTPException(status_code=404, detail="Prompt not found")

        # SQLAlchemy's Session is synchronous under the hood -- every
        # .commit() is a blocking call. Running it via asyncio.to_thread
        # hands that blocking work to a worker thread instead of running
        # it directly on the event loop, so other concurrent requests
        # aren't stalled while this write completes.
        chat = await asyncio.to_thread(self._create_chat_with_first_message, prompt)

        await self._run_turn(chat, model=model)
        return self.get_chat(chat.id)

    async def follow_up(self, chat_id: UUID, content: str, model: Optional[str] = None) -> Chat:
        chat = self.get_chat(chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")

        await asyncio.to_thread(self._append_message, chat, "user", content, 0, 0, 0)
        await self._run_turn(chat, model=model)
        return self.get_chat(chat.id)

    async def summarize_chat(self, chat_id: UUID) -> str:
        chat = self.get_chat(chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")

        messages = [{"role": m.role, "content": m.content} for m in chat.messages]

        summary = await self._call_llm_service(
            "/summarize", {"messages": messages}, response_key="summary",
        )

        await asyncio.to_thread(self._save_summary, chat, summary)
        return summary

    async def _run_turn(self, chat: Chat, model: Optional[str]) -> None:
        """Sends the full message history to llm-service, then stores
        the assistant's reply as a new message and updates the chat's
        running token total. Shared by both execute_prompt (first turn)
        and follow_up (every subsequent turn)."""
        messages = [{"role": m.role, "content": m.content} for m in chat.messages]

        result = await self._call_llm_service(
            "/generate", {"messages": messages, "model": model}, response_key=None,
        )

        await asyncio.to_thread(
            self._append_message,
            chat, "assistant", result["content"],
            result["usage"]["prompt_tokens"],
            result["usage"]["completion_tokens"],
            result["usage"]["total_tokens"],
        )

    async def _call_llm_service(self, path: str, body: dict, response_key: Optional[str]):
        """
        The actual cross-service call to llm-service. Mirrors the
        404-vs-503 distinction from review-service's Week 1 call to
        prompt-service, extended with a 504 for timeouts specifically.
        """
        try:
            response = await self.http_client.post(
                f"{settings.LLM_SERVICE_URL}{path}",
                json=body,
                timeout=httpx.Timeout(connect=5.0, read=65.0, write=10.0, pool=5.0),
            )
        except httpx.ReadTimeout:
            raise HTTPException(status_code=504, detail="llm-service timed out waiting for a model response.")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="llm-service is unavailable.")

        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"llm-service returned an error: {response.text}")

        data = response.json()
        return data[response_key] if response_key else data

    def _create_chat_with_first_message(self, prompt: Prompt) -> Chat:
        chat = Chat(prompt_id=prompt.id, title=prompt.name, total_tokens=0)
        self.db.add(chat)
        self.db.flush()  # assigns chat.id without a full commit, so the Message below can reference it

        first_message = Message(chat_id=chat.id, role="user", content=prompt.content,
                                 prompt_tokens=0, completion_tokens=0, total_tokens=0)
        self.db.add(first_message)
        self.db.commit()
        self.db.refresh(chat)
        return chat

    def _append_message(self, chat: Chat, role: str, content: str,
                         prompt_tokens: int, completion_tokens: int, total_tokens: int) -> None:
        message = Message(
            chat_id=chat.id, role=role, content=content,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=total_tokens,
        )
        self.db.add(message)

        chat.total_tokens = (chat.total_tokens or 0) + total_tokens
        self.db.add(chat)
        self.db.commit()

    def _save_summary(self, chat: Chat, summary: str) -> None:
        chat.summary = summary
        self.db.add(chat)
        self.db.commit()

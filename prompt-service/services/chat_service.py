import asyncio
from typing import Optional
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.config import settings
from models import Chat, ChatDocument, Message, Prompt
from schemas import DocumentAttachment


# Rough token estimator. Avoids adding tiktoken/another tokenizer to
# this service just to power a UI badge -- the 4-chars-per-token rule
# is accurate enough for English-language display (within ~10-20%).
# OpenRouter still returns the *real* prompt_tokens / completion_tokens
# from the model; this estimate only powers the split into system vs
# input tokens, which OpenRouter does not break out.
def estimate_tokens(text: str) -> int:
    return max(0, (len(text) + 3) // 4)


class ChatService:
    """
    Owns chats, messages, and chat-document attachments. prompt-service
    remains the orchestrator: it's the only service that talks to
    llm-service, and the only writer to its own database.

    Every method that makes a cross-service LLM call is async, because
    that network call can take many seconds and a synchronous call would
    freeze the whole service for every other concurrent request.
    """

    def __init__(self, db: Session, http_client: httpx.AsyncClient):
        self.db = db
        self.http_client = http_client

    # ---- queries ----

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

    # ---- chat lifecycle ----

    async def start_chat(
        self,
        content: str,
        model: Optional[str] = None,
        attachments: Optional[list[DocumentAttachment]] = None,
    ) -> Chat:
        if not content.strip():
            raise HTTPException(status_code=400, detail="Content is required.")

        prompt = await asyncio.to_thread(self._create_prompt_from_content, content)
        chat = await asyncio.to_thread(self._create_chat_with_first_message, prompt)

        if attachments:
            await asyncio.to_thread(self._attach_all, chat.id, attachments)
            self.db.refresh(chat)

        await self._run_turn(chat, model=model)
        return self.get_chat(chat.id)

    async def execute_prompt(self, prompt_id: UUID, model: Optional[str] = None) -> Chat:
        prompt = self.db.query(Prompt).filter(Prompt.id == prompt_id).first()
        if prompt is None:
            raise HTTPException(status_code=404, detail="Prompt not found")

        chat = await asyncio.to_thread(self._create_chat_with_first_message, prompt)
        await self._run_turn(chat, model=model)
        return self.get_chat(chat.id)

    async def follow_up(self, chat_id: UUID, content: str, model: Optional[str] = None) -> Chat:
        chat = self.get_chat(chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")

        await asyncio.to_thread(self._append_message, chat, "user", content, 0, 0, 0, 0)
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

    # ---- chat documents ----

    def list_documents(self, chat_id: UUID) -> list[ChatDocument]:
        chat = self.get_chat(chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat.documents

    def attach_document(self, chat_id: UUID, attachment: DocumentAttachment) -> ChatDocument:
        chat = self.get_chat(chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")

        if len(chat.documents) >= 3:
            raise HTTPException(
                status_code=409,
                detail="A chat can have at most 3 attached documents.",
            )
        if any(d.document_id == attachment.document_id for d in chat.documents):
            raise HTTPException(
                status_code=409,
                detail="This document is already attached to this chat.",
            )

        cd = ChatDocument(
            chat_id=chat_id,
            document_id=attachment.document_id,
            filename=attachment.filename,
            extracted_text=attachment.extracted_text,
        )
        self.db.add(cd)
        self.db.commit()
        self.db.refresh(cd)
        return cd

    def detach_document(self, chat_id: UUID, document_id: UUID) -> bool:
        row = (
            self.db.query(ChatDocument)
            .filter(ChatDocument.chat_id == chat_id, ChatDocument.document_id == document_id)
            .first()
        )
        if row is None:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    # ---- internals ----

    async def _run_turn(self, chat: Chat, model: Optional[str]) -> None:
        """Sends the system prompt + full message history to llm-service,
        stores the assistant reply with a System/Input/Output token split,
        and updates the running chat total. Shared by start_chat,
        execute_prompt (first turn) and follow_up (every later turn)."""
        system_prompt = self._build_system_prompt(chat)
        system_tokens = estimate_tokens(system_prompt) if system_prompt else 0

        outbound = []
        if system_prompt:
            outbound.append({"role": "system", "content": system_prompt})
        outbound.extend({"role": m.role, "content": m.content} for m in chat.messages)

        result = await self._call_llm_service(
            "/generate", {"messages": outbound, "model": model}, response_key=None,
        )

        await asyncio.to_thread(
            self._append_message,
            chat, "assistant", result["content"],
            system_tokens,
            result["usage"]["prompt_tokens"],
            result["usage"]["completion_tokens"],
            result["usage"]["total_tokens"],
        )

    def _build_system_prompt(self, chat: Chat) -> str:
        """Concise, since free OpenRouter models have tight context
        windows. Each attached doc is fenced with its filename so the
        model can refer to them by name when answering."""
        docs = chat.documents
        if not docs:
            return ""

        parts = ["The user attached the following document(s). Use them as context when answering."]
        for d in docs:
            parts.append(f"\n--- {d.filename} ---\n{d.extracted_text}")
        return "\n".join(parts)

    async def _call_llm_service(self, path: str, body: dict, response_key: Optional[str]):
        """The actual cross-service call to llm-service. Maps failures
        per the brief: timeout -> 504, unreachable -> 503, error -> 502."""
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

    def _create_prompt_from_content(self, content: str) -> Prompt:
        first_line = content.strip().splitlines()[0]
        name = first_line[:60] + ("…" if len(first_line) > 60 else "")
        prompt = Prompt(name=name, content=content)
        self.db.add(prompt)
        self.db.commit()
        self.db.refresh(prompt)
        return prompt

    def _create_chat_with_first_message(self, prompt: Prompt) -> Chat:
        chat = Chat(prompt_id=prompt.id, title=prompt.name, total_tokens=0)
        self.db.add(chat)
        self.db.flush()  # assigns chat.id without a full commit, so Message below can reference it

        first_message = Message(
            chat_id=chat.id, role="user", content=prompt.content,
            system_tokens=0, prompt_tokens=0, completion_tokens=0, total_tokens=0,
        )
        self.db.add(first_message)
        self.db.commit()
        self.db.refresh(chat)
        return chat

    def _attach_all(self, chat_id: UUID, attachments: list[DocumentAttachment]) -> None:
        # Sanity check: don't blow past the per-chat 3-doc cap even when
        # seeding a brand-new chat (frontend already enforces this, but
        # the backend is the source of truth).
        if len(attachments) > 3:
            raise HTTPException(
                status_code=409,
                detail="A chat can have at most 3 attached documents.",
            )
        for a in attachments:
            row = ChatDocument(
                chat_id=chat_id,
                document_id=a.document_id,
                filename=a.filename,
                extracted_text=a.extracted_text,
            )
            self.db.add(row)
        self.db.commit()

    def _append_message(
        self,
        chat: Chat,
        role: str,
        content: str,
        system_tokens: int,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
    ) -> None:
        message = Message(
            chat_id=chat.id, role=role, content=content,
            system_tokens=system_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
        self.db.add(message)

        chat.total_tokens = (chat.total_tokens or 0) + total_tokens
        self.db.add(chat)
        self.db.commit()

    def _save_summary(self, chat: Chat, summary: str) -> None:
        chat.summary = summary
        self.db.add(chat)
        self.db.commit()

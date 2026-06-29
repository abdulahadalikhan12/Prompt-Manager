from schemas import ChatMessage, SummarizeResponse
from services.openrouter_client import OpenRouterClient

SUMMARY_SYSTEM_PROMPT = (
    "You are a summarization assistant. Read the following conversation "
    "and produce a concise summary (2-4 sentences) capturing what was "
    "discussed and any conclusions reached. Do not add commentary about "
    "the summarization task itself -- just summarize the conversation."
)


async def summarize_chat(client: OpenRouterClient, messages: list[ChatMessage]) -> SummarizeResponse:
    """
    Builds a fresh message list with the summarization instruction as a
    system prompt, followed by the actual conversation, and calls the
    normal generate() path -- summarization is just generation with a
    specific system prompt, not a separate API mechanism.
    """
    summary_messages = [
        ChatMessage(role="system", content=SUMMARY_SYSTEM_PROMPT),
        *messages,
    ]
    result = await client.generate(messages=summary_messages, temperature=0.3)
    return SummarizeResponse(summary=result.content, model=result.model)

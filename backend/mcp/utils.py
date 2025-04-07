from typing import List, Dict, Any
from .context import Context, Message, MessageRole


def estimate_token_count(text: str) -> int:
    """Estimate token count in text (rough approximation)."""
    # A very rough estimation - about 4 chars per token on average
    return len(text) // 4


def truncate_context_if_needed(context: Context, max_tokens: int = 4000) -> Context:
    """Truncate context to fit within token limit."""
    # Make a copy of the context
    new_context = Context(
        system_prompt=context.system_prompt,
        temperature=context.temperature,
        max_tokens=context.max_tokens,
        metadata=context.metadata.copy()
    )
    
    # Start with system prompt tokens
    total_tokens = estimate_token_count(context.system_prompt or "")
    
    # Add messages from newest to oldest until we hit token limit
    for message in reversed(context.messages):
        msg_tokens = estimate_token_count(message.content)
        if total_tokens + msg_tokens <= max_tokens:
            new_context.messages.insert(0, message)
            total_tokens += msg_tokens
        else:
            # If we can't add more messages, break
            break
    
    return new_context
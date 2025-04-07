from typing import List, Dict, Any, Optional
import json
import logging
import traceback
from mcp.context import MessageRole, Message

logger = logging.getLogger(__name__)

class ConversationMemory:
    """Manages conversation history with short-term and long-term memory."""
    
    def __init__(self, max_short_term_messages: int = 10):
        """Initialize memory storage."""
        self.short_term_memory: List[Message] = []  # Recent messages
        self.long_term_memory: Dict[str, List[str]] = {}  # Important information by topic
        self.summaries: List[str] = []  # Periodic summaries of conversation
        self.max_short_term_messages = max_short_term_messages
    
    def add_message(self, message: Message) -> None:
        """Add a message to short-term memory."""
        self.short_term_memory.append(message)
        
        # Trim if exceeds max length
        if len(self.short_term_memory) > self.max_short_term_messages:
            self.short_term_memory.pop(0)
    
    def add_to_long_term(self, topic: str, information: str) -> None:
        """Add information to long-term memory under a specific topic."""
        if topic not in self.long_term_memory:
            self.long_term_memory[topic] = []
        self.long_term_memory[topic].append(information)
    
    def add_summary(self, summary: str) -> None:
        """Add a conversation summary to memory."""
        self.summaries.append(summary)
    
    def get_recent_messages(self, count: int = 5) -> List[Message]:
        """Get the most recent messages from short-term memory."""
        return self.short_term_memory[-count:] if self.short_term_memory else []
    
    def get_context_for_query(self, query: str) -> List[Message]:
        """Get relevant context for a query from both short and long-term memory."""
        # Always include recent messages
        context = self.get_recent_messages()
        
        # Include relevant information from long-term memory
        relevant_info = []
        for topic, info_list in self.long_term_memory.items():
            if topic.lower() in query.lower():
                for info in info_list:
                    relevant_info.append(
                        Message(
                            role=MessageRole.SYSTEM,
                            content=f"Related information about {topic}: {info}",
                            metadata={"source": "long_term_memory", "topic": topic}
                        )
                    )
        
        # Include most recent summary if available
        if self.summaries:
            context.append(
                Message(
                    role=MessageRole.SYSTEM,
                    content=f"Conversation summary: {self.summaries[-1]}",
                    metadata={"source": "summary"}
                )
            )
        
        return context + relevant_info
    
    def extract_key_information(self, message: Message) -> Dict[str, List[str]]:
        """
        Placeholder for extracting key information from a message.
        In a real implementation, this would use the LLM to identify important facts.
        """
        # Simple implementation that extracts potential topics
        extracted_info = {}
        content = message.content.lower()
        
        # Very basic extraction - in reality would use NLP or the LLM
        keywords = ["project", "deadline", "meeting", "contact", "email", "phone"]
        for keyword in keywords:
            if keyword in content:
                extracted_info[keyword] = [message.content]
        
        return extracted_info


async def generate_conversation_summary(provider, messages: List[Message]) -> str:
    """Generate a summary of the conversation."""
    from mcp.context import Context
    
    logger.info(f"Generating summary from {len(messages)} messages...")
    
    if not messages:
        logger.warning("No messages to summarize")
        return "No conversation to summarize yet."
    
    # Create a specialized system prompt for summarization
    summary_prompt = (
        "You are a conversation summarizer. Create a concise summary of the "
        "following conversation, focusing on key points, decisions, and important information. "
        "Highlight any facts or data that should be remembered for future reference. "
        "Keep your summary under 200 words."
    )
    
    # Format the conversation messages
    conversation_text = "\n".join([
        f"{msg.role.value}: {msg.content}" for msg in messages
    ])
    
    logger.info(f"Conversation text length: {len(conversation_text)} characters")
    
    # Create context with the specialized system prompt
    context = Context(system_prompt=summary_prompt)
    
    # Add the conversation text as a user message
    context.add_message(
        MessageRole.USER,
        f"Please summarize this conversation:\n\n{conversation_text}"
    )
    
    try:
        # Generate the summary
        summary = await provider.generate_response(context)
        logger.info(f"Generated summary: {summary[:100]}...")
        return summary
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        logger.error(traceback.format_exc())
        return "Error generating summary."


async def extract_key_facts(provider, message: Message) -> Dict[str, List[str]]:
    """
    Use the LLM to extract key facts from a message that should be stored in long-term memory.
    """
    from mcp.context import Context
    
    logger.info(f"Extracting facts from message: {message.content[:100]}...")
    
    # Create a specialized system prompt for fact extraction
    extraction_prompt = (
        "You are a fact extraction specialist. Your task is to identify important facts, "
        "data points, or information from the given message that should be remembered for "
        "future reference. Return your response in JSON format like this:\n"
        "{\n"
        "  \"topic1\": [\"fact1\", \"fact2\"],\n"
        "  \"topic2\": [\"fact3\"]\n"
        "}\n"
        "Only include truly important information. If no important facts are present, return an empty JSON object {}."
        "IMPORTANT: Return ONLY the raw JSON without any markdown formatting, code blocks, or explanations."
    )
    
    # Create context with the specialized system prompt
    context = Context(system_prompt=extraction_prompt)
    
    # Add the message content to extract facts from
    context.add_message(
        MessageRole.USER,
        f"Extract important facts from this message:\n\n{message.content}"
    )
    
    try:
        # Generate the extraction
        extraction_result = await provider.generate_response(context)
        logger.info(f"Raw extraction result length: {len(extraction_result)}")
        
        # Clean up the result
        cleaned_result = extraction_result.strip()
        
        # Handle <think> tags if present
        if "<think>" in cleaned_result and "</think>" in cleaned_result:
            think_end = cleaned_result.rfind("</think>")
            if think_end > 0:
                cleaned_result = cleaned_result[think_end + 8:].strip()
                logger.info(f"Removed <think> tags, remaining: {len(cleaned_result)} chars")
        
        # Handle markdown code blocks
        if "```" in cleaned_result:
            # Find the code block
            start_block = cleaned_result.find("```")
            end_block = cleaned_result.rfind("```")
            
            if start_block >= 0 and end_block > start_block:
                # Extract content between code blocks
                # Skip language specifier if present (```json)
                content_start = cleaned_result.find("\n", start_block) + 1
                if content_start > 0:
                    cleaned_result = cleaned_result[content_start:end_block].strip()
                    logger.info(f"Extracted from code block, content: {len(cleaned_result)} chars")
        
        logger.info(f"Cleaned extraction result: {cleaned_result[:100]}...")
        
        # Parse the JSON response
        try:
            facts = json.loads(cleaned_result)
            logger.info(f"Successfully parsed facts: {len(facts)} topics")
            return facts
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing fact extraction result: {e}")
            logger.error(f"Problem string: '{cleaned_result}'")
            
            # Try to fix common JSON issues
            try:
                # Try to find a valid JSON object in the string
                import re
                json_pattern = r'\{.*\}'
                match = re.search(json_pattern, cleaned_result, re.DOTALL)
                if match:
                    potential_json = match.group(0)
                    facts = json.loads(potential_json)
                    logger.info(f"Successfully extracted JSON using regex: {len(facts)} topics")
                    return facts
            except Exception as e:
                logger.error(f"Failed to extract JSON using regex: {e}")
            
            logger.error("Failed to fix JSON parsing issues")
            return {}
    except Exception as e:
        logger.error(f"Error in fact extraction: {e}")
        logger.error(traceback.format_exc())
        return {}
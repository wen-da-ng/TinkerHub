from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"


class Message(BaseModel):
    role: MessageRole
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Context(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    system_prompt: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_message(self, role: MessageRole, content: str, **metadata) -> None:
        """Add a message to the context."""
        self.messages.append(Message(role=role, content=content, metadata=metadata))
    
    def get_formatted_messages(self) -> List[Dict[str, Any]]:
        """Get messages formatted for LLM API consumption."""
        formatted = []
        
        if self.system_prompt:
            formatted.append({
                "role": MessageRole.SYSTEM.value,
                "content": self.system_prompt
            })
        
        for message in self.messages:
            formatted.append({
                "role": message.role.value,
                "content": message.content
            })
            
        return formatted
    
    def get_last_message(self) -> Optional[Message]:
        """Get the last message in the context."""
        if not self.messages:
            return None
        return self.messages[-1]
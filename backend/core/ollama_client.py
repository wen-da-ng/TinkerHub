# core/ollama_client.py

from typing import AsyncGenerator
import aiohttp
import time
import re
import logging
from datetime import datetime
import asyncio
import json

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.session = None
        self.last_request_time = 0
        self.min_delay = 1

    async def get_session(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def refine_search_query(self, question: str, history: str) -> str:
        try:
            current_time = time.time()
            if (delay := self.min_delay - (current_time - self.last_request_time)) > 0:
                await asyncio.sleep(delay)

            session = await self.get_session()
            prompt = f"""Current date: {datetime.now().strftime("%Y-%m-%d")}

Previous conversation:
{history}

Based on the conversation above, the user asked: "{question}"

Your task:
1. Identify if this is a follow-up question that references previous context
2. If it is a follow-up question, incorporate the relevant context into a search query
3. If it's a new question, use it as is
4. Output ONLY the search query between <search> tags

Examples:
- If first question was "What is the MH370 incident" and follow-up is "When did it happen", 
output: <search>When did Malaysia Airlines Flight MH370 disappear</search>
- If it's a new question like "What is quantum computing",
output: <search>What is quantum computing</search>

Generate the search query:"""
                
            async with session.post(
                f"{self.base_url}/api/generate",
                json={"model": "deepseek-r1:14b", "prompt": prompt, "stream": False}
            ) as response:
                data = await response.json()
                self.last_request_time = time.time()
                if match := re.search(r'<search>(.*?)</search>', data['response'], re.DOTALL):
                    return match.group(1).strip()
                return question
        except Exception as e:
            logger.error(f"Query refinement error: {e}")
            return question

    async def generate_response(self, model: str, prompt: str, context: str = "", history: str = "", system_prompt: str = "") -> AsyncGenerator[str, None]:
        try:
            current_time = time.time()
            if (delay := self.min_delay - (current_time - self.last_request_time)) > 0:
                await asyncio.sleep(delay)

            session = await self.get_session()
            
            full_prompt = f"""Current date: {datetime.now().strftime("%Y-%m-%d")}

{system_prompt}

=== CONTEXT ===
{context}

=== CONVERSATION HISTORY ===
{history}

=== USER REQUEST ===
{prompt}

Please provide a thorough response that demonstrates you've read and understood all provided content. Start your response with a <think> tag to show your analysis process:"""
            
            async with session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": True,
                    "temperature": 0.7,
                    "context_window": 32768,
                    "num_predict": 4096
                }
            ) as response:
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line)
                            yield data.get('response', '')
                        except json.JSONDecodeError:
                            continue
            self.last_request_time = time.time()
        except Exception as e:
            logger.error(f"Generation error: {e}")
            yield f"Error: {str(e)}"

ollama_client = OllamaClient()
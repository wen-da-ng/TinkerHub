from typing import AsyncGenerator, List, Dict
import aiohttp
import time
import re
import logging
from datetime import datetime
import asyncio
import json
import os
from pathlib import Path

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

    async def get_model_details(self) -> List[Dict]:
        try:
            session = await self.get_session()
            async with session.get(f"{self.base_url}/api/tags") as response:
                if not response.ok:
                    logger.error(f"Failed to fetch models: {response.status}")
                    return []
                    
                data = await response.json()
                models_info = []
                
                # Base directory for model manifests
                base_dir = os.path.expandvars(r'%USERPROFILE%\.ollama\models\manifests\registry.ollama.ai\library')
                
                for model in data.get('models', []):
                    try:
                        name = str(model.get('name', ''))
                        if not name:
                            continue
                        
                        size_gb = 0
                        parameter_size = ''
                        
                        # Parse model name and tag
                        if ':' in name:
                            model_name, tag = name.split(':')
                        else:
                            model_name = name
                            tag = 'latest'
                        
                        # Construct path to manifest file
                        manifest_path = os.path.join(base_dir, model_name, tag)
                        
                        if os.path.exists(manifest_path):
                            try:
                                with open(manifest_path, 'r') as f:
                                    manifest = json.load(f)
                                    # Find the model layer and get its size
                                    for layer in manifest.get('layers', []):
                                        if layer.get('mediaType') == 'application/vnd.ollama.image.model':
                                            size_bytes = layer.get('size', 0)
                                            size_gb = round(size_bytes / (1024 * 1024 * 1024), 1)
                                            break
                            except Exception as e:
                                logger.error(f"Error reading manifest for {name}: {e}")
                                logger.error(f"Manifest path: {manifest_path}")
                        
                        # Extract parameter size from tag if available
                        if 'b' in tag.lower():
                            param_size = tag.lower().replace('b', '').strip()
                            if param_size.isdigit() or (param_size.replace('.', '').isdigit() and param_size.count('.') == 1):
                                parameter_size = f"{param_size}B"
                        
                        # Calculate RAM requirement (2x model size or minimum 8GB)
                        ram_requirement = max(size_gb * 2, 8)
                        
                        models_info.append({
                            'name': name,
                            'size_gb': size_gb,
                            'ram_requirement': round(ram_requirement, 1),
                            'parameter_size': parameter_size
                        })
                        
                    except Exception as e:
                        logger.error(f"Error processing model {name}: {e}")
                        continue
                
                return sorted(models_info, key=lambda x: x['size_gb'])
                
        except Exception as e:
            logger.error(f"Error fetching model details: {e}")
            return []

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

    async def generate_response(
        self,
        model: str,
        prompt: str,
        context: str = "",
        history: str = "",
        system_prompt: str = "Strictly always refer to the user as 'sir' instead of 'user'."
    ) -> AsyncGenerator[str, None]:
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
                    "options": {
                        "temperature": 0.7,
                        "num_ctx": 4096,
                        "num_predict": 131072
                    }
                }
            ) as response:
                if not response.ok:
                    error_text = await response.text()
                    logger.error(f"Generation failed: {error_text}")
                    yield f"Error: Failed to generate response with model {model}. Please try again or select a different model."
                    return
                    
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line)
                            if error := data.get('error'):
                                logger.error(f"Generation error: {error}")
                                yield f"Error: {error}"
                                return
                            yield data.get('response', '')
                        except json.JSONDecodeError:
                            continue
                            
            self.last_request_time = time.time()
            
        except Exception as e:
            logger.error(f"Generation error: {e}")
            yield f"Error: {str(e)}"

ollama_client = OllamaClient()
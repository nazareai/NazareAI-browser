from typing import Dict, Any, List, Optional, Union
import os
from openai import AsyncOpenAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, ValidationError
import json
import logging
import asyncio
from functools import wraps
from datetime import datetime, timedelta
import hashlib
import aiofiles
import aiofiles.os
from pathlib import Path
import tenacity
from ..exceptions import LLMError, LLMResponseError, LLMAPIError
from ..dom.manager import DOMManager
from ..core.page import Page

logger = logging.getLogger(__name__)

class ResponseCache:
    def __init__(self, cache_dir: str = ".cache/llm", ttl_minutes: int = 60):
        self.cache_dir = Path(cache_dir)
        self.ttl = timedelta(minutes=ttl_minutes)
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, prompt: str) -> str:
        """Generate a cache key from the prompt."""
        return hashlib.sha256(prompt.encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get the cache file path for a key."""
        return self.cache_dir / f"{key}.json"
    
    async def get(self, prompt: str) -> Optional[str]:
        """Get cached response if it exists and is not expired."""
        try:
            key = self._get_cache_key(prompt)
            cache_path = self._get_cache_path(key)
            
            if not cache_path.exists():
                return None
                
            async with aiofiles.open(cache_path, 'r') as f:
                data = json.loads(await f.read())
                
            cached_time = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - cached_time > self.ttl:
                await aiofiles.os.remove(cache_path)
                return None
                
            return data['response']
        except Exception as e:
            logger.warning(f"Cache read error: {str(e)}")
            return None
    
    async def set(self, prompt: str, response: str):
        """Cache a response."""
        try:
            key = self._get_cache_key(prompt)
            cache_path = self._get_cache_path(key)
            
            data = {
                'timestamp': datetime.now().isoformat(),
                'response': response
            }
            
            async with aiofiles.open(cache_path, 'w') as f:
                await f.write(json.dumps(data))
        except Exception as e:
            logger.warning(f"Cache write error: {str(e)}")

class BrowserAction(BaseModel):
    """Model for browser actions with enhanced validation."""
    type: str = Field(description="Type of action to perform (navigate, click, type, extract)")
    selector: str = Field(description="CSS selector or text description of the target element")
    value: str = Field(description="Value to use for the action (URL for navigate, text for type)")
    wait_for: str = Field(description="Element or condition to wait for after action", default="")
    press_enter: bool = Field(description="Whether to press Enter after typing (for type action)", default=False)
    
    @property
    def is_valid(self) -> bool:
        """Validate action based on type."""
        if self.type not in ["navigate", "click", "type", "extract"]:
            return False
        if self.type == "navigate" and not self.value.startswith(("http://", "https://")):
            return False
        if self.type in ["click", "type"] and not self.selector:
            return False
        return True

class ActionPlan(BaseModel):
    """Model for action plans with enhanced validation."""
    url: str = Field(description="Target URL for the action")
    actions: List[BrowserAction] = Field(description="List of actions to perform")
    extraction: Dict[str, Any] = Field(description="Data to extract after actions", default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        """Validate the entire action plan."""
        if not self.url.startswith(("http://", "https://")):
            return False
        return all(action.is_valid for action in self.actions)

def with_llm_error_handling(func):
    """Decorator to handle LLM-related errors."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValidationError as e:
            logger.error(f"LLM response validation error: {str(e)}")
            raise LLMResponseError(f"Invalid LLM response format: {str(e)}")
        except tenacity.RetryError as e:
            logger.error(f"LLM API retry error: {str(e)}")
            raise LLMAPIError("Failed to get valid response from LLM API after retries")
        except Exception as e:
            logger.error(f"Unexpected LLM error: {str(e)}")
            raise LLMError(f"Unexpected error in LLM operation: {str(e)}")
    return wrapper

class LLMController:
    def __init__(self, page: Page, dom_manager: DOMManager):
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/0xroyce/NazareAI-Browser-v2",
                "X-Title": "NazareAI Browser"
            }
        )
        self.model = "anthropic/claude-3-opus-20240229"
        self.action_parser = PydanticOutputParser(pydantic_object=ActionPlan)
        self.cache = ResponseCache()
        
        self.command_prompt = PromptTemplate(
            template="""You are an AI browser automation expert. Given the following command and page state,
            generate a structured plan of actions to accomplish the task.

            IMPORTANT: Return ONLY the JSON object, no additional text or explanation.

            For YouTube tasks, use these reliable selectors:
            - Search box: "input#search"
            - Search button: "button#search-icon-legacy"
            - Video links: "a#video-title-link"
            - Video player: "#movie_player video"
            - Play button: ".ytp-play-button"
            - Pause button: ".ytp-pause-button"
            - Volume button: ".ytp-mute-button"
            - Settings button: ".ytp-settings-button"
            - Full screen button: ".ytp-fullscreen-button"

            Command: {command}

            Current Page State:
            {page_state}

            Required JSON Structure:
            {format_instructions}

            JSON Response:""",
            input_variables=["command", "page_state"],
            partial_variables={"format_instructions": self.action_parser.get_format_instructions()}
        )

        self.page = page
        self.dom_manager = dom_manager
        self._setup_rate_limiter()

    def _setup_rate_limiter(self):
        """Setup rate limiting for API calls."""
        self.rate_limit = {
            'calls_per_minute': 50,
            'calls': [],
            'lock': asyncio.Lock()
        }

    async def _check_rate_limit(self):
        """Check and enforce rate limits."""
        async with self.rate_limit['lock']:
            now = datetime.now()
            minute_ago = now - timedelta(minutes=1)
            
            # Remove calls older than 1 minute
            self.rate_limit['calls'] = [
                t for t in self.rate_limit['calls']
                if t > minute_ago
            ]
            
            if len(self.rate_limit['calls']) >= self.rate_limit['calls_per_minute']:
                wait_time = (self.rate_limit['calls'][0] - minute_ago).total_seconds()
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    
            self.rate_limit['calls'].append(now)

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
        retry=tenacity.retry_if_exception_type(LLMAPIError)
    )
    async def _get_completion(self, prompt: str) -> str:
        """Get completion from OpenRouter API using OpenAI client with retries and caching."""
        # Check cache first
        cached_response = await self.cache.get(prompt)
        if cached_response:
            return cached_response
            
        # Check rate limit
        await self._check_rate_limit()
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.7,
                max_tokens=2000
            )
            
            if not response or not response.choices:
                raise LLMAPIError("Empty response from OpenRouter API")
                
            result = response.choices[0].message.content
            if not result:
                raise LLMAPIError("Empty content in OpenRouter API response")
            
            # Cache successful response
            await self.cache.set(prompt, result)
            
            return result
        except Exception as e:
            logger.error(f"LLM API error: {str(e)}")
            if "choices" in str(e):
                logger.error("Response structure: %s", str(response) if 'response' in locals() else "No response")
            raise LLMAPIError(f"Failed to get completion: {str(e)}")

    @with_llm_error_handling
    async def interpret_command(self, command: str, page_state: str = "") -> Dict[str, Any]:
        """Enhanced command interpretation with validation."""
        elements = await self.get_interactive_elements()
        
        # Generate the prompt with enhanced context
        prompt = f"""You are an AI browser automation expert. Generate a structured plan to accomplish the task.
        Return ONLY a valid JSON object with this exact structure:
        {{
            "url": "https://example.com",  // Target URL (must start with http:// or https://)
            "actions": [  // List of actions to perform
                {{
                    "type": "navigate",  // One of: navigate, click, type, extract
                    "value": "https://example.com",  // URL for navigate, text for type
                    "selector": "",  // CSS selector or element description
                    "wait_for": "",  // Optional: Element to wait for after action
                    "press_enter": false  // Optional: Whether to press Enter after typing
                }}
            ],
            "extraction": {{}}  // Optional: Data to extract after actions
        }}

        Command: {command}

        Current Page URL: {await self.page.url()}
        
        Available Interactive Elements:
        {self._format_elements(elements)}

        Current Page State:
        {page_state}

        For YouTube tasks, use these reliable selectors:
        - Search box: "input#search"
        - Search button: "button#search-icon-legacy"
        - Video links: "a#video-title-link"
        - Video player: "#movie_player video"
        - Play button: ".ytp-play-button"
        - Pause button: ".ytp-pause-button"
        - Volume button: ".ytp-mute-button"
        - Settings button: ".ytp-settings-button"
        - Full screen button: ".ytp-fullscreen-button"

        Return ONLY the JSON object, no additional text.
        
        JSON Response:"""
        
        response = await self._get_completion(prompt)
        
        # Extract and validate JSON from the response
        try:
            # Try to find JSON content between curly braces
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                try:
                    # Parse JSON first
                    action_plan = json.loads(json_str)
                    
                    # Basic validation
                    if not isinstance(action_plan, dict):
                        raise LLMResponseError("Response is not a dictionary")
                    
                    # Validate URL
                    if "url" not in action_plan or not isinstance(action_plan["url"], str):
                        raise LLMResponseError("Missing or invalid 'url' field")
                    if not action_plan["url"].startswith(("http://", "https://")):
                        action_plan["url"] = f"https://{action_plan['url']}"
                    
                    # Validate actions
                    if "actions" not in action_plan or not isinstance(action_plan["actions"], list):
                        raise LLMResponseError("Missing or invalid 'actions' field")
                    
                    # Validate each action
                    valid_types = {"navigate", "click", "type", "extract"}
                    for action in action_plan["actions"]:
                        if not isinstance(action, dict):
                            raise LLMResponseError("Invalid action format")
                        if "type" not in action or action["type"] not in valid_types:
                            raise LLMResponseError(f"Invalid action type: {action.get('type')}")
                        if "value" not in action:
                            action["value"] = ""
                        if "selector" not in action:
                            action["selector"] = ""
                        if "wait_for" not in action:
                            action["wait_for"] = ""
                        if "press_enter" not in action:
                            action["press_enter"] = False
                    
                    # Ensure extraction exists
                    if "extraction" not in action_plan:
                        action_plan["extraction"] = {}
                    
                    return action_plan
                    
                except json.JSONDecodeError as e:
                    raise LLMResponseError(f"Failed to parse JSON: {str(e)}")
                except Exception as e:
                    raise LLMResponseError(f"Failed to validate action plan: {str(e)}")
            raise LLMResponseError("No valid JSON found in response")
        except Exception as e:
            logger.error(f"Error processing LLM response: {str(e)}")
            logger.error(f"Raw response: {response}")
            raise LLMResponseError(f"Failed to process LLM response: {str(e)}")

    async def get_interactive_elements(self):
        """Get all pre-annotated interactive elements on the page with enhanced error handling."""
        try:
            return await self.page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('[data-nazare-interactive]');
                    return Array.from(elements).map(el => ({
                        id: el.id,
                        type: el.getAttribute('data-nazare-type'),
                        role: el.getAttribute('data-nazare-role'),
                        text: el.getAttribute('data-nazare-text'),
                        isVisible: el.getAttribute('data-nazare-visible') === 'true'
                    })).filter(el => el.isVisible);  // Only return visible elements
                }
            """)
        except Exception as e:
            logger.error(f"Failed to get interactive elements: {str(e)}")
            return []

    def _format_elements(self, elements: List[Dict[str, Any]]) -> str:
        """Format elements list for prompt context."""
        if not elements:
            return "No interactive elements found"
            
        formatted = []
        for el in elements:
            desc = f"- {el['type']} element"
            if el['id']:
                desc += f" (id: {el['id']})"
            if el['role']:
                desc += f" with role {el['role']}"
            if el['text']:
                desc += f": {el['text']}"
            formatted.append(desc)
            
        return "\n".join(formatted)

    async def summarize_content(self, content: str, max_length: int = 500) -> str:
        """
        Summarize extracted content using the LLM.
        
        Args:
            content: The content to summarize
            max_length: Maximum length of the summary in characters
            
        Returns:
            A concise summary of the content
        """
        prompt = f"""Summarize the following content in a clear and concise way.
        Keep the summary under {max_length} characters.
        
        Content:
        {content}
        
        Summary:"""
        
        return await self._get_completion(prompt)

    async def extract_information(self, content: str, extraction_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract specific information from content based on an extraction plan.
        
        Args:
            content: The content to extract information from
            extraction_plan: A dictionary specifying what information to extract
            
        Returns:
            A dictionary containing the extracted information
        """
        try:
            # If no extraction plan, return empty result
            if not extraction_plan:
                return {"result": "No extraction plan provided"}

            prompt = f"""Extract the following information from the content according to the plan.
            Return ONLY the JSON object, no additional text or explanation.
            
            Plan:
            {json.dumps(extraction_plan, indent=2)}
            
            Content:
            {content}
            
            JSON response:"""
            
            try:
                response = await self._get_completion(prompt)
                if not response:
                    return {"error": "No response from LLM"}
                
                # First try to parse the entire response as JSON
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    # If that fails, try to extract JSON between curly braces
                    start_idx = response.find('{')
                    end_idx = response.rfind('}') + 1
                    if start_idx >= 0 and end_idx > start_idx:
                        try:
                            json_str = response[start_idx:end_idx]
                            return json.loads(json_str)
                        except json.JSONDecodeError as e:
                            return {
                                "error": f"Invalid JSON in extracted content: {str(e)}",
                                "raw_response": response[:500]
                            }
                    
                    # If no JSON found, try to create a simple result
                    return {
                        "result": response.strip()[:1000]  # Return truncated response as plain text
                    }
                    
            except LLMAPIError as e:
                return {
                    "error": f"LLM API error: {str(e)}"
                }
            except Exception as e:
                return {
                    "error": f"Extraction error: {str(e)}",
                    "raw_response": response[:500] if 'response' in locals() else None
                }
                
        except Exception as e:
            logger.error(f"Error in extract_information: {str(e)}")
            return {
                "error": f"Fatal extraction error: {str(e)}"
            }

    async def analyze_page(self):
        """Get enhanced page analysis with annotated elements"""
        page_content = await self.dom_manager.get_page_content()
        
        # Include annotated elements in the context
        elements_context = await self.page.evaluate("""
            () => {
                const elements = document.querySelectorAll('.nazare-highlight');
                return Array.from(elements).map(el => ({
                    id: el.id,
                    type: el.getAttribute('data-nazare-type'),
                    text: el.getAttribute('data-nazare-text'),
                    isVisible: el.getBoundingClientRect().height > 0
                }));
            }
        """)
        
        context = {
            "page_content": page_content,
            "interactive_elements": elements_context,
            "current_url": await self.page.url()
        }
        
        return context

    async def suggest_action(self, task_description):
        """Suggest next action based on enhanced page analysis"""
        context = await self.analyze_page()
        
        prompt = f"""
        Task: {task_description}
        
        Current page URL: {context['current_url']}
        
        Available interactive elements:
        {self._format_elements(context['interactive_elements'])}
        
        What should be the next action? Consider:
        1. Which element to interact with
        2. What type of interaction (click, type, etc.)
        3. Any required input data
        """
        
        response = await self._get_completion(prompt)
        return self._parse_action(response)

    def _format_elements(self, elements: List[Dict[str, Any]]) -> str:
        """Format elements list for LLM consumption"""
        formatted = []
        for el in elements:
            desc = f"- {el['type']}"
            if el['role'] != el['type']:
                desc += f" (role: {el['role']})"
            if el['text']:
                desc += f": {el['text']}"
            formatted.append(desc)
        return "\n".join(formatted) 
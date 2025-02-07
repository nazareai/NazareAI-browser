from typing import Dict, Any, List
import os
from openai import AsyncOpenAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import json


class BrowserAction(BaseModel):
    type: str = Field(description="Type of action to perform (navigate, click, type, extract)")
    selector: str = Field(description="CSS selector or text description of the target element")
    value: str = Field(description="Value to use for the action (URL for navigate, text for type)")
    wait_for: str = Field(description="Element or condition to wait for after action", default="")
    press_enter: bool = Field(description="Whether to press Enter after typing (for type action)", default=False)


class ActionPlan(BaseModel):
    url: str = Field(description="Target URL for the action")
    actions: List[BrowserAction] = Field(description="List of actions to perform")
    extraction: Dict[str, Any] = Field(description="Data to extract after actions", default_factory=dict)


class LLMController:
    def __init__(self):
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
        
        self.command_prompt = PromptTemplate(
            template="""You are an AI browser automation expert. Given the following command and page state,
            generate a structured plan of actions to accomplish the task.

            IMPORTANT: Return ONLY the JSON object, no additional text or explanation.

            For YouTube tasks, use these reliable selectors:
            - Search box: "input[name='search_query']"
            - Search button: "button#search-icon-legacy"
            - Video links: "a#video-title"
            - Video player: "video.html5-main-video"

            Command: {command}

            Current Page State:
            {page_state}

            Required JSON Structure:
            {format_instructions}

            JSON Response:""",
            input_variables=["command", "page_state"],
            partial_variables={"format_instructions": self.action_parser.get_format_instructions()}
        )

    async def _get_completion(self, prompt: str) -> str:
        """Get completion from OpenRouter API using OpenAI client."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": prompt
            }],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content

    async def interpret_command(self, command: str, page_state: str = "") -> Dict[str, Any]:
        """
        Interpret a natural language command and convert it to structured browser actions.
        
        Args:
            command: The natural language command to interpret
            page_state: JSON string containing the current page state (optional)
            
        Returns:
            A dictionary containing the structured action plan
        """
        # Generate the prompt
        prompt = self.command_prompt.format(
            command=command,
            page_state=page_state
        )
        
        # Get LLM response
        response = await self._get_completion(prompt)
        
        # Extract JSON from the response
        try:
            # Try to find JSON content between curly braces
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                # Parse the JSON content
                try:
                    action_plan = self.action_parser.parse(json_str)
                    return action_plan.dict()
                except:
                    return json.loads(json_str)
            raise ValueError("No valid JSON found in response")
        except Exception as e:
            raise ValueError(f"Failed to parse LLM response: {str(e)}")

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
        prompt = f"""Extract the following information from the content according to the plan.
        Return ONLY the JSON object, no additional text or explanation.
        
        Plan:
        {json.dumps(extraction_plan, indent=2)}
        
        Content:
        {content}
        
        JSON response:"""
        
        response = await self._get_completion(prompt)
        
        # Extract JSON from the response
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                return json.loads(response[start_idx:end_idx])
            raise ValueError("No valid JSON found in response")
        except:
            return {"error": "Failed to parse extracted information"} 
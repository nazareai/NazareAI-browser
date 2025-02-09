from typing import Optional, Dict, Any, Union, List
from playwright.async_api import (
    Page as PlaywrightPage,
    ElementHandle,
    Response,
    BrowserContext,
    Route,
    ViewportSize
)
import logging
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)

class Page:
    """Wrapper around Playwright's Page class with enhanced functionality."""
    
    def __init__(self, playwright_page: PlaywrightPage):
        self._page = playwright_page
        
    @property
    def raw_page(self) -> PlaywrightPage:
        """Get the underlying Playwright page object."""
        return self._page
        
    @property
    def context(self) -> BrowserContext:
        """Get the browser context."""
        return self._page.context
        
    async def set_viewport_size(self, viewport: Dict[str, int]):
        """Set viewport size."""
        await self._page.set_viewport_size(viewport)
        
    async def get_viewport_size(self) -> ViewportSize:
        """Get current viewport size."""
        return self._page.viewport_size()
        
    async def goto(self, url: str, **kwargs) -> Optional[Response]:
        """Navigate to a URL."""
        return await self._page.goto(url, **kwargs)
        
    async def url(self) -> str:
        """Get current page URL."""
        return self._page.url
        
    async def content(self) -> str:
        """Get page content."""
        return await self._page.content()
        
    async def evaluate(self, expression: str, *args, **kwargs) -> Any:
        """Evaluate JavaScript code."""
        return await self._page.evaluate(expression, *args, **kwargs)
        
    async def evaluate_handle(self, expression: str, *args, **kwargs) -> ElementHandle:
        """Evaluate JavaScript code and return ElementHandle."""
        return await self._page.evaluate_handle(expression, *args, **kwargs)
        
    async def query_selector(self, selector: str) -> Optional[ElementHandle]:
        """Find element by selector."""
        return await self._page.query_selector(selector)
        
    async def query_selector_all(self, selector: str) -> List[ElementHandle]:
        """Find all elements matching selector."""
        return await self._page.query_selector_all(selector)
        
    async def wait_for_selector(self, selector: str, **kwargs) -> Optional[ElementHandle]:
        """Wait for element matching selector."""
        return await self._page.wait_for_selector(selector, **kwargs)
        
    async def wait_for_load_state(self, state: str = "load", **kwargs):
        """Wait for page load state."""
        return await self._page.wait_for_load_state(state, **kwargs)
        
    async def add_init_script(self, script: str):
        """Add initialization script."""
        return await self._page.add_init_script(script)
        
    async def route(self, url: str, handler: Callable[[Route], Awaitable[None]]):
        """Add route handler."""
        return await self._page.route(url, handler)
        
    def set_default_timeout(self, timeout: int):
        """Set default timeout."""
        self._page.set_default_timeout(timeout)
        
    def set_default_navigation_timeout(self, timeout: int):
        """Set default navigation timeout."""
        self._page.set_default_navigation_timeout(timeout)
        
    async def click(self, selector: str, **kwargs):
        """Click an element."""
        return await self._page.click(selector, **kwargs)
        
    async def type(self, selector: str, text: str, **kwargs):
        """Type text into an element."""
        return await self._page.type(selector, text, **kwargs)
        
    async def press(self, selector: str, key: str, **kwargs):
        """Press a key on an element."""
        return await self._page.press(selector, key, **kwargs)
        
    async def wait_for_navigation(self, **kwargs):
        """Wait for navigation to complete."""
        return await self._page.wait_for_navigation(**kwargs)
        
    async def close(self):
        """Close the page."""
        await self._page.close()
        
    async def screenshot(self, **kwargs) -> bytes:
        """Take a screenshot of the page."""
        return await self._page.screenshot(**kwargs)
        
    async def reload(self, **kwargs) -> Optional[Response]:
        """Reload the page."""
        return await self._page.reload(**kwargs)
        
    async def wait_for_function(self, expression: str, **kwargs):
        """Wait for function to be true."""
        return await self._page.wait_for_function(expression, **kwargs)
        
    async def title(self) -> str:
        """Get page title."""
        return await self._page.title()
        
    async def bring_to_front(self):
        """Bring page to front."""
        return await self._page.bring_to_front()
        
    async def set_extra_http_headers(self, headers: Dict[str, str]):
        """Set extra HTTP headers."""
        await self._page.set_extra_http_headers(headers)

    async def add_script_tag(self, **kwargs):
        """Add a script tag to the page."""
        return await self._page.add_script_tag(**kwargs)

    async def wait_for_timeout(self, timeout: int):
        """Wait for a specified time."""
        await self._page.wait_for_timeout(timeout)

    async def keyboard_press(self, key: str):
        """Press a keyboard key."""
        await self._page.keyboard.press(key)

    async def keyboard_type(self, text: str, delay: int = 50):
        """Type text with keyboard."""
        await self._page.keyboard.type(text, delay=delay)

    async def is_visible(self, selector: str) -> bool:
        """Check if element is visible."""
        try:
            element = await self.query_selector(selector)
            if not element:
                return False
            return await element.is_visible()
        except:
            return False
        
    async def add_style_tag(self, **kwargs):
        """Add a style tag to the page."""
        return await self._page.add_style_tag(**kwargs)
        
    # Add any additional methods needed for your specific use case 
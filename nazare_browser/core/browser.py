from typing import Optional, Dict, Any, Callable, TypeVar, ParamSpec, List, Union
from playwright.async_api import (
    async_playwright,
    Browser as PlaywrightBrowser,
    ElementHandle,
    BrowserContext,
    TimeoutError as PlaywrightTimeoutError,
    Error as PlaywrightError
)
import asyncio
from pathlib import Path
import yaml
import logging
from functools import wraps
import time
from tenacity import retry, stop_after_attempt, wait_exponential

from ..llm.controller import LLMController
from ..dom.manager import DOMManager
from ..plugins.manager import PluginManager
from ..config.settings import Settings, DomainSettings
from .cookie_manager import CookieManager
from .page import Page
from ..exceptions import BrowserError, NavigationError, ElementNotFoundError

logger = logging.getLogger(__name__)

T = TypeVar('T')
P = ParamSpec('P')

def with_error_handling(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to add error handling to browser methods."""
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout error in {func.__name__}: {str(e)}")
            raise NavigationError(f"Operation timed out: {str(e)}")
        except PlaywrightError as e:
            logger.error(f"Playwright error in {func.__name__}: {str(e)}")
            raise BrowserError(f"Browser operation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            raise BrowserError(f"Unexpected error: {str(e)}")
    return wrapper

class Browser:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.browser: Optional[PlaywrightBrowser] = None
        self.context = None
        self.page: Optional[Page] = None
        self.current_url: str = ""
        
        # Initialize managers
        self.dom_manager = None
        self.llm_controller = None
        self.plugin_manager = PluginManager()
        self.domain_settings = DomainSettings()
        self.cookie_manager = CookieManager()
        self._dom_managers = {}
        
        # Setup health monitoring
        self._last_health_check = time.time()
        self._health_check_interval = 60  # seconds
        self._is_healthy = True

    @with_error_handling
    async def start(self):
        """Initialize and start the browser with enhanced error handling and recovery."""
        try:
            playwright = await async_playwright().start()
            
            # Configure browser with performance optimizations
            self.browser = await playwright.chromium.launch(
                headless=self.settings.browser.headless,
                args=self._get_browser_args()
            )
            
            # Create context with optimized settings
            self.context = await self.browser.new_context(
                viewport=self.settings.browser.viewport,
                java_script_enabled=True,
                bypass_csp=True,
                ignore_https_errors=True,
                user_agent=self.settings.browser.user_agent or self._get_default_user_agent()
            )
            
            # Setup error handling for context
            self.context.set_default_timeout(self.settings.browser.default_timeout)
            await self._setup_context_handlers()
            
            # Create our Page wrapper around Playwright's page
            playwright_page = await self.context.new_page()
            self.page = Page(playwright_page)
            
            # Initialize managers that depend on page
            self.dom_manager = DOMManager(self.page)
            self.llm_controller = LLMController(self.page, self.dom_manager)
            
            # Set timeouts from config
            self.page.set_default_timeout(self.settings.browser.default_timeout)
            self.page.set_default_navigation_timeout(
                self.settings.browser.default_navigation_timeout
            )
            
            # Initialize components
            await self.plugin_manager.initialize(self.page)
            self.cookie_manager.clear_expired_cookies()
            
            # Initialize page with DOM utilities and annotations
            await self.dom_manager.setup_page()
            
            # Start health monitoring
            asyncio.create_task(self._monitor_health())
            
            logger.info("Browser started successfully!")
            
        except Exception as e:
            logger.error(f"Failed to start browser: {str(e)}")
            await self._cleanup()
            raise BrowserError(f"Browser startup failed: {str(e)}")

    def _get_browser_args(self) -> List[str]:
        """Get optimized browser launch arguments."""
        return [
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--disable-software-rasterizer',
            '--disable-extensions',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--js-flags=--expose-gc',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-background-networking',
            '--disable-breakpad',
            '--disable-component-extensions-with-background-pages',
            '--disable-ipc-flooding-protection',
            '--enable-features=NetworkService,NetworkServiceInProcess'
        ]

    def _get_default_user_agent(self) -> str:
        """Get the default user agent string."""
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )

    async def _setup_context_handlers(self):
        """Setup handlers for various browser context events."""
        self.context.on("page", self._handle_new_page)
        self.context.on("close", self._handle_context_close)
        
        # Setup request handling
        await self.context.route("**/*", self._handle_route)

    async def _monitor_health(self):
        """Monitor browser health and attempt recovery if needed."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._check_health()
            except Exception as e:
                logger.error(f"Health check failed: {str(e)}")
                self._is_healthy = False
                await self._attempt_recovery()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _check_health(self):
        """Check browser health by performing a simple operation."""
        if not self.page or not self.browser:
            self._is_healthy = False
            return
            
        try:
            # Try to evaluate a simple expression
            await self.page.evaluate("1 + 1")
            self._is_healthy = True
            self._last_health_check = time.time()
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            self._is_healthy = False
            raise

    async def _attempt_recovery(self):
        """Attempt to recover from unhealthy state."""
        logger.info("Attempting browser recovery...")
        try:
            await self._cleanup()
            await self.start()
            logger.info("Browser recovery successful!")
        except Exception as e:
            logger.error(f"Recovery failed: {str(e)}")
            raise BrowserError("Failed to recover browser state")

    async def _cleanup(self):
        """Clean up browser resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")

    async def _setup_performance_monitoring(self, page: Page):
        """Setup performance monitoring and page event handlers."""
        try:
            # Get the DOM manager for this page
            dom_manager = self._dom_managers.get(page)
            if not dom_manager:
                logger.error("No DOM manager found for page")
                return

            # Re-setup page annotations after navigation
            await page.playwright_page.on("load", lambda: dom_manager.annotate_page())
            
            # Handle consent dialogs and other common overlays
            await page.playwright_page.on("domcontentloaded", lambda: self._handle_common_overlays(page))
            
            logger.info("Performance monitoring setup complete")
        except Exception as e:
            logger.error(f"Failed to setup performance monitoring: {str(e)}")

    async def _handle_common_overlays(self, page: Page):
        """Handle common overlays like cookie consent dialogs."""
        try:
            # List of common consent button selectors
            consent_selectors = [
                'button[id*="consent"]',
                'button[class*="consent"]',
                'button[id*="cookie"]',
                'button[class*="cookie"]',
                '[aria-label*="consent"]',
                '[aria-label*="cookie"]'
            ]
            
            for selector in consent_selectors:
                try:
                    button = await page.playwright_page.wait_for_selector(selector, timeout=1000)
                    if button:
                        await button.click()
                        logger.info(f"Clicked consent button matching selector: {selector}")
                        break
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Error handling overlays: {str(e)}")
            # Don't raise the error as this is a non-critical operation

    async def _setup_dom_handling(self):
        """Setup DOM manipulation and monitoring."""
        if not self.page:
            return
            
        # Inject DOM utilities
        await self.page.add_init_script("""
            window.DOMUtils = {
                makeElementVisible: function(element) {
                    if (!element) return;
                    
                    // Make element and parents visible
                    let current = element;
                    while (current) {
                        const style = window.getComputedStyle(current);
                        if (style.display === 'none') {
                            current.style.setProperty('display', 'block', 'important');
                        }
                        if (style.visibility === 'hidden') {
                            current.style.setProperty('visibility', 'visible', 'important');
                        }
                        if (style.opacity === '0') {
                            current.style.setProperty('opacity', '1', 'important');
                        }
                        
                        // Ensure element is enabled and interactive
                        if (current.disabled) {
                            current.disabled = false;
                        }
                        if (current.hasAttribute('aria-hidden')) {
                            current.removeAttribute('aria-hidden');
                        }
                        if (current.hasAttribute('hidden')) {
                            current.removeAttribute('hidden');
                        }
                        
                        current = current.parentElement;
                    }
                    
                    // Ensure element is in viewport
                    element.scrollIntoView({
                        behavior: 'smooth',
                        block: 'center'
                    });
                },
                
                waitForElement: function(selector, timeout = 5000) {
                    return new Promise((resolve) => {
                        if (document.querySelector(selector)) {
                            resolve(document.querySelector(selector));
                            return;
                        }
                        
                        const observer = new MutationObserver((mutations, obs) => {
                            const element = document.querySelector(selector);
                            if (element) {
                                obs.disconnect();
                                resolve(element);
                            }
                        });
                        
                        observer.observe(document.body, {
                            childList: true,
                            subtree: true
                        });
                        
                        setTimeout(() => {
                            observer.disconnect();
                            resolve(null);
                        }, timeout);
                    });
                },
                
                getElementInfo: function(element) {
                    if (!element) return null;
                    
                    return {
                        tag: element.tagName.toLowerCase(),
                        id: element.id,
                        classes: Array.from(element.classList),
                        attributes: Object.fromEntries(
                            Array.from(element.attributes)
                                .map(attr => [attr.name, attr.value])
                        ),
                        text: element.textContent?.trim(),
                        isVisible: (
                            element.offsetWidth > 0 &&
                            element.offsetHeight > 0 &&
                            window.getComputedStyle(element).visibility !== 'hidden'
                        ),
                        rect: element.getBoundingClientRect().toJSON()
                    };
                }
            };
            
            // Expose utilities globally
            window.makeElementVisible = window.DOMUtils.makeElementVisible;
            window.waitForElement = window.DOMUtils.waitForElement;
            window.getElementInfo = window.DOMUtils.getElementInfo;
        """)
        
        # Setup mutation observer for DOM changes
        await self.page.evaluate("""
            window.domObserver = new MutationObserver((mutations) => {
                mutations.forEach(mutation => {
                    if (mutation.type === 'childList' || mutation.type === 'attributes') {
                        const element = mutation.target;
                        if (element.hasAttribute('data-ai-target')) {
                            window.DOMUtils.makeElementVisible(element);
                        }
                    }
                });
            });
            
            window.domObserver.observe(document.body, {
                childList: true,
                subtree: true,
                attributes: true
            });
        """)

    async def _handle_route(self, route):
        """Handle route requests with optimization."""
        request = route.request
        resource_type = request.resource_type
        
        # Only block resources if specified in config
        if self.settings.browser.block_resources:
            if resource_type in ['image', 'media', 'font']:
                if not self._is_critical_resource(request.url):
                    await route.abort()
                    return
        
        # Cache responses
        response = await route.fetch()
        if resource_type in ['script', 'stylesheet']:
            await route.fulfill(
                response=response,
                headers={
                    **response.headers,
                    'Cache-Control': 'public, max-age=31536000'
                }
            )
        else:
            await route.continue_()

    def _is_critical_resource(self, url: str) -> bool:
        """Determine if a resource is critical for functionality."""
        critical_patterns = [
            'youtube.com/s/player',
            'youtube.com/s/desktop',
            '/favicon.ico'
        ]
        return any(pattern in url for pattern in critical_patterns)

    async def _handle_navigation(self, url: str):
        """Handle navigation with optimized loading."""
        try:
            # Clear previous page state
            if self.current_url != url:
                self.dom_manager.clear_cache(self.current_url)
                self.current_url = url
            
            # Load cookies
            await self.cookie_manager.load_cookies(self.context, url)
            
            # Navigate with optimized settings
            response = await self.page.goto(
                url,
                timeout=60000,
                wait_until="domcontentloaded"
            )
            
            # Wait for critical content and setup page
            await self.dom_manager.wait_for_navigation(timeout=60000)
            await self.dom_manager.setup_page()
            
            # Handle consent dialogs
            await self.cookie_manager.handle_consent_dialogs(self.page, url)
            
            # Save cookies
            await self.cookie_manager.save_cookies(self.context, url)
            
            return response
            
        except Exception as e:
            logger.error(f"Navigation error for {url}: {str(e)}")
            raise

    async def _wait_for_element(self, selector: str, timeout: int = 10000) -> Optional[ElementHandle]:
        """Wait for element with DOM cache support."""
        try:
            # Check DOM cache first
            element = await self.dom_manager.find_element(self.page, selector)
            if element:
                return element
            
            # Fallback to direct selector
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if element and await element.is_visible():
                return element
            
            return None
            
        except Exception as e:
            logger.error(f"Error waiting for element {selector}: {str(e)}")
            return None

    async def execute_command(self, command: str) -> str:
        """Execute command with optimized DOM handling."""
        try:
            logger.info(f"Processing command: {command}")
            
            # Get current page state from cache
            logger.info("Capturing current page state...")
            page_state = await self.dom_manager.capture_dom_state()
            
            # Get action plan
            logger.info("Generating action plan from LLM...")
            action_plan = await self.llm_controller.interpret_command(command, page_state)
            
            # Log the action plan
            logger.info("Action plan generated:")
            if "url" in action_plan:
                logger.info(f"- Target URL: {action_plan['url']}")
            if "actions" in action_plan:
                for i, action in enumerate(action_plan["actions"], 1):
                    logger.info(f"- Action {i}: {action.get('type', 'unknown')} - {action.get('value', '')}")
            
            # Execute actions
            logger.info("Executing action plan...")
            result = await self._execute_action_plan(action_plan)
            
            logger.info("Command execution completed")
            return result
            
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            return f"Error executing command: {str(e)}"

    async def _execute_action_plan(self, action_plan: Dict[str, Any]) -> str:
        """Execute action plan with optimized element handling."""
        try:
            # Track if we've already navigated to avoid double loading
            initial_navigation_done = False
            
            if "url" in action_plan and not initial_navigation_done:
                url = action_plan["url"]
                if not url.startswith(("http://", "https://")):
                    url = f"https://{url}"
                logger.info(f"Applying domain settings for: {url}")
                await self.domain_settings.apply_settings(self.page, url)
                logger.info(f"Navigating to: {url}")
                await self._handle_navigation(url)
                initial_navigation_done = True
            
            if "actions" in action_plan:
                for i, action in enumerate(action_plan["actions"], 1):
                    action_type = action.get("type", "").lower()
                    value = action.get("value", "")
                    selector = action.get("selector", "")
                    
                    if action_type == "navigate" and not initial_navigation_done:
                        url = value
                        if not url.startswith(("http://", "https://")):
                            url = f"https://{url}"
                        logger.info(f"Action {i}: Navigating to {url}")
                        await self._handle_navigation(url)
                        initial_navigation_done = True
                    elif action_type == "navigate":
                        logger.info(f"Skipping redundant navigation to: {value}")
                        continue
                    
                    elif action_type == "click":
                        logger.info(f"Action {i}: Attempting to click element: {selector}")
                        element = await self.dom_manager.find_element(selector)
                        if element:
                            logger.info("Element found, performing click")
                            await element.click()
                            await asyncio.sleep(0.5)  # Short delay for stability
                            logger.info("Click performed successfully")
                        else:
                            logger.error(f"Could not find clickable element: {selector}")
                            return f"Could not find clickable element: {selector}"
                    
                    elif action_type == "type":
                        logger.info(f"Action {i}: Attempting to type '{value}' into element: {selector}")
                        element = await self.dom_manager.find_element(selector)
                        if element:
                            logger.info("Element found, typing text")
                            await element.type(value, delay=50)
                            if action.get("press_enter", False):
                                logger.info("Pressing Enter after typing")
                                await element.press("Enter")
                                await asyncio.sleep(0.5)
                            logger.info("Text input completed successfully")
                        else:
                            logger.error(f"Could not find input element: {selector}")
                            return f"Could not find input element: {selector}"
                    
                    elif action_type == "wait":
                        wait_for = action.get("wait_for", "")
                        if wait_for:
                            logger.info(f"Action {i}: Waiting for element: {wait_for}")
                            await self.dom_manager.find_element(wait_for)
                            logger.info("Wait completed")
                    
                    logger.info(f"Action {i} completed successfully")
            
            if "extraction" in action_plan:
                logger.info("Extracting information from page...")
                content = await self.page.content()
                result = await self.llm_controller.extract_information(content, action_plan["extraction"])
                logger.info("Information extraction completed")
                return result
            
            return "Command executed successfully"
            
        except Exception as e:
            logger.error(f"Error executing action plan: {str(e)}")
            return f"Error executing action plan: {str(e)}"

    async def _process_results(self, extraction_plan: Dict[str, Any]) -> str:
        """Process and extract results based on the extraction plan."""
        # Implement result extraction logic here
        pass

    async def close(self):
        """Close browser and cleanup resources."""
        if self.browser:
            await self.browser.close()
            self.dom_manager.clear_cache()

    async def new_page(self) -> Page:
        """Create a new page with all required setup."""
        try:
            # Create new page
            playwright_page = await self.context.new_page()
            page = Page(playwright_page)
            
            # Set viewport size
            await page.set_viewport_size({"width": 1280, "height": 720})
            
            # Initialize DOM manager
            dom_manager = DOMManager(page)
            await dom_manager.inject_dom_utilities()
            await dom_manager.setup_observers()
            
            # Store the DOM manager
            self._dom_managers[page] = dom_manager
            
            return page
        except Exception as e:
            logger.error(f"Failed to create new page: {str(e)}")
            raise 

    async def _handle_new_page(self, page):
        """Handle new page creation."""
        try:
            # Create our Page wrapper
            wrapped_page = Page(page)
            
            # Initialize DOM manager for the new page
            dom_manager = DOMManager(wrapped_page)
            await dom_manager.setup_page()
            
            # Store the DOM manager
            self._dom_managers[wrapped_page] = dom_manager
            
            logger.info("New page initialized successfully")
            
        except Exception as e:
            logger.error(f"Error handling new page: {str(e)}")
            raise BrowserError(f"Failed to handle new page: {str(e)}")

    async def _handle_context_close(self):
        """Handle browser context closure."""
        try:
            # Clean up DOM managers
            for page in list(self._dom_managers.keys()):
                self._dom_managers[page].clear_cache()
                del self._dom_managers[page]
            
            logger.info("Browser context closed successfully")
            
        except Exception as e:
            logger.error(f"Error handling context close: {str(e)}")
            raise BrowserError(f"Failed to handle context close: {str(e)}") 
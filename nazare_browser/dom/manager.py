from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import logging
from playwright.async_api import Page, ElementHandle
from bs4 import BeautifulSoup
from ..core.page import Page

logger = logging.getLogger(__name__)

class DOMManager:
    def __init__(self, page: Page):
        self.page = page
        self._element_cache = {}
        self._last_url = None
        self.dom_cache: Dict[str, Any] = {}
        self.element_cache: Dict[str, Dict[str, Any]] = {}
        self.last_interaction_map: Dict[str, str] = {}
        self.highlight_style = """
            /* Reset any site-specific styles that might interfere */
            .nazare-enabled [data-nazare-interactive] {
                all: initial !important;
                position: relative !important;
                cursor: pointer !important;
                display: inline-block !important;
            }
            
            /* Highlight styles */
            .nazare-enabled [data-nazare-interactive]::after {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                outline: 2px solid rgba(0, 123, 255, 0.5);
                outline-offset: 2px;
                pointer-events: none;
                z-index: 999999;
                opacity: 0;
                transition: opacity 0.2s;
            }
            
            .nazare-enabled [data-nazare-interactive]:hover::after {
                opacity: 1;
            }
            
            /* Type indicators */
            .nazare-enabled [data-nazare-type]::before {
                content: attr(data-nazare-type);
                position: absolute;
                top: -20px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 10px;
                opacity: 0;
                pointer-events: none;
                z-index: 1000000;
                transition: opacity 0.2s;
            }
            
            .nazare-enabled [data-nazare-interactive]:hover::before {
                opacity: 1;
            }
        """
        
    async def inject_styles(self):
        """Inject the highlight styles into the page"""
        try:
            # Add style tag directly
            await self.page.add_style_tag(content=self.highlight_style)
            
            # Add nazare-enabled class to body
            await self.page.evaluate("""
                document.body.classList.add('nazare-enabled');
            """)
            
            logger.info("Styles injected successfully")
            
        except Exception as e:
            logger.error(f"Error injecting styles: {str(e)}")
            raise

    async def setup_page(self):
        """Initialize page with DOM utilities."""
        try:
            # Wait for page to be ready
            await self.page.wait_for_load_state("domcontentloaded")
            
            # Load DOM utilities script
            script_path = Path(__file__).parent.parent / "static" / "dom-utils.js"
            with open(script_path) as f:
                dom_utils_script = f.read()
            
            # Add script tag directly
            await self.page.add_script_tag(content=dom_utils_script)
            
            # Wait for utilities to be available
            await self.page.wait_for_function('!!window.NazareDOM', timeout=5000)
            
            # Initialize annotations
            await self.page.evaluate('window.NazareDOM.init()')
            
            logger.info("Page setup completed successfully")
            
        except Exception as e:
            logger.error(f"Error setting up page: {str(e)}")
            raise

    async def inject_dom_utilities(self):
        """Inject enhanced DOM utilities."""
        await self.page.evaluate("""() => {
            if (window.DOMUtils) return;
            
            window.DOMUtils = {
                getElementContext(element) {
                    if (!element || element.nodeType !== Node.ELEMENT_NODE) return null;
                    
                    // Get computed role and type
                    const role = this.computeAriaRole(element);
                    const type = this.determineSemanticType(element);
                    
                    // Get text content with enhanced extraction
                    const text = this.extractElementText(element);
                    
                    // Check visibility with improved detection
                    const isVisible = this.isElementVisible(element);
                    
                    return { role, type, text, isVisible };
                },
                
                computeAriaRole(element) {
                    const explicitRole = element.getAttribute('role');
                    if (explicitRole) return explicitRole;
                    
                    const tag = element.tagName.toLowerCase();
                    const type = element.getAttribute('type');
                    
                    // Compute implicit role based on element characteristics
                    if (tag === 'button' || type === 'button') return 'button';
                    if (tag === 'a' && element.hasAttribute('href')) return 'link';
                    if (tag === 'input') {
                        if (type === 'text' || type === 'search') return 'textbox';
                        if (type === 'checkbox') return 'checkbox';
                        if (type === 'radio') return 'radio';
                        return type || 'textbox';
                    }
                    if (tag === 'select') return 'combobox';
                    if (tag === 'textarea') return 'textbox';
                    if (tag.match(/^h[1-6]$/)) return 'heading';
                    
                    return 'generic';
                },
                
                determineSemanticType(element) {
                    const tag = element.tagName.toLowerCase();
                    const role = element.getAttribute('role');
                    const type = element.getAttribute('type');
                    
                    // Enhanced type detection for YouTube
                    if (element.id === 'search') return 'searchbox';
                    if (element.id === 'search-icon-legacy') return 'button';
                    if (element.id === 'video-title-link') return 'link';
                    if (element.classList.contains('ytp-play-button')) return 'button';
                    if (element.classList.contains('ytp-settings-button')) return 'button';
                    
                    // General semantic types
                    if (tag === 'button' || role === 'button') return 'button';
                    if (tag === 'a' || role === 'link') return 'link';
                    if (tag === 'input') {
                        if (type === 'text') return 'textbox';
                        if (type === 'search') return 'searchbox';
                        if (type === 'checkbox') return 'checkbox';
                        if (type === 'radio') return 'radio';
                        return type;
                    }
                    if (tag === 'select') return 'dropdown';
                    if (role === 'navigation') return 'navigation';
                    if (role === 'main') return 'main-content';
                    if (role === 'complementary') return 'sidebar';
                    if (tag.match(/^h[1-6]$/)) return 'heading';
                    
                    return 'generic';
                },
                
                extractElementText(element) {
                    // Try aria-label first
                    let text = element.getAttribute('aria-label');
                    if (text) return text;
                    
                    // Then try placeholder
                    text = element.getAttribute('placeholder');
                    if (text) return text;
                    
                    // Then try value for inputs
                    if (element.tagName.toLowerCase() === 'input') {
                        text = element.value;
                        if (text) return text;
                    }
                    
                    // Finally try text content
                    text = element.textContent;
                    if (text) return text.trim();
                    
                    return '';
                },
                
                isElementVisible(element) {
                    if (!element) return false;
                    
                    const style = window.getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    
                    return !!(
                        rect.width && 
                        rect.height && 
                        style.visibility !== 'hidden' && 
                        style.display !== 'none' &&
                        style.opacity !== '0' &&
                        !element.hasAttribute('hidden') &&
                        !element.hasAttribute('aria-hidden')
                    );
                },
                
                preAnnotateElement(element) {
                    if (!element || element.nodeType !== Node.ELEMENT_NODE) return;
                    
                    const context = this.getElementContext(element);
                    if (!context) return;
                    
                    // Generate a unique ID if needed
                    if (!element.id) {
                        element.id = `nazare-${Math.random().toString(36).substr(2, 9)}`;
                    }
                    
                    // Add data attributes
                    element.setAttribute('data-nazare-role', context.role);
                    element.setAttribute('data-nazare-type', context.type);
                    if (context.text) {
                        element.setAttribute('data-nazare-text', context.text);
                    }
                    element.setAttribute('data-nazare-visible', context.isVisible.toString());
                    
                    // Mark interactive elements
                    if (['button', 'link', 'textbox', 'searchbox', 'checkbox', 'radio', 'dropdown'].includes(context.type)) {
                        element.setAttribute('data-nazare-interactive', 'true');
                    }
                    
                    // Store element context
                    window.nazareElements = window.nazareElements || {};
                    window.nazareElements[element.id] = context;
                },
                
                findElement(selector) {
                    // Try exact match first
                    let element = document.querySelector(selector);
                    if (element) return element;
                    
                    // Try data attributes with exact match
                    element = document.querySelector(`[data-nazare-text="${selector}"]`);
                    if (element) return element;
                    
                    // Try semantic search with partial match
                    const elements = document.querySelectorAll('[data-nazare-interactive]');
                    for (const el of elements) {
                        const text = el.getAttribute('data-nazare-text');
                        if (text && text.toLowerCase().includes(selector.toLowerCase())) {
                            return el;
                        }
                    }
                    
                    // Try role-based search
                    const role = selector.toLowerCase();
                    element = document.querySelector(`[data-nazare-role="${role}"]`);
                    if (element) return element;
                    
                    return null;
                }
            };
            
            // Expose utilities globally
            window.preAnnotateElement = window.DOMUtils.preAnnotateElement.bind(window.DOMUtils);
            window.findElement = window.DOMUtils.findElement.bind(window.DOMUtils);
        }""")

    async def pre_annotate_page(self):
        """Pre-annotate all elements on the page."""
        return await self.page.evaluate("""() => {
            if (!window.DOMUtils) {
                console.error('DOMUtils not initialized');
                return {};
            }
            
            try {
                // First annotate the body
                window.DOMUtils.preAnnotateElement(document.body);
                
                // Then annotate all elements
                document.querySelectorAll('*').forEach(el => {
                    try {
                        window.DOMUtils.preAnnotateElement(el);
                    } catch (e) {
                        console.error('Error pre-annotating element:', e);
                    }
                });
                
                return window.nazareElements || {};
            } catch (e) {
                console.error('Error in pre_annotate_page:', e);
                return {};
            }
        }""")

    async def setup_observers(self):
        """Setup mutation observers for dynamic content."""
        await self.page.evaluate("""() => {
            if (!window.DOMUtils) {
                console.error('DOMUtils not initialized');
                return;
            }
            
            // Create observer for dynamic content
            window.domObserver = new MutationObserver((mutations) => {
                mutations.forEach(mutation => {
                    if (mutation.type === 'childList') {
                        mutation.addedNodes.forEach(node => {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                try {
                                    window.DOMUtils.preAnnotateElement(node);
                                    // Also pre-annotate all children
                                    node.querySelectorAll('*').forEach(el => {
                                        try {
                                            window.DOMUtils.preAnnotateElement(el);
                                        } catch (e) {
                                            console.error('Error pre-annotating child element:', e);
                                        }
                                    });
                                } catch (e) {
                                    console.error('Error pre-annotating element:', e);
                                }
                            }
                        });
                    }
                });
            });

            // Start observing with configuration for better performance
            window.domObserver.observe(document.body, {
                childList: true,
                subtree: true,
                attributes: false  // We don't need to watch attributes
            });
        }""")

    async def find_element(self, selector: str, timeout: int = 10000) -> Optional[ElementHandle]:
        """Find an element using enhanced element finding."""
        try:
            # First try using NazareDOM's findElement
            found_element = await self.page.evaluate(f"""
                () => {{
                    const el = window.NazareDOM.findElement("{selector}");
                    if (el) {{
                        el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        return el.id;
                    }}
                    return null;
                }}
            """)
            
            if found_element:
                return await self.page.query_selector(f"#{found_element}")
            
            # Fallback to direct selector
            return await self.page.wait_for_selector(selector, timeout=timeout)
            
        except Exception as e:
            logger.error(f"Error finding element: {str(e)}")
            return None

    async def _is_element_visible(self, element: ElementHandle) -> bool:
        """Check if element is visible."""
        try:
            return await element.evaluate("element => window.NazareDOM.checkVisibility(element)")
        except:
            return False

    async def capture_dom_state(self) -> str:
        """Capture current DOM state for LLM context."""
        try:
            # Get current URL
            current_url = await self.page.url()
            
            # Get interactive elements
            elements = await self.get_interactive_elements()
            
            # Format state for LLM
            state = f"Current URL: {current_url}\n\n"
            
            if elements:
                state += "Interactive Elements:\n"
                for el in elements:
                    if el['isVisible']:
                        state += f"- {el['type'].upper()}: {el['text']} (role: {el['role']})\n"
            else:
                state += "No interactive elements found on the page.\n"
            
            return state
            
        except Exception as e:
            logger.error(f"Error capturing DOM state: {str(e)}")
            return "Error: Could not capture DOM state"

    def _build_element_cache(self, node: Dict[str, Any], url: str, path: str = ""):
        """Build a cache of elements for quick access."""
        if not isinstance(node, dict):
            return
            
        # Create unique key for element
        key = f"{path}/{node['tag']}"
        if node.get('id'):
            key += f"#{node['id']}"
        if node.get('classes'):
            key += f".{'.'.join(node['classes'])}"
            
        # Cache element data
        self.element_cache[url] = self.element_cache.get(url, {})
        self.element_cache[url][key] = {
            'tag': node['tag'],
            'attributes': node.get('attributes', {}),
            'text': node.get('text', ''),
            'isVisible': node.get('isVisible', False),
            'rect': node.get('rect', {}),
            'path': path
        }
        
        # Process children
        for i, child in enumerate(node.get('children', [])):
            child_path = f"{path}/{i}" if path else str(i)
            self._build_element_cache(child, url, child_path)

    def clear_cache(self, url: Optional[str] = None):
        """Clear element cache for a specific URL or all URLs."""
        if url:
            self._element_cache.pop(url, None)
        else:
            self._element_cache.clear()

    async def highlight_element(self, element_handle: ElementHandle, highlight_type: str = 'default'):
        """
        Highlight an element with enhanced visual feedback
        highlight_type can be: 'default', 'active', 'error'
        """
        if not element_handle:
            return
            
        await self.page.evaluate("""(element, type) => {
            // Remove existing highlights
            document.querySelectorAll('.nazare-highlight').forEach(el => {
                el.classList.remove('nazare-highlight', 'nazare-highlight-active', 'nazare-highlight-error');
            });
            
            // Add new highlight
            element.classList.add('nazare-highlight');
            if (type === 'active') {
                element.classList.add('nazare-highlight-active');
            } else if (type === 'error') {
                element.classList.add('nazare-highlight-error');
            }
            
            // Scroll element into view if needed
            const rect = element.getBoundingClientRect();
            const isInViewport = (
                rect.top >= 0 &&
                rect.left >= 0 &&
                rect.bottom <= window.innerHeight &&
                rect.right <= window.innerWidth
            );
            
            if (!isInViewport) {
                element.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }
            
            // Add semantic type indicator
            const semanticType = window.nazareAnnotations[element.id]?.semanticType;
            if (semanticType) {
                element.setAttribute('data-semantic-type', semanticType);
            }
        }""", element_handle, highlight_type)

    async def get_interactive_elements(self) -> List[Dict[str, Any]]:
        """Get all interactive elements on the page."""
        try:
            return await self.page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('.nazare-interactive');
                    return Array.from(elements).map(el => ({
                        id: el.id,
                        type: el.getAttribute('data-nazare-type'),
                        role: el.getAttribute('data-nazare-role') || el.getAttribute('role'),
                        text: el.getAttribute('data-nazare-text') || el.textContent.trim(),
                        isVisible: window.NazareDOM.checkVisibility(el)
                    }));
                }
            """)
        except Exception as e:
            logger.error(f"Error getting interactive elements: {str(e)}")
            return []

    async def wait_for_navigation(self, timeout: int = 30000):
        """Wait for navigation to complete and reinitialize DOM utilities."""
        try:
            # Wait for initial load
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
            
            # Re-inject and initialize DOM utilities
            script_path = Path(__file__).parent.parent / "static" / "dom-utils.js"
            with open(script_path) as f:
                dom_utils_script = f.read()
            
            # Add script tag directly
            await self.page.add_script_tag(content=dom_utils_script)
            
            # Wait for utilities to be available and initialize
            await self.page.wait_for_function('!!window.NazareDOM', timeout=5000)
            await self.page.evaluate('window.NazareDOM.init()')
            
            logger.info("DOM utilities reinitialized after navigation")
            
        except Exception as e:
            logger.error(f"Error waiting for navigation: {str(e)}")
            raise 
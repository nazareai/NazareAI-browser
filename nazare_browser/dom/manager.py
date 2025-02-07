from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import logging
from playwright.async_api import Page, ElementHandle
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class DOMManager:
    def __init__(self):
        self.dom_cache: Dict[str, Any] = {}
        self.element_cache: Dict[str, Dict[str, Any]] = {}
        self.last_interaction_map: Dict[str, str] = {}
        
    async def capture_dom_state(self, page: Page) -> str:
        """Capture and cache the current DOM state."""
        try:
            # Get page URL as cache key
            url = page.url
            
            # Capture DOM snapshot using JavaScript
            dom_snapshot = await page.evaluate("""() => {
                function processNode(node) {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const element = {
                            tag: node.tagName.toLowerCase(),
                            id: node.id || '',
                            classes: Array.from(node.classList),
                            attributes: {},
                            children: [],
                            text: node.textContent?.trim() || '',
                            isVisible: (
                                node.offsetWidth > 0 && 
                                node.offsetHeight > 0 && 
                                window.getComputedStyle(node).visibility !== 'hidden'
                            ),
                            rect: node.getBoundingClientRect().toJSON()
                        };
                        
                        // Capture relevant attributes
                        for (const attr of node.attributes) {
                            element.attributes[attr.name] = attr.value;
                        }
                        
                        // Process children
                        for (const child of node.children) {
                            element.children.push(processNode(child));
                        }
                        
                        return element;
                    }
                    return null;
                }
                
                return processNode(document.documentElement);
            }""")
            
            # Cache the DOM state
            self.dom_cache[url] = {
                'timestamp': await page.evaluate('Date.now()'),
                'snapshot': dom_snapshot
            }
            
            # Build element cache for quick access
            self._build_element_cache(dom_snapshot, url)
            
            return json.dumps(dom_snapshot, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to capture DOM state: {str(e)}")
            return ""

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

    async def find_element(self, page: Page, description: str) -> Optional[ElementHandle]:
        """Find an element using semantic description and cached state."""
        try:
            url = page.url
            
            # Try exact selectors first for common elements
            if description.lower().startswith(('search', 'input', 'button', 'link')):
                element = await self._try_common_selectors(page, description)
                if element:
                    return element
            
            # Try last successful selector
            if description in self.last_interaction_map:
                try:
                    element = await page.wait_for_selector(
                        self.last_interaction_map[description],
                        timeout=2000
                    )
                    if element and await element.is_visible():
                        return element
                except:
                    pass
            
            # Use DOM utilities to find and prepare element
            selector = await page.evaluate("""(description) => {
                function findBestMatch() {
                    const elements = Array.from(document.querySelectorAll('*'));
                    let bestMatch = null;
                    let bestScore = 0;
                    
                    const desc = description.toLowerCase();
                    
                    for (const el of elements) {
                        let score = 0;
                        
                        // Check text content
                        const text = el.textContent?.toLowerCase() || '';
                        if (text.includes(desc)) {
                            score += text === desc ? 1.0 : 0.5;
                        }
                        
                        // Check attributes
                        const attrs = ['id', 'name', 'placeholder', 'aria-label', 'title', 'alt'];
                        for (const attr of attrs) {
                            const value = el.getAttribute(attr)?.toLowerCase() || '';
                            if (value.includes(desc)) {
                                score += value === desc ? 0.8 : 0.3;
                            }
                        }
                        
                        // Check tag relevance
                        if (['button', 'a', 'input'].includes(el.tagName.toLowerCase())) {
                            if (desc.includes(el.tagName.toLowerCase())) {
                                score += 0.2;
                            }
                            score += 0.1;  // Bonus for interactive elements
                        }
                        
                        // Visibility bonus
                        const style = window.getComputedStyle(el);
                        if (el.offsetWidth > 0 && 
                            el.offsetHeight > 0 && 
                            style.visibility !== 'hidden' && 
                            style.display !== 'none' && 
                            style.opacity !== '0') {
                            score += 0.3;
                        }
                        
                        if (score > bestScore) {
                            bestScore = score;
                            bestMatch = el;
                        }
                    }
                    
                    return { element: bestMatch, score: bestScore };
                }
                
                const result = findBestMatch();
                if (result.element && result.score > 0.5) {
                    // Make element visible and interactive
                    const el = result.element;
                    
                    // Generate a unique selector
                    let selector = el.tagName.toLowerCase();
                    
                    // Add ID if present
                    if (el.id) {
                        selector += `#${el.id}`;
                    }
                    
                    // Add significant classes
                    const significantClasses = Array.from(el.classList)
                        .filter(c => !c.includes('js-') && !c.includes('_'))
                        .join('.');
                    if (significantClasses) {
                        selector += `.${significantClasses}`;
                    }
                    
                    // Add distinguishing attributes
                    const attrs = ['name', 'role', 'aria-label', 'data-testid'];
                    for (const attr of attrs) {
                        if (el.hasAttribute(attr)) {
                            selector += `[${attr}="${el.getAttribute(attr)}"]`;
                        }
                    }
                    
                    return selector;
                }
                
                return null;
            }""", description)
            
            if selector:
                # Wait for element with generated selector
                try:
                    element = await page.wait_for_selector(selector, timeout=2000)
                    if element and await element.is_visible():
                        # Make element visible and interactive
                        await page.evaluate("""(selector) => {
                            const el = document.querySelector(selector);
                            if (el) {
                                // Make element and parents visible
                                let current = el;
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
                                    current = current.parentElement;
                                }
                                
                                // Ensure element is interactive
                                el.disabled = false;
                                el.readOnly = false;
                                el.tabIndex = 0;
                                
                                // Scroll into view
                                el.scrollIntoView({
                                    behavior: 'smooth',
                                    block: 'center'
                                });
                            }
                        }""", selector)
                        
                        self.last_interaction_map[description] = selector
                        return element
                except Exception as e:
                    logger.debug(f"Error using generated selector: {str(e)}")
            
            # Fallback to direct search
            return await self._fallback_find_element(page, description)
            
        except Exception as e:
            logger.error(f"Error finding element: {str(e)}")
            return None

    async def _try_common_selectors(self, page: Page, description: str) -> Optional[ElementHandle]:
        """Try common selectors for frequently used elements."""
        desc = description.lower()
        selectors = []
        
        if 'search' in desc:
            selectors.extend([
                'input[name="search_query"]',
                'input[type="search"]',
                'input[aria-label*="search" i]',
                '#search',
                '.search-input'
            ])
        elif 'button' in desc:
            selectors.extend([
                f'button:has-text("{description}")',
                f'button[aria-label*="{description}" i]',
                'button.primary-button',
                'button.submit-button'
            ])
        elif 'input' in desc:
            selectors.extend([
                f'input[placeholder*="{description}" i]',
                f'input[aria-label*="{description}" i]',
                'input[type="text"]',
                'input.form-input'
            ])
        elif 'link' in desc:
            selectors.extend([
                f'a:has-text("{description}")',
                f'a[aria-label*="{description}" i]',
                f'a[title*="{description}" i]'
            ])
        
        for selector in selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=2000)
                if element and await element.is_visible():
                    # Make element visible using DOM utilities
                    await page.evaluate("""(selector) => {
                        const element = document.querySelector(selector);
                        if (element) {
                            window.makeElementVisible(element);
                        }
                    }""", selector)
                    return element
            except:
                continue
        
        return None

    async def _fallback_find_element(self, page: Page, description: str) -> Optional[ElementHandle]:
        """Fallback method for finding elements when other methods fail."""
        try:
            # Use DOM utilities to wait for and prepare element
            element = await page.evaluate(f"""async (description) => {{
                const element = await window.waitForElement(`[aria-label*="{description}" i], [title*="{description}" i], [placeholder*="{description}" i]`);
                if (element) {{
                    window.makeElementVisible(element);
                    return true;
                }}
                return false;
            }}""", description)
            
            if element:
                # Try to find the now-visible element
                selectors = [
                    f'[aria-label*="{description}" i]',
                    f'[title*="{description}" i]',
                    f'[placeholder*="{description}" i]',
                    f'text="{description}"'
                ]
                
                for selector in selectors:
                    try:
                        el = await page.wait_for_selector(selector, timeout=2000)
                        if el and await el.is_visible():
                            return el
                    except:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error in fallback element search: {str(e)}")
            return None

    def clear_cache(self, url: Optional[str] = None):
        """Clear DOM and element caches."""
        if url:
            self.dom_cache.pop(url, None)
            self.element_cache.pop(url, None)
        else:
            self.dom_cache.clear()
            self.element_cache.clear()
            self.last_interaction_map.clear() 
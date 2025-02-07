from typing import Dict, Any, List, Optional
from playwright.async_api import Page, ElementHandle
import json
from bs4 import BeautifulSoup


class DOMAnnotator:
    def __init__(self):
        self.cached_elements: Dict[str, Dict[str, Any]] = {}

    async def annotate_page(self, page: Page) -> str:
        """
        Analyze the page and create semantic annotations for important elements.
        Returns a JSON string with annotated elements.
        """
        # Get page content and create soup
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Clear previous cache
        self.cached_elements = {}
        
        # Collect and annotate interactive elements
        annotations = {
            "clickable": await self._find_clickable(page),
            "forms": await self._find_forms(page),
            "navigation": await self._find_navigation(page),
            "content": await self._find_content_areas(page)
        }
        
        return json.dumps(annotations, indent=2)

    async def find_element(self, page: Page, description: str) -> Optional[ElementHandle]:
        """
        Find an element on the page based on semantic description.
        Uses the cached annotations to find the most relevant element.
        """
        # First, ensure we have fresh annotations
        if not self.cached_elements:
            await self.annotate_page(page)
        
        # Use custom element finding logic based on the description
        element = await self._find_best_match(page, description)
        return element

    async def _find_clickable(self, page: Page) -> List[Dict[str, Any]]:
        """Find and annotate clickable elements."""
        clickable = []
        
        # Find buttons and links
        elements = await page.query_selector_all('button, a, [role="button"], [onclick]')
        
        for element in elements:
            # Get element properties
            text = await element.text_content()
            tag = await element.evaluate('element => element.tagName.toLowerCase()')
            
            # Get computed role
            role = await element.evaluate('''element => {
                return element.getAttribute('role') || element.tagName.toLowerCase()
            }''')
            
            # Create semantic annotation
            annotation = {
                "type": "clickable",
                "tag": tag,
                "role": role,
                "text": text.strip() if text else "",
                "selector": await self._generate_unique_selector(element),
                "visible": await element.is_visible()
            }
            
            clickable.append(annotation)
            
        return clickable

    async def _find_forms(self, page: Page) -> List[Dict[str, Any]]:
        """Find and annotate form elements."""
        forms = []
        
        # Find form elements
        elements = await page.query_selector_all('form, input, textarea, select')
        
        for element in elements:
            tag = await element.evaluate('element => element.tagName.toLowerCase()')
            
            annotation = {
                "type": "form",
                "tag": tag,
                "input_type": await element.evaluate('element => element.type || ""'),
                "name": await element.evaluate('element => element.name || ""'),
                "placeholder": await element.evaluate('element => element.placeholder || ""'),
                "selector": await self._generate_unique_selector(element),
                "required": await element.evaluate('element => element.required || false')
            }
            
            forms.append(annotation)
            
        return forms

    async def _find_navigation(self, page: Page) -> List[Dict[str, Any]]:
        """Find and annotate navigation elements."""
        nav_elements = []
        
        # Find navigation elements
        elements = await page.query_selector_all('nav, [role="navigation"], header menu')
        
        for element in elements:
            annotation = {
                "type": "navigation",
                "text": (await element.text_content() or "").strip(),
                "selector": await self._generate_unique_selector(element),
                "links": await self._extract_links(element)
            }
            
            nav_elements.append(annotation)
            
        return nav_elements

    async def _find_content_areas(self, page: Page) -> List[Dict[str, Any]]:
        """Find and annotate main content areas."""
        content_areas = []
        
        # Find main content areas
        elements = await page.query_selector_all('main, article, [role="main"], .content, #content')
        
        for element in elements:
            annotation = {
                "type": "content",
                "role": await element.evaluate('element => element.getAttribute("role") || ""'),
                "selector": await self._generate_unique_selector(element),
                "headings": await self._extract_headings(element)
            }
            
            content_areas.append(annotation)
            
        return content_areas

    async def _generate_unique_selector(self, element: ElementHandle) -> str:
        """Generate a unique CSS selector for an element."""
        return await element.evaluate('''element => {
            const path = [];
            while (element.nodeType === Node.ELEMENT_NODE) {
                let selector = element.nodeName.toLowerCase();
                if (element.id) {
                    selector += '#' + element.id;
                    path.unshift(selector);
                    break;
                } else {
                    let sibling = element;
                    let nth = 1;
                    while (sibling.previousElementSibling) {
                        sibling = sibling.previousElementSibling;
                        if (sibling.nodeName.toLowerCase() === selector) nth++;
                    }
                    if (nth > 1) selector += `:nth-of-type(${nth})`;
                }
                path.unshift(selector);
                element = element.parentElement;
            }
            return path.join(' > ');
        }''')

    async def _extract_links(self, element: ElementHandle) -> List[Dict[str, Any]]:
        """Extract links from a navigation element."""
        links = []
        elements = await element.query_selector_all('a')
        
        for link in elements:
            links.append({
                "text": (await link.text_content() or "").strip(),
                "href": await link.evaluate('element => element.href || ""'),
                "selector": await self._generate_unique_selector(link)
            })
            
        return links

    async def _extract_headings(self, element: ElementHandle) -> List[Dict[str, Any]]:
        """Extract headings from a content area."""
        headings = []
        elements = await element.query_selector_all('h1, h2, h3, h4, h5, h6')
        
        for heading in elements:
            headings.append({
                "level": await heading.evaluate('element => element.tagName.toLowerCase()'),
                "text": (await heading.text_content() or "").strip(),
                "selector": await self._generate_unique_selector(heading)
            })
            
        return headings

    async def _find_best_match(self, page: Page, description: str) -> Optional[ElementHandle]:
        """Find the best matching element based on semantic description."""
        # Implement fuzzy matching logic here
        # This could use techniques like cosine similarity with embeddings
        # For now, we'll use a simple text matching approach
        
        # Try exact text match first
        element = await page.query_selector(f'text="{description}"')
        if element:
            return element
            
        # Try partial text match
        element = await page.query_selector(f'text="{description}"i')
        if element:
            return element
            
        # Try aria-label match
        element = await page.query_selector(f'[aria-label*="{description}"i]')
        if element:
            return element
            
        return None 
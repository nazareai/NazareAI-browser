from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import logging
from datetime import datetime, timedelta
from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)


class CookieManager:
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path("cache/cookies")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_age_days = 30  # Maximum age for stored cookies
        
    def _get_cookie_file(self, domain: str) -> Path:
        """Get the path to the cookie file for a domain."""
        return self.storage_dir / f"{domain}.json"
    
    async def save_cookies(self, context: BrowserContext, url: str):
        """Save cookies for a domain."""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            
            # Get all cookies from the context
            cookies = await context.cookies([url])
            
            # Add consent cookies for specific domains
            if "ft.com" in domain:
                cookies.extend([
                    {
                        "name": "FTConsent",
                        "value": "true",
                        "domain": ".ft.com",
                        "path": "/"
                    },
                    {
                        "name": "cookieConsent",
                        "value": "true",
                        "domain": ".ft.com",
                        "path": "/"
                    },
                    {
                        "name": "accept_cookies",
                        "value": "true",
                        "domain": ".ft.com",
                        "path": "/"
                    }
                ])
            
            # Add timestamp for expiration tracking
            cookie_data = {
                "timestamp": datetime.now().isoformat(),
                "cookies": cookies
            }
            
            # Save to file
            cookie_file = self._get_cookie_file(domain)
            with open(cookie_file, "w") as f:
                json.dump(cookie_data, f, indent=2)
                
            logger.info(f"Saved {len(cookies)} cookies for {domain}")
            
        except Exception as e:
            logger.error(f"Failed to save cookies for {url}: {str(e)}")
    
    async def load_cookies(self, context: BrowserContext, url: str) -> bool:
        """Load cookies for a domain if they exist and are not expired."""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            
            cookie_file = self._get_cookie_file(domain)
            if not cookie_file.exists():
                # Add default consent cookies for specific domains
                if "ft.com" in domain:
                    await context.add_cookies([
                        {
                            "name": "FTConsent",
                            "value": "true",
                            "domain": ".ft.com",
                            "path": "/"
                        },
                        {
                            "name": "cookieConsent",
                            "value": "true",
                            "domain": ".ft.com",
                            "path": "/"
                        },
                        {
                            "name": "accept_cookies",
                            "value": "true",
                            "domain": ".ft.com",
                            "path": "/"
                        }
                    ])
                    logger.info(f"Added default consent cookies for {domain}")
                    return True
                return False
            
            # Load cookie data
            with open(cookie_file) as f:
                cookie_data = json.load(f)
            
            # Check if cookies are expired
            timestamp = datetime.fromisoformat(cookie_data["timestamp"])
            if datetime.now() - timestamp > timedelta(days=self.max_age_days):
                logger.info(f"Cookies for {domain} are expired")
                cookie_file.unlink()
                return False
            
            # Add cookies to context
            await context.add_cookies(cookie_data["cookies"])
            logger.info(f"Loaded {len(cookie_data['cookies'])} cookies for {domain}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load cookies for {url}: {str(e)}")
            return False
    
    def clear_expired_cookies(self):
        """Clear expired cookie files."""
        try:
            for cookie_file in self.storage_dir.glob("*.json"):
                try:
                    with open(cookie_file) as f:
                        cookie_data = json.load(f)
                    
                    timestamp = datetime.fromisoformat(cookie_data["timestamp"])
                    if datetime.now() - timestamp > timedelta(days=self.max_age_days):
                        cookie_file.unlink()
                        logger.info(f"Cleared expired cookies: {cookie_file.name}")
                        
                except Exception as e:
                    logger.error(f"Error processing cookie file {cookie_file}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Failed to clear expired cookies: {str(e)}")
    
    def clear_all_cookies(self):
        """Clear all stored cookies."""
        try:
            for cookie_file in self.storage_dir.glob("*.json"):
                cookie_file.unlink()
            logger.info("Cleared all stored cookies")
            
        except Exception as e:
            logger.error(f"Failed to clear all cookies: {str(e)}")
    
    async def handle_consent_dialogs(self, page, url: str):
        """Handle common cookie consent dialogs."""
        try:
            # FT.com consent dialog
            if "ft.com" in url:
                try:
                    # First try JavaScript approach
                    await page.evaluate("""() => {
                        function acceptCookies() {
                            const selectors = [
                                'button[title="Accept cookies"]',
                                'button[data-trackable="accept-cookies"]',
                                '#consent-accept-all',
                                '.cookie-consent__button--accept',
                                'button:has-text("Accept")',
                                'button[data-trackable="accept-consent"]'
                            ];
                            
                            for (const selector of selectors) {
                                const button = document.querySelector(selector);
                                if (button) {
                                    button.click();
                                    console.log('Clicked cookie consent via JS:', selector);
                                    return true;
                                }
                            }
                            return false;
                        }
                        acceptCookies();
                    }""")
                    
                    # Then try Playwright selectors
                    consent_selectors = [
                        'button[title="Accept cookies"]',
                        'button[data-trackable="accept-cookies"]',
                        '#consent-accept-all',
                        '.cookie-consent__button--accept',
                        'button:has-text("Accept")',
                        'button[data-trackable="accept-consent"]'
                    ]
                    
                    for selector in consent_selectors:
                        try:
                            button = await page.wait_for_selector(selector, timeout=2000)
                            if button and await button.is_visible():
                                await button.click()
                                logger.info(f"Clicked FT.com cookie consent button: {selector}")
                                await page.wait_for_load_state("networkidle", timeout=2000)
                                break
                        except Exception as e:
                            continue
                    
                    # Add cookies directly
                    await page.context.add_cookies([
                        {
                            "name": "FTConsent",
                            "value": "true",
                            "domain": ".ft.com",
                            "path": "/"
                        },
                        {
                            "name": "cookieConsent",
                            "value": "true",
                            "domain": ".ft.com",
                            "path": "/"
                        }
                    ])
                    
                except Exception as e:
                    logger.error(f"Error handling FT.com cookie consent: {str(e)}")
            
            # YouTube consent dialog
            elif "youtube.com" in url:
                try:
                    # Try multiple approaches for YouTube consent
                    await page.evaluate("""() => {
                        function acceptYouTubeConsent() {
                            const buttons = document.querySelectorAll('button');
                            for (const button of buttons) {
                                if (button.textContent.includes('Accept all') || 
                                    button.textContent.includes('I agree') ||
                                    button.getAttribute('aria-label')?.includes('Accept')) {
                                    button.click();
                                    return true;
                                }
                            }
                            return false;
                        }
                        acceptYouTubeConsent();
                    }""")
                    
                    # Also try Playwright selector
                    consent_button = await page.wait_for_selector(
                        'button[aria-label="Accept all"], button:has-text("Accept all")',
                        timeout=2000
                    )
                    if consent_button and await consent_button.is_visible():
                        await consent_button.click()
                        logger.info("Accepted YouTube cookie consent")
                        await page.wait_for_load_state("networkidle", timeout=2000)
                except Exception as e:
                    logger.debug(f"YouTube consent handling: {str(e)}")
            
            # Generic consent dialogs
            common_selectors = [
                'button[id*="accept"]',
                'button[class*="accept"]',
                'button[id*="consent"]',
                'button[class*="consent"]',
                'a[id*="accept"]',
                'a[class*="accept"]',
                '[aria-label*="accept" i]',
                '[title*="accept" i]',
                'button:has-text("Accept")',
                'button:has-text("Accept all")',
                'button:has-text("Allow all")',
                'button:has-text("I agree")'
            ]
            
            # First try JavaScript approach for generic dialogs
            await page.evaluate("""() => {
                function acceptGenericConsent() {
                    const selectors = [
                        'button[id*="accept"]',
                        'button[class*="accept"]',
                        'button[id*="consent"]',
                        'button[class*="consent"]',
                        'a[id*="accept"]',
                        'a[class*="accept"]',
                        '[aria-label*="accept" i]',
                        '[title*="accept" i]'
                    ];
                    
                    for (const selector of selectors) {
                        const elements = document.querySelectorAll(selector);
                        for (const element of elements) {
                            if (element.offsetWidth > 0 && 
                                element.offsetHeight > 0 && 
                                window.getComputedStyle(element).visibility !== 'hidden') {
                                element.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }
                acceptGenericConsent();
            }""")
            
            # Then try Playwright selectors
            for selector in common_selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=1000)
                    if button and await button.is_visible():
                        await button.click()
                        logger.info(f"Clicked consent button: {selector}")
                        await page.wait_for_load_state("networkidle", timeout=1000)
                        break
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.error(f"Error handling consent dialogs: {str(e)}")
            
        # Final check - remove any remaining consent dialogs via JavaScript
        try:
            await page.evaluate("""() => {
                const commonConsentSelectors = [
                    '#cookie-banner',
                    '#cookie-consent',
                    '#consent-banner',
                    '.cookie-notice',
                    '.consent-banner',
                    '[aria-label*="cookie" i]',
                    '[class*="cookie-banner"]',
                    '[class*="consent-banner"]',
                    '[id*="cookie-banner"]',
                    '[id*="consent-banner"]'
                ];
                
                for (const selector of commonConsentSelectors) {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => el.remove());
                }
            }""")
        except Exception as e:
            logger.debug(f"Error removing remaining consent dialogs: {str(e)}") 
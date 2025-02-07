from typing import Dict, Any, Optional
from pathlib import Path
import yaml
from urllib.parse import urlparse
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)


class DomainSettings:
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path("config/domains")
        self.settings_cache: Dict[str, Dict[str, Any]] = {}
        self._load_settings()
    
    def _load_settings(self):
        """Load all domain settings from the config directory."""
        if not self.config_dir.exists():
            logger.warning(f"Domain settings directory {self.config_dir} does not exist")
            return
        
        for config_file in self.config_dir.glob("*.yaml"):
            try:
                with open(config_file) as f:
                    domain_settings = yaml.safe_load(f)
                    if isinstance(domain_settings, dict):
                        domain = config_file.stem
                        self.settings_cache[domain] = domain_settings
            except Exception as e:
                logger.error(f"Failed to load domain settings from {config_file}: {str(e)}")
    
    def _get_domain_settings(self, url: str) -> Dict[str, Any]:
        """Get settings for a specific domain."""
        domain = urlparse(url).netloc
        
        # Try exact domain match
        if domain in self.settings_cache:
            return self.settings_cache[domain]
        
        # Try wildcard match
        base_domain = ".".join(domain.split(".")[-2:])  # e.g., "google.com" from "www.google.com"
        if base_domain in self.settings_cache:
            return self.settings_cache[base_domain]
        
        # Return default settings
        return self.settings_cache.get("default", {})
    
    async def apply_settings(self, page: Page, url: str):
        """Apply domain-specific settings to a page."""
        settings = self._get_domain_settings(url)
        
        try:
            # Apply viewport settings
            if "viewport" in settings:
                await page.set_viewport_size(settings["viewport"])
            
            # Apply user agent
            if "user_agent" in settings:
                await page.set_extra_http_headers({"User-Agent": settings["user_agent"]})
            
            # Apply geolocation
            if "geolocation" in settings:
                context = page.context
                await context.grant_permissions(['geolocation'])
                await context.set_geolocation(settings["geolocation"])
            
            # Apply permissions
            if "permissions" in settings:
                for permission in settings["permissions"]:
                    await page.context.grant_permissions([permission])
            
            # Apply custom JavaScript
            if "scripts" in settings:
                for script in settings["scripts"]:
                    await page.add_init_script(script=script)
            
            # Apply custom styles
            if "styles" in settings:
                for style in settings["styles"]:
                    await page.evaluate(f"""
                        const style = document.createElement('style');
                        style.textContent = `{style}`;
                        document.head.appendChild(style);
                    """)
            
            # Apply cookie settings
            if "cookies" in settings:
                await page.context.add_cookies(settings["cookies"])
            
            # Apply request headers
            if "headers" in settings:
                await page.set_extra_http_headers(settings["headers"])
            
            # Apply request interception rules
            if "block_resources" in settings:
                for resource_type in settings["block_resources"]:
                    await page.route(f"**/*.{resource_type}", lambda route: route.abort())
            
            # Apply custom timing settings
            if "timing" in settings:
                timing = settings["timing"]
                if "default_timeout" in timing:
                    page.set_default_timeout(timing["default_timeout"])
                if "default_navigation_timeout" in timing:
                    page.set_default_navigation_timeout(timing["default_navigation_timeout"])
            
            logger.info(f"Applied domain settings for {url}")
            
        except Exception as e:
            logger.error(f"Failed to apply domain settings for {url}: {str(e)}")
    
    def create_domain_settings(self, domain: str, settings: Dict[str, Any]):
        """Create or update settings for a domain."""
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Write settings to file
            config_file = self.config_dir / f"{domain}.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(settings, f)
            
            # Update cache
            self.settings_cache[domain] = settings
            
            logger.info(f"Created domain settings for {domain}")
            
        except Exception as e:
            logger.error(f"Failed to create domain settings for {domain}: {str(e)}")
            raise
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Get the default domain settings template."""
        return {
            "viewport": {
                "width": 1920,
                "height": 1080
            },
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "geolocation": {
                "latitude": 0,
                "longitude": 0,
                "accuracy": 100
            },
            "permissions": [],
            "scripts": [],
            "styles": [],
            "cookies": [],
            "headers": {},
            "block_resources": [],
            "timing": {
                "default_timeout": 30000,
                "default_navigation_timeout": 30000
            }
        } 
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml
import importlib.util
import inspect
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)


class Plugin:
    """Base class for all plugins."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)
    
    async def initialize(self, page: Page):
        """Initialize the plugin with the browser page."""
        pass
    
    async def before_navigation(self, url: str):
        """Called before navigating to a new URL."""
        pass
    
    async def after_navigation(self, url: str):
        """Called after navigating to a new URL."""
        pass
    
    async def before_action(self, action: Dict[str, Any]):
        """Called before performing a browser action."""
        pass
    
    async def after_action(self, action: Dict[str, Any]):
        """Called after performing a browser action."""
        pass


class AdBlocker(Plugin):
    """Plugin for blocking advertisements."""
    
    async def initialize(self, page: Page):
        # Block common ad domains
        await page.route("**/{ads,analytics,trackers}/**", lambda route: route.abort())
        
        # Block by resource type
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media"] and self._is_ad(route.request.url) else route.continue_())
    
    def _is_ad(self, url: str) -> bool:
        """Check if a URL is likely an advertisement."""
        ad_keywords = ["ad", "ads", "advert", "banner", "sponsor", "tracking"]
        return any(keyword in url.lower() for keyword in ad_keywords)


class PrivacyGuard(Plugin):
    """Plugin for enhancing privacy."""
    
    async def initialize(self, page: Page):
        # Clear cookies before navigation
        await page.context.clear_cookies()
        
        # Block trackers
        await page.route("**/{tracking,analytics,pixel}/**", lambda route: route.abort())
        
        # Spoof common fingerprinting APIs
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [] });
        """)


class AutoScroll(Plugin):
    """Plugin for automatic scrolling."""
    
    async def after_navigation(self, url: str):
        if not self.config.get("enabled", True):
            return
            
        scroll_amount = self.config.get("scroll_amount", 800)
        scroll_delay = self.config.get("scroll_delay", 1000)
        
        await self.page.evaluate(f"""
            async function autoScroll() {{
                await new Promise((resolve) => {{
                    let totalHeight = 0;
                    let distance = {scroll_amount};
                    let timer = setInterval(() => {{
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        
                        if(totalHeight >= document.body.scrollHeight) {{
                            clearInterval(timer);
                            resolve();
                        }}
                    }}, {scroll_delay});
                }});
            }}
            autoScroll();
        """)


class PluginManager:
    def __init__(self, config_path: Optional[Path] = None):
        self.plugins: Dict[str, Plugin] = {}
        self.config = self._load_config(config_path)
        self._load_plugins()
    
    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load plugin configuration from YAML file."""
        if not config_path:
            config_path = Path("config/plugins.yaml")
            
        if not config_path.exists():
            return {}
            
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def _load_plugins(self):
        """Load all enabled plugins."""
        # Load built-in plugins
        self.plugins["adblocker"] = AdBlocker(self.config.get("adblocker", {}))
        self.plugins["privacy"] = PrivacyGuard(self.config.get("privacy", {}))
        self.plugins["autoscroll"] = AutoScroll(self.config.get("autoscroll", {}))
        
        # Load custom plugins from config
        custom_plugins_dir = Path(self.config.get("custom_plugins_dir", "plugins"))
        if custom_plugins_dir.exists():
            for plugin_file in custom_plugins_dir.glob("*.py"):
                try:
                    self._load_custom_plugin(plugin_file)
                except Exception as e:
                    logger.error(f"Failed to load plugin {plugin_file}: {str(e)}")
    
    def _load_custom_plugin(self, plugin_file: Path):
        """Load a custom plugin from a Python file."""
        try:
            # Import the module
            spec = importlib.util.spec_from_file_location(plugin_file.stem, plugin_file)
            if not spec or not spec.loader:
                raise ImportError(f"Failed to load spec for {plugin_file}")
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, Plugin) and 
                    obj != Plugin):
                    # Initialize plugin
                    config = self.config.get(plugin_file.stem, {})
                    self.plugins[plugin_file.stem] = obj(config)
                    break
                    
        except Exception as e:
            logger.error(f"Error loading custom plugin {plugin_file}: {str(e)}")
            raise
    
    async def initialize(self, page: Page):
        """Initialize all enabled plugins."""
        for plugin in self.plugins.values():
            if plugin.enabled:
                try:
                    await plugin.initialize(page)
                except Exception as e:
                    logger.error(f"Failed to initialize plugin {plugin.__class__.__name__}: {str(e)}")
    
    async def before_navigation(self, url: str):
        """Notify plugins before navigation."""
        for plugin in self.plugins.values():
            if plugin.enabled:
                await plugin.before_navigation(url)
    
    async def after_navigation(self, url: str):
        """Notify plugins after navigation."""
        for plugin in self.plugins.values():
            if plugin.enabled:
                await plugin.after_navigation(url)
    
    async def before_action(self, action: Dict[str, Any]):
        """Notify plugins before browser action."""
        for plugin in self.plugins.values():
            if plugin.enabled:
                await plugin.before_action(action)
    
    async def after_action(self, action: Dict[str, Any]):
        """Notify plugins after browser action."""
        for plugin in self.plugins.values():
            if plugin.enabled:
                await plugin.after_action(action) 
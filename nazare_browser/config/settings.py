"""Configuration management for NazareAI Browser."""
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import logging
from ..exceptions import ConfigurationError

logger = logging.getLogger(__name__)

class BrowserConfig(BaseModel):
    """Browser configuration settings."""
    headless: bool = Field(default=False, description="Run browser in headless mode")
    viewport: Dict[str, int] = Field(
        default={"width": 1280, "height": 720},
        description="Browser viewport dimensions"
    )
    default_timeout: int = Field(default=30000, description="Default timeout in milliseconds")
    default_navigation_timeout: int = Field(default=30000, description="Navigation timeout in milliseconds")
    downloads_path: str = Field(default="./downloads", description="Path for downloaded files")
    screenshots_path: str = Field(default="./screenshots", description="Path for screenshots")
    block_resources: bool = Field(default=False, description="Whether to block non-critical resources")
    user_agent: Optional[str] = Field(default=None, description="Custom user agent string")
    launch_args: List[str] = Field(default_factory=list, description="Browser launch arguments")

class LLMConfig(BaseModel):
    """LLM configuration settings."""
    model: str = Field(
        default="anthropic/claude-3.5-sonnet:beta",
        description="LLM model to use"
    )
    temperature: float = Field(default=0.7, description="LLM temperature")
    max_tokens: int = Field(default=2000, description="Maximum tokens per request")
    context_window: int = Field(default=100000, description="Context window size")

class PluginConfig(BaseModel):
    """Plugin configuration settings."""
    custom_plugins_dir: str = Field(default="./plugins", description="Custom plugins directory")
    enabled_plugins: Dict[str, bool] = Field(default_factory=dict, description="Enabled/disabled plugins")

class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    level: str = Field(default="INFO", description="Logging level")
    file: Optional[str] = Field(default=None, description="Log file path")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )

class CacheConfig(BaseModel):
    """Cache configuration settings."""
    enabled: bool = Field(default=True, description="Enable caching")
    directory: str = Field(default=".cache", description="Cache directory")
    max_size_mb: int = Field(default=1000, description="Maximum cache size in MB")
    ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")

class CookieConfig(BaseModel):
    """Cookie configuration settings."""
    max_age_days: int = Field(default=7, description="Maximum cookie age in days")
    domains: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Domain-specific cookie settings")

class ResourceBlockingConfig(BaseModel):
    """Resource blocking configuration."""
    enabled: bool = Field(default=True, description="Enable resource blocking")
    blocked_resources: List[str] = Field(default_factory=list, description="Resource patterns to block")
    allowed_domains: List[str] = Field(default_factory=list, description="Domains to allow resources from")

class HeadersConfig(BaseModel):
    """Headers configuration."""
    ft_com: Dict[str, Union[str, int]] = Field(default_factory=dict, alias="ft.com", description="Headers for ft.com")

class NavigationConfig(BaseModel):
    """Navigation configuration."""
    timeout: int = Field(default=30000, description="Navigation timeout")
    wait_until: str = Field(default="networkidle", description="Wait until condition")
    referer: str = Field(default="https://www.google.com", description="Default referer")

class ElementFindingConfig(BaseModel):
    """Element finding configuration."""
    timeout: int = Field(default=10000, description="Element finding timeout")
    retry_interval: int = Field(default=500, description="Retry interval")
    max_retries: int = Field(default=3, description="Maximum retries")

class Settings(BaseSettings):
    """Main application settings."""
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    plugins: PluginConfig = Field(default_factory=PluginConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    domains_config_dir: str = Field(default="config/domains", description="Domain-specific config directory")
    cookies: CookieConfig = Field(default_factory=CookieConfig)
    resource_blocking: ResourceBlockingConfig = Field(default_factory=ResourceBlockingConfig)
    headers: HeadersConfig = Field(default_factory=HeadersConfig)
    navigation: NavigationConfig = Field(default_factory=NavigationConfig)
    element_finding: ElementFindingConfig = Field(default_factory=ElementFindingConfig)

    class Config:
        populate_by_name = True

    @classmethod
    def load_from_file(cls, config_path: Optional[Path] = None) -> 'Settings':
        """Load settings from a YAML file."""
        if not config_path:
            config_path = Path("config/browser.yaml")

        try:
            if config_path.exists():
                with open(config_path) as f:
                    config_data = yaml.safe_load(f)
                return cls(**config_data)
            else:
                logger.warning(f"Config file not found at {config_path}, using defaults")
                return cls()
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            raise ConfigurationError(f"Failed to load configuration: {str(e)}")

    def get_domain_settings(self, domain: str) -> Dict[str, Any]:
        """Get domain-specific settings."""
        try:
            domain_config_path = Path(self.domains_config_dir) / f"{domain}.yaml"
            if domain_config_path.exists():
                with open(domain_config_path) as f:
                    return yaml.safe_load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading domain config for {domain}: {str(e)}")
            return {}

class DomainSettings:
    """Domain-specific settings manager."""
    def __init__(self):
        self.settings = Settings.load_from_file()
        self._domain_cache: Dict[str, Dict[str, Any]] = {}

    def get_settings(self, domain: str) -> Dict[str, Any]:
        """Get settings for a specific domain."""
        if domain not in self._domain_cache:
            self._domain_cache[domain] = self.settings.get_domain_settings(domain)
        return self._domain_cache[domain]

    async def apply_settings(self, page: Any, url: str):
        """Apply domain-specific settings to a page."""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        settings = self.get_settings(domain)

        if not settings:
            return

        try:
            # Apply headers
            if "headers" in settings:
                await page.set_extra_http_headers(settings["headers"])

            # Apply cookies
            if "cookies" in settings:
                for cookie in settings["cookies"]:
                    await page.context.add_cookies([cookie])

            # Apply other domain-specific settings
            if "viewport" in settings:
                await page.set_viewport_size(settings["viewport"])

            if "user_agent" in settings:
                await page.set_user_agent(settings["user_agent"])

            logger.info(f"Applied domain settings for {domain}")

        except Exception as e:
            logger.error(f"Error applying domain settings for {domain}: {str(e)}") 
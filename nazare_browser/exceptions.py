"""Custom exceptions for the NazareAI Browser."""

class BrowserError(Exception):
    """Base exception for browser-related errors."""
    pass

class NavigationError(BrowserError):
    """Exception raised when navigation fails."""
    pass

class ElementNotFoundError(BrowserError):
    """Exception raised when an element cannot be found."""
    pass

class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass

class LLMResponseError(LLMError):
    """Exception raised when LLM response is invalid or cannot be parsed."""
    pass

class LLMAPIError(LLMError):
    """Exception raised when there's an error communicating with the LLM API."""
    pass

class ConfigurationError(Exception):
    """Exception raised when there's an error in configuration."""
    pass

class PluginError(Exception):
    """Base exception for plugin-related errors."""
    pass

class PluginLoadError(PluginError):
    """Exception raised when a plugin fails to load."""
    pass

class PluginExecutionError(PluginError):
    """Exception raised when a plugin fails during execution."""
    pass

class DOMError(Exception):
    """Base exception for DOM-related errors."""
    pass

class InvalidSelectorError(DOMError):
    """Exception raised when a selector is invalid."""
    pass

class StaleElementError(DOMError):
    """Exception raised when an element reference is stale."""
    pass

class TimeoutError(BrowserError):
    """Exception raised when an operation times out."""
    pass

class NetworkError(BrowserError):
    """Exception raised when there's a network-related error."""
    pass

class SecurityError(Exception):
    """Exception raised when there's a security-related error."""
    pass

class ResourceError(Exception):
    """Exception raised when there's an error with browser resources."""
    pass

class CookieError(Exception):
    """Exception raised when there's an error managing cookies."""
    pass 
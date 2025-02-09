import asyncio
import typer
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.panel import Panel
from rich.logging import RichHandler
import os
from dotenv import load_dotenv
import logging
import json
from typing import Optional

from .core.browser import Browser
from .config.settings import Settings
from .exceptions import BrowserError, ConfigurationError

# Initialize typer app and rich console
app = typer.Typer()
console = Console()

def setup_logging(config: Settings):
    """Setup logging with rich handler."""
    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)
    
    handlers = [
        RichHandler(
            console=console,
            show_time=False,
            show_path=False,
            rich_tracebacks=True
        )
    ]
    
    if config.logging.file:
        # Ensure log directory exists
        log_path = Path(config.logging.file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(config.logging.file))
    
    logging.basicConfig(
        level=log_level,
        format=config.logging.format,
        handlers=handlers
    )

def check_environment():
    """Check required environment variables."""
    required_vars = ["OPENROUTER_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        console.print("[red]Error: Missing required environment variables:[/red]")
        for var in missing_vars:
            console.print(f"  - {var}")
        console.print("\nPlease set them in your .env file or environment")
        raise typer.Exit(1)

@app.command()
def main(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    headless: bool = typer.Option(
        None,
        "--headless",
        "-h",
        help="Run browser in headless mode",
    ),
):
    """
    NazareAI Browser - An LLM-controlled browser for AI agents.
    """
    try:
        # Load environment variables
        load_dotenv()
        check_environment()
        
        # Load configuration
        settings = Settings.load_from_file(config)
        
        # Override headless mode if specified
        if headless is not None:
            settings.browser.headless = headless
        
        # Setup logging
        setup_logging(settings)
        
        # Run the browser
        asyncio.run(run_browser(settings))
        
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {str(e)}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    except Exception as e:
        console.print(f"[red]Fatal error: {str(e)}[/red]")
        logging.exception("Fatal error occurred")
        raise typer.Exit(1)

async def run_browser(settings: Settings):
    """Run the browser with the specified settings."""
    # Initialize browser
    browser = Browser(settings)
    
    # Create progress display
    progress_display = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console
    )
    
    # Start browser with progress
    with progress_display:
        task = progress_display.add_task("[cyan]Starting browser...", total=None)
        try:
            await browser.start()
            progress_display.update(task, completed=True)
        except BrowserError as e:
            progress_display.update(task, description=f"[red]Failed to start browser: {str(e)}[/red]")
            raise

    console.print("[green]Browser started successfully![/green]")
    console.print(
        "\nEnter commands in natural language. Examples:"
        "\n- 'Go to youtube and find videos about Python programming'"
        "\n- 'Visit ft.com and summarize the top 5 articles'"
        "\n- 'Search for a product on Amazon and compare prices'"
        "\n\nType 'exit' to quit."
    )

    # Main command loop
    while True:
        try:
            # Get command from user
            command = Prompt.ask("\n[cyan]Enter command[/cyan]")
            
            if command.lower() in ("exit", "quit"):
                break
            
            # Execute command with live updates
            with Live(
                Panel("Initializing...", title="Command Execution", border_style="blue"),
                refresh_per_second=4,
                console=console
            ) as live:
                def update_status(msg: str):
                    live.update(Panel(msg, title="Command Execution", border_style="blue"))
                
                # Setup logging handler to update live display
                class LiveDisplayHandler(logging.Handler):
                    def emit(self, record):
                        msg = self.format(record)
                        update_status(msg)
                
                # Add live display handler
                live_handler = LiveDisplayHandler()
                live_handler.setFormatter(logging.Formatter('%(message)s'))
                logging.getLogger().addHandler(live_handler)
                
                try:
                    # Execute command
                    result = await browser.execute_command(command)
                    
                    # Display result
                    if isinstance(result, str):
                        update_status(f"[green]Command completed:[/green]\n{result}")
                    else:
                        update_status(f"[green]Command completed:[/green]\n{json.dumps(result, indent=2)}")
                        
                except BrowserError as e:
                    update_status(f"[red]Browser error: {str(e)}[/red]")
                except Exception as e:
                    update_status(f"[red]Error: {str(e)}[/red]")
                    logging.exception("Error executing command")
                finally:
                    # Remove live display handler
                    logging.getLogger().removeHandler(live_handler)
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Command interrupted[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]")
            logging.exception("Error in command loop")

    # Clean up
    try:
        await browser.close()
        console.print("[green]Browser closed successfully![/green]")
    except Exception as e:
        console.print(f"[red]Error closing browser: {str(e)}[/red]")
        logging.exception("Error closing browser")

if __name__ == "__main__":
    app() 
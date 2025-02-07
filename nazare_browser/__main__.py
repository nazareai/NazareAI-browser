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

from .core.browser import Browser

# Initialize typer app and rich console
app = typer.Typer()
console = Console()

# Configure logging with rich handler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, show_time=False, show_path=False)]
)

# Load environment variables
load_dotenv()


@app.command()
def main(
    config: Path = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    headless: bool = typer.Option(
        False,
        "--headless",
        "-h",
        help="Run browser in headless mode",
    ),
):
    """
    NazareAI Browser - An LLM-controlled browser for AI agents.
    """
    # Ensure OpenRouter API key is set
    if not os.getenv("OPENROUTER_API_KEY"):
        console.print("[red]Error: OPENROUTER_API_KEY environment variable is not set[/red]")
        console.print("Please set it in your .env file or environment variables")
        raise typer.Exit(1)

    async def run_browser():
        # Initialize browser
        browser = Browser(config)
        
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
            await browser.start()
            progress_display.update(task, completed=True)

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
                            
                    finally:
                        # Remove live display handler
                        logging.getLogger().removeHandler(live_handler)
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Command interrupted[/yellow]")
            except Exception as e:
                console.print(f"\n[red]Error: {str(e)}[/red]")

        # Clean up
        await browser.close()
        console.print("[green]Browser closed successfully![/green]")

    # Run the async main loop
    try:
        asyncio.run(run_browser())
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Fatal error: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app() 
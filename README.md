# NazareAI Browser

THIS PROJECT IS IN DEVELOPMENT AND NOT READY FOR PRODUCTION USE.

An LLM-controlled browser automation system powered by OpenRouter and Playwright. This system allows AI agents to perform complex web tasks through natural language commands.

## Features

- Natural language control of web browser actions
- Smart DOM handling with element annotation for LLM understanding
- Plugin system for extensibility (ad blocking, etc.)
- Domain-specific settings and configurations
- Command-line interface for easy interaction
- Built on Playwright for robust browser automation
- OpenRouter integration for flexible LLM usage
- LangChain integration for advanced AI capabilities

## Requirements

- Python 3.11+

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```
4. Copy `env.example` to `.env` and add your OpenRouter API key

## Usage

1. Start the browser:
   ```bash
   python -m nazare_browser
   ```

2. Enter commands in natural language, for example:
   - "Go to youtube and find videos about Python programming"
   - "Visit ft.com and summarize the top 5 articles"
   - "Search for a product on Amazon and compare prices"

## Configuration

- Domain-specific settings can be configured in `config/domains/`
- Plugins can be enabled/disabled in `config/plugins.yaml`
- Browser settings can be modified in `config/browser.yaml`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is not for commercial use. All rights reserved.

NazareAI is not responsible for any damage caused by this software. Use at your own risk.
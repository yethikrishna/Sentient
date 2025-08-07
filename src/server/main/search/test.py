import asyncio
import json
import os
import sys

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

# --- Setup ---
# Add the project root to the Python path to allow imports from 'main'
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

# Load environment variables from the main .env file
dotenv_path = os.path.join(project_root, ".env")
if not os.path.exists(dotenv_path):
    print(f"ERROR: .env file not found at {dotenv_path}")
    print("Please create a .env file in the 'src/server' directory with MAIN_SERVER_URL and SELF_HOST_AUTH_SECRET.")
    sys.exit(1)

load_dotenv(dotenv_path=dotenv_path)

# --- Configuration ---
SERVER_URL = os.getenv("MAIN_SERVER_URL", "http://localhost:5000")
# Use the self-host secret for simple, direct authentication in testing
AUTH_TOKEN = os.getenv("SELF_HOST_AUTH_SECRET")
SEARCH_ENDPOINT = f"{SERVER_URL}/api/search/unified"

console = Console()

if not AUTH_TOKEN:
    console.print("[bold red]ERROR: SELF_HOST_AUTH_SECRET is not set in your .env file.[/bold red]")
    console.print("Please add it to 'src/server/.env' to run this test script.")
    sys.exit(1)

def print_agent_step(event: dict):
    """Prints a formatted representation of a single step from the agent's process."""
    event_type = event.get("type")
    
    if event_type == "agent_step":
        message = event.get("message", {})
        role = message.get("role")
        content = message.get("content")

        if role == "assistant" and isinstance(content, str) and content.strip():
            console.print(Panel(
                Markdown(content),
                title="[bold yellow]:thought_balloon: Agent Thought[/bold yellow]",
                border_style="yellow",
                expand=False
            ))
        elif role == "assistant" and message.get("function_call"):
            fc = message["function_call"]
            try:
                args = json.dumps(json.loads(fc.get("arguments", "{}")), indent=2)
            except json.JSONDecodeError:
                args = fc.get("arguments", "")
            
            syntax = Syntax(args, "json", theme="monokai", line_numbers=True)
            console.print(Panel(
                syntax,
                title=f"[bold cyan]:hammer_and_wrench: Tool Call: {fc.get('name')}[/bold cyan]",
                border_style="cyan",
                expand=False
            ))
        elif role == "function":
            try:
                result_content = json.dumps(json.loads(content), indent=2)
            except (json.JSONDecodeError, TypeError):
                result_content = str(content)
            
            syntax = Syntax(result_content, "json", theme="monokai", line_numbers=True)
            console.print(Panel(
                syntax,
                title=f"[bold green]:arrow_left: Tool Result: {message.get('name')}[/bold green]",
                border_style="green",
                expand=False
            ))

async def run_search(query: str):
    """Connects to the streaming endpoint and prints the agent's process and final report."""
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    payload = {"query": query}
    
    console.print(f"\n[bold blue]Sending query:[/bold blue] '{query}' to {SEARCH_ENDPOINT}")
    console.print("-" * 50)

    final_report = "No final report was generated."
    buffer = ""

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", SEARCH_ENDPOINT, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    console.print(f"[bold red]Error: Received status code {response.status_code}[/bold red]")
                    error_text = await response.aread()
                    console.print(f"Response: {error_text.decode()}")
                    return

                async for chunk in response.aiter_bytes():
                    buffer += chunk.decode('utf-8')
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            try:
                                event = json.loads(line)
                                if event.get("type") == "done":
                                    final_report = event.get("final_report", "Report was empty.")
                                else:
                                    print_agent_step(event)
                            except json.JSONDecodeError:
                                console.print(f"[dim red]Could not decode JSON line: {line}[/dim red]")

    except httpx.ConnectError as e:
        console.print(f"[bold red]Connection Error: Could not connect to the server at {SERVER_URL}. Is it running?[/bold red]")
        console.print(f"Details: {e}")
        return
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
        return

    console.print("\n" + "=" * 20 + " [bold magenta]FINAL REPORT[/bold magenta] " + "=" * 20)
    console.print(Panel(
        Markdown(final_report),
        title="[bold magenta]Comprehensive Search Summary[/bold magenta]",
        border_style="magenta",
        expand=True
    ))
    console.print("=" * 55)


async def main():
    """Main function to run the interactive test client."""
    console.print("[bold green]Unified Search Agent Test Client[/bold green]")
    console.print("Enter your search query below. Type 'quit' or 'exit' to stop.")
    
    while True:
        try:
            query = console.input("[bold cyan]Query> [/bold cyan]")
            if query.lower() in ["quit", "exit"]:
                break
            if not query.strip():
                continue
            
            await run_search(query)

        except KeyboardInterrupt:
            break
    
    console.print("\n[bold yellow]Exiting test client. Goodbye![/bold yellow]")

if __name__ == "__main__":
    asyncio.run(main())
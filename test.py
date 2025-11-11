from rich.console import Console
from rich.text import Text
from rich.tree import Tree
from rich.live import Live
import time

cmd_branch = "├─"
cmd_end = "└─"
cmd_pipe = "│"

def process_text(msg):
    lines = msg.split('\n')
    formatted = f'\n{cmd_pipe}  '.join(lines)
    formatted = f"{cmd_pipe}  {formatted}"
    return formatted
console = Console()
user_name = "Cooper"
message = """This is not happening.
But It is."""
formatted = f"[cyan]{user_name}[/cyan]\n {message}"
console.print(formatted, justify='right')
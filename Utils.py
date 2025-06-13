
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt

DEBUG = True
console = Console()

def tw_print(x):
    #print(x)
    console.print(Markdown(x))

def dprint(x):
    if DEBUG:
        print(x)

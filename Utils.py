from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from pprint import pprint

DEBUG = True
# DEBUG_LOGFILE = None  # z. B. "debug.log"
DEBUG_LOGFILE = "debug.log"
console = Console()

def tw_print(x):
    console.print(Markdown(x))


def dprint(x):
    if DEBUG:

        if DEBUG_LOGFILE:
            with open(DEBUG_LOGFILE, "a", encoding="utf-8") as f:
                f.write(str(x) + "\n")
        else:
            print(x)


def dpprint(x):
    if DEBUG:

        if DEBUG_LOGFILE:
            with open(DEBUG_LOGFILE, "a", encoding="utf-8") as f:
                from pprint import pformat
                f.write(pformat(x) + "\n")
        else:
            pprint(x)
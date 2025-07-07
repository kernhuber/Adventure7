from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from pprint import pprint
import datetime
DEBUG = True
ADV_LOGGER = None

class dlogger():


    def __init__(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.logfile =f"debug-{timestamp}.log"

    def dprint(self,x):
        if DEBUG:

            if self.logfile:
                with open(self.logfile, "a", encoding="utf-8") as f:
                    f.write(str(x) + "\n")
            else:
                print(x)

    def dpprint(self,x):
        if DEBUG:

            if self.logfile:
                with open(self.logfile, "a", encoding="utf-8") as f:
                    from pprint import pformat
                    f.write(pformat(x) + "\n")
            else:
                pprint(x)


console = Console()

def tw_print(x):
    console.print(Markdown(x))


def dprint(x):
    if ADV_LOGGER:
        ADV_LOGGER.dprint(x)


def dpprint(x):
    if ADV_LOGGER:
        ADV_LOGGER.dpprint(x)
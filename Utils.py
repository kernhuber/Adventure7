from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from pprint import pprint
import datetime
from enum import IntFlag, auto

class dl(IntFlag):
    GAMELOOP        = auto()
    GAMESTATE       = auto()
    PLAYERSTATE     = auto()
    NPCPLAYERSTATE  = auto()
    LLM             = auto()
    LLM_PROMPT      = auto()
    EXPLOSIONSTATE  = auto()
    SYSTEST         = auto()

DEBUG = True
DEBUG_LEVEL = dl.LLM|dl.LLM_PROMPT|dl.NPCPLAYERSTATE|dl.PLAYERSTATE|dl.GAMELOOP|dl.GAMESTATE|dl.SYSTEST
ADV_LOGGER = None

class dlogger():


    def __init__(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.logfile =f"debug-{timestamp}.log"

    def dprint(self,l:dl, x):
        if DEBUG and (l & DEBUG_LEVEL):

            if self.logfile:
                with open(self.logfile, "a", encoding="utf-8") as f:
                    f.write(str(x) + "\n")
            else:
                print(x)

    def dpprint(self,l:dl,x):
        if DEBUG and (l & DEBUG_LEVEL):

            if self.logfile:
                with open(self.logfile, "a", encoding="utf-8") as f:
                    from pprint import pformat
                    f.write(pformat(x) + "\n")
            else:
                pprint(x)


console = Console()

def tw_print(x):
    console.print(Markdown(x))


def dprint(l:dl, x):
    if ADV_LOGGER:
        ADV_LOGGER.dprint(l,x)


def dpprint(l:dl, x):
    if ADV_LOGGER:
        ADV_LOGGER.dpprint(l, x)
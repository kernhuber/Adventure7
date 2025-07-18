from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from pprint import pprint
import datetime
from enum import IntFlag, auto

class dl(IntFlag):
    GAMELOOP        = auto()  # Messages from the game loop
    GAMESTATE       = auto() # Game State (engine)
    PLAYERSTATE     = auto() # Player debug messages
    NPCPLAYERSTATE  = auto() # Dog NPC
    LLM             = auto() # Gemini-Interface
    LLM_PROMPT      = auto() # Prompting
    EXPLOSIONSTATE  = auto() # test messages from the explosion NPC
    SYSTEST         = auto() # test game engine with atomic messages
    SYSTESTLLM      = auto() # test game with actual sentences

DEBUG = True
DEBUG_LEVEL = dl.LLM|dl.LLM_PROMPT|dl.NPCPLAYERSTATE|dl.PLAYERSTATE|dl.GAMELOOP|dl.GAMESTATE|dl.SYSTESTLLM
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
                    f.write(pformat(x,indent=5) + "\n")
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
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from pprint import pprint
import datetime
from enum import IntFlag, auto

import difflib
import inspect

#
# Debugging and logging
#
class dl(IntFlag):
    GAMELOOP        = auto()  # Messages from the game loop
    GAMESTATE       = auto() # Game State (engine)
    PLAYERSTATE     = auto() # Player debug messages
    NPCPLAYERSTATE  = auto() # Dog NPC
    LLM             = auto() # Gemini-Interface
    LLM_PROMPT      = auto() # Prompting
    LLM_TOKENS      = auto() # Token usage
    EXPLOSIONSTATE  = auto() # test messages from the explosion NPC
    SYSTEST         = auto() # test game engine with atomic messages
    SYSTESTLLM      = auto() # test game with actual sentences
    WEBGUI          = auto() # WebGUI debugging
    CMDLOG          = auto() # Testing of json_cmd-Function below
    ZOMBIE          = auto() # General testing of Zombie NPC

GHOSTMODE = False   # No obstacles, no hidden ways, no NPCs
NODOG = False # No dog NPC
DEBUG = True
# DEBUG_LEVEL = dl.LLM|dl.NPCPLAYERSTATE|dl.PLAYERSTATE|dl.GAMELOOP|dl.GAMESTATE|dl.WEBGUI|dl.CMDLOG|dl.ZOMBIE
DEBUG_LEVEL = dl.ZOMBIE|dl.LLM_TOKENS|dl.LLM|dl.LLM_PROMPT|dl.WEBGUI|dl.CMDLOG|dl.NPCPLAYERSTATE
ADV_LOGGER = None

class dlogger():


    def __init__(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.logfile =f"debug-{timestamp}.log"

    def dprint(self,l:dl, x):
        if DEBUG and (l & DEBUG_LEVEL):
            lvl = l.name or str(l)   # z.B. "WEBGUI" (bei kombinierten Flags "A|B")
            if self.logfile:
                with open(self.logfile, "a", encoding="utf-8") as f:
                    f.write(f"{lvl}: " + str(x) + "\n")
            else:
                print(f"{lvl}: {x}")

    def dpprint(self,l:dl,x):
        if DEBUG and (l & DEBUG_LEVEL):
            lvl = l.name or str(l)
            if self.logfile:
                with open(self.logfile, "a", encoding="utf-8") as f:
                    from pprint import pformat
                    f.write(f"{lvl}: " + pformat(x,indent=5) + "\n")
            else:
                print(f"{lvl}:")
                pprint(x)

    def ddiff(self,l:dl,a,b):
        if DEBUG and (l & DEBUG_LEVEL):
            if self.logfile:
                with open(self.logfile, "a", encoding="utf-8") as f:
                    from pprint import pformat
                    f.write("************* Difference between texts:\n")
                    lines1 = a.splitlines(keepends=True)
                    lines2 = b.splitlines(keepends=True)
                    diff = difflib.unified_diff(
                        lines1,
                        lines2,
                        fromfile=f'Version {a}',
                        tofile=f'Version {b}'
                    )
                    for l in diff:
                        f.write(f"{l}\n")
            else:
                pprint(f"text A: \n {a}\n {'#'*30}\n\nText B: \n{b}")


console = Console()

def tw_print(x):
    console.print(Markdown(x))


def dprint(l:dl, x):
    if ADV_LOGGER:
        ADV_LOGGER.dprint(l,x)


def dpprint(l:dl, x):
    if ADV_LOGGER:
        ADV_LOGGER.dpprint(l, x)

def ddiff(l:dl, a, b):
    if ADV_LOGGER:
        ADV_LOGGER.ddiff(l,a,b)

game_known_tokens = ["anwenden",
                    "interagiere",
                    "nimm",
                    "ablegen",
                    "untersuche",
                    "umsehen",
                    "hilfe",
                    "gehe",
                    "llm",
                    "toeten",
                    "angreifen",
                    "inventory",
                    "context",
                    "dogstate",
                    "quit",
                    "nichts",
                    "interaktion",
                    "zurueckweisen",
                    "zurückweisen",
                    "unbekannt",
                    "toggle_layout",
                    "minigame",
                    "gameover",
                    "player_message",
                    "dog_message",
                    "explosion_message",
                    "do_explosion",
                    "check_pinpad",
                    "zombie_message",
                    "zombie_bite",
                    "zombie_event"]
#
# Translate "String"-style commands to JSON
#
# ({'function_call': {'name': ui, 'args': {}}})





#
# Return commands in the same way the LLM does return them via function call:
#

def json_cmd_simple(cmd_in:str, arg1:str=None, arg2:str=None):
    # capture and log callsite (file:line in function), helps trace where JSON commands are created
    try:
        frm = inspect.stack()[1]
        caller_file = frm.filename
        caller_func = frm.function
        caller_line = frm.lineno
        caller_info = f"{caller_file}:{caller_line} in {caller_func}()"
    except Exception:
        caller_info = "unknown"
    dprint(dl.CMDLOG, f"[json_cmd_simple] caller={caller_info} cmd={cmd_in}, {arg1 if arg1 else ''}, {arg2 if arg2 else ''}")



    if cmd_in in game_known_tokens:
        match cmd_in:
            case "anwenden":
                args = {
                    "what":arg1,
                    "towhat":arg2 if arg2 else None,
                }
            case "interagiere":
                args = {
                    "who":arg1,
                    "firstmessage":arg2 if arg2 else "",
                }
            case "nimm":
                args = {
                    "whato":arg1
                }
            case "ablegen":
                args = {
                    "whato":arg1
                }
            case "untersuche":
                args = {
                    "what":arg1
                }
            case "umsehen":
                args = {}
            case "hilfe":
                args = {}
            case "gehe":
                args = {
                    "direction":arg1
                }
            case "llm":
                args = {}
            case "toeten":
                args = {
                    "whom":arg1
                }
            case "angreifen":
                args = {
                    "whom":arg1,
                }
            case "inventory":
                args = {}
            case "context":
                args = {}
            case "dogstate":
                args = {}
            case "quit":
                args = {}
            case "nichts":
                args = {}
            case "interaktion":
                args = {
                    "who":arg1,
                    "firstmessage":arg2 if arg2 else None,
                }
            case "zurueckweisen":
                args = {
                    "why":arg1
                }
            case "zurückweisen":
                args = {
                    "why": arg1
                }

            case "unbekannt":
                args = {}

            case "toggle_layout":
                args = {}

            case "minigame":
                args = {}
                if arg1:
                    args["whichgame"] = arg1

            case "gameover":
                args = {}
                if arg1:
                    args["message"] = arg1

            case "player_message":
                args = {
                    "message": arg1
                }

            case "dog_message":
                args = {
                    "message": arg1
                }

            case "explosion_message":
                args = {
                    "message": arg1
                }

            case "do_explosion":
                args = {
                    "message": arg1
                }

            case "check_pinpad":
                args = {
                    "hash":arg1
                }

            case "zombie_message":
                args = {
                    "message": arg1
                }

            case "zombie_bite":
                args = {
                    "message": arg1
                }

            case "zombie_event":
                args = {
                    "message": arg1
                }

        cmd_struct = {
            "function_call":{
                "name":cmd_in,
                "args":args
            }
        }
    else:
        cmd_struct = {
            "function_call":{
                "name":"message",
                "args":{
                    "message":cmd_in
                }
            }
        }
    dprint(dl.CMDLOG,"Resulting CMD structure:")
    dpprint(dl.CMDLOG,cmd_struct)
    return cmd_struct



def return_do_nothing():
    return json_cmd_simple("nichts")
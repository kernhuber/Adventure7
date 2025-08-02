from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from pprint import pprint
import datetime
from enum import IntFlag, auto
import difflib

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
    EXPLOSIONSTATE  = auto() # test messages from the explosion NPC
    SYSTEST         = auto() # test game engine with atomic messages
    SYSTESTLLM      = auto() # test game with actual sentences
    WEBGUI          = auto() # WebGUI debugging
    CMDLOG          = auto() # Testin of json_cmd-Function below

DEBUG = True
DEBUG_LEVEL = dl.LLM|dl.NPCPLAYERSTATE|dl.PLAYERSTATE|dl.GAMELOOP|dl.GAMESTATE|dl.WEBGUI|dl.CMDLOG
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

#
# Translate "String"-style commands to JSON
#
# ({'function_call': {'name': ui, 'args': {}}})

def json_cmd(cmd_in:str):
    dprint(dl.CMDLOG,f"json_cmd: {cmd_in}")

    # tokens = input.split()
    import regex as re
    tokens = re.findall(r'#[^#]*#|[\p{L}_][\p{L}\p{N}_-]*[\p{L}\p{N}_]', cmd_in)
    #
    # Jetzt noch Anführungszeichen bzz "#" entfernen falls nötig ("#" als Substitute für Anführungszeihen)
    #
    tokens = [t[1:-1] if t.startswith('#') else t for t in tokens]
    if tokens[0] in ["anwenden","nimm","ablegen","untersuche","umsehen","hilfe","gehe","llm","toeten","angreifen","inventory","context","dogstate","quit","nichts","interaktion","zurueckweisen","zurückweisen","unbekannt","toggle_layout"]:
        match tokens[0]:
            case "anwenden":
                args = {
                    "what":tokens[1],
                    "towhat":tokens[2] if tokens[2] else None,
                }

            case "nimm":
                args = {
                    "whato":tokens[1]
                }
            case "ablegen":
                args = {
                    "whato":tokens[1]
                }
            case "untersuche":
                args = {
                    "what":tokens[1]
                }
            case "umsehen":
                args = {}
            case "hilfe":
                args = {}
            case "gehe":
                args = {
                    "direction":tokens[1]
                }
            case "llm":
                args = {}
            case "toeten":
                args = {
                    "whom":tokens[1]
                }
            case "angreifen":
                args = {
                    "whom":tokens[1],
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
                    "whom":tokens[1],
                    "what":tokens[2] if tokens[2] else None,
                }
            case "zurueckweisen":
                args = {
                    "why":tokens[1]
                }
            case "zurückweisen":
                args = {
                    "why": tokens[1]
                }

            case "unbekannt":
                args = {}
            case "toggle_layout":
                args = {}


        cmd_struct = {
            "function_call":{
                "name":tokens[0],
                "args":args
            }
        }
    else:
        cmd_struct = {
            "function_call":{
                "name":"gen_message",
                "args":{
                    "message":cmd_in
                }
            }
        }
    dprint(dl.CMDLOG,"Resulting CMD structure:")
    dpprint(dl.CMDLOG,cmd_struct)
    return cmd_in


def return_do_nothing():
    return "nichts"
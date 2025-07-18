#from Adventure6 import places, state, items, gehe, nimm, untersuche, anwenden, umsehen, inventory
# from Door import Door
# from InteractLLM import PromptGenerator
#

from collections import deque

import Utils


class SysTest:
    def __init__(self):

        #
        # For testing purposes rename any of the following to "test_queue"
        #


        self.test_queue_cheese = deque([
            "gehe schuppen",
            "untersuche blumentopf",
            "anwenden schlüssel schuppen",
            "gehe innen",
            "nimm sprengladung",
            "gehe schuppen",
            "gehe warenautomat",
            "anwenden sprengladung warenautomat",
            #"ablegen sprengladung",
            "gehe schuppen",
            "nichts"
        ])
        self.test_queue_llm = deque([
            "gehe zum schuppen",
            "schau dich um",
            "untersuche den blumentopf",
            "schließe mit dem schlüssel den Schuppen auf und gehe hinein",
         #   "gehe innen",
            "sieh dich um",
            "nimm die sprengladung und verlasse den schuppen",
         #   "gehe schuppen",
            "gehe zum felsen",
            "sieh dich um",
            "aktiviere die Sprengladung und lege sie am Felsen ab",
          #  "ablegen sprengladung",
            "gehe zum schuppen",
            "gehe nach innen und sieh dich um",
            "untersuche das skelett",
            "untersuche die geldboerse",
            "nimm die ec-karte und die Leiter",
           # "nimm leiter",
            "verlasse den schuppen",
           # "umsehen",
            "lehne die Leiter an den Schuppen",
          # "anwenden leiter schuppen",
            "gehe zum felsen und sieh dich um",
            "gehe in die höhle und schau dich um",
          #  "umschauen",
            "betätige den hauptschalter und verlasse die höhle",
           # "gehe felsen",
            "gehe zum schuppen und steige auf das dach",
           # "gehe dach",
            "umsehen",
            "betätige den Hebel",
            "springe vom schuppen",
            "gehe zum warenautomat",
           # "gehe warenautomat",
            "gehe zum u-bahnhof",
            "trinke vom wasserspender",
            "untersuche den mülleimer",
            "nimm den Zettzel mit der geheimzahl",
            "gehe wieder an die Oberfläche",
            "nichts",
            "nichts",
            "gehe zur u-bahn",
            "trinke vom Wasserspender",
            "nichts",
            "gehe in den wagen",
            "nichts",
            "nichts",
            "verlasse den Wagen",
            "Gehe wieder an die Oberfläche",
            "gehe zum geldautomat",
            "inventory",
            "Stecke die Geldkarte in den Geldautomaten",
            "nimm die us-dollar",
            "gehe zum warenautomat",
            "gehe in die ubahn",
            "nichts",
            "nichts",
            "gehe wieder nach oben",
            "nichts",
            "nichts",
            "gehe zur ubahn",
            "gehe gehe in den wagen und betätige den türschließer",
            # "anwenden türschließer",
            "umsehen",
            "gehe auf den bahnsteig",
            "umsehen",
            "untersuche den pizzaautomaten",
            "wirf die US-Dollar in den Pizzaautomaten",
            "nimm die lire und die pizza",
            "gehe in den wagen und betätige den türschließer",
            "verlasse den wagen",
            "trinke vom wasserspender",
            "gehe an die oberfläche",
            "gehe zum schuppen und lege die pizza ab",
            "steige auf den schuppen",
            "betätige den hebel",
            "springe vom schuppen",
            "gehe zum warenautomaten",
            "wirf die lire in den warenautomat",
            "nimm die fahrradkette und gehe zum start",
            "baue die fahrradkette in das fahrrad ein",

        ])





    def test_game_llm(self) -> str:
        from Utils import dprint, dl
        if self.test_queue_llm:
            c = self.test_queue_llm.popleft()
            dprint (dl.PLAYERSTATE, 'Player: {c}')
            print(f"Spieler: {c}")
            return c
        else:
            return None



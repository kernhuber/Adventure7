#from Adventure6 import places, state, items, gehe, nimm, untersuche, anwenden, umsehen, inventory
# from Door import Door
# from InteractLLM import PromptGenerator
#

from collections import deque

class SysTest:
    def __init__(self):
        self.test_queue = deque([])

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
        self.test_queue_long = deque([
            # "gehe geldautomat",
            #
            # Hundekampf provozieren
            #
            # "nichts",
            # "nichts",
            # "nichts",
            # "nichts",
            # "nichts",
            # "nichts",
            # "nichts",
            "gehe p_schuppen",
            "umsehen",
            "untersuche Blumentopf",
            "anwenden Schlüssel Schuppen",
            "gehe p_innen",
            "umsehen",
            "nimm sprengladung",
            "gehe p_schuppen",
            "gehe felsen",
            "umsehen",
            "anwenden sprengladung",
            "ablegen sprengladung",
            "gehe p_schuppen",
            "gehe p_innen",
            "nichts",
            "gehe p_schuppen",
            "gehe p_felsen",
            "umsehen",
            "gehe höhle",
            "umsehen",
            "anwenden breaker",
            "gehe felsen",
            "gehe p_schuppen",
            "gehe p_innen",
            "untersuche o_skelett",
            "untersuche o_geldboerse",
            "nimm o_ec_karte",
            "nimm o_leiter",
            "gehe p_schuppen",
            "anwenden o_leiter o_schuppen",
            "gehe p_dach",
            "umsehen",
            "anwenden o_hebel",
            "gehe p_schuppen",
            "anwenden o_ec_karte o_blumentopf",
            "gehe p_geldautomat",
            # "anwenden o_ec_karte o_geldautomat",
            "gehe p_warenautomat",
            "umsehen",
            "gehe p_ubahn",
            "umsehen",
            "untersuche o_muelleimer",
            "untersuche o_geheimzahl",
            "nimm o_geheimzahl",
            "gehe p_warenautomat",
            "gehe p_geldautomat",
            "untersuche o_geheimzahl",
            "anwenden o_ec_karte o_geldautomat",
            "gehe p_warenautomat",
            "gehe p_ubahn",
            "gehe p_wagen",
            "umsehen",
            "nimm o_salami",
            "gehe p_ubahn",
            "gehe p_warenautomat",
            "gehe p_schuppen",
            "ablegen o_salami",
            "umsehen",
            "gehe p_innen",
            "nichts",
            "nichts",
            "gehe p_schuppen",
            "gehe p_geldautomat",
            "nimm o_geld_dollar",
            "gehe p_warenautomat",
            "anwenden o_geld_dollar o_warenautomat",
            "gehe p_schuppen",
            "nichts",
            "nichts",
            "nichts",
            "gehe p_dach",
            "anwenden o_hebel",
            "gehe p_schuppen",
            "gehe p_warenautomat",
            "umsehen",
            "anwenden o_geld_dollar o_warenautomat",
            "untersuche o_warenautomat",
            "nichts",
            "gehe schuppen",
            "gehe dach",
            "anwenden hebel",
            "gehe schuppen",
            "gehe warenautomat",
            "gehe u-bahn",
            "gehe wagen",
            "umsehen",
            "anwenden turschliesser",
            "gehe p_ubahn2",
            "umsehen",
            "anwenden o_geld_dollar o_pizzaautomat",
            "umsehen",
            "nimm pizza",
            "nimm lire",
            "gehe wagen",
            "anwenden tuerschliesser",
            "gehe ubahn",
            "gehe warenautomat",
            "anwenden lire warenautomat",
            "gehe schuppen",
            "gehe dach",
            "anwenden hebel",
            "gehe schuppen",
            "gehe warenautomat",
            "nichts"

        ])

    def test_game(self) -> str:
        if self.test_queue:
            c = self.test_queue.popleft()
            print (f'Player: {c}')
            return c
        else:
            return None





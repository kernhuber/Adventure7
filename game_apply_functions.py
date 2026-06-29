""" This module contains all the game verbs as well as a super simple parser and execution mechanism"""
#import pylab as p

from game_state import GameState
from game_object import GameObject
from player_state import PlayerState
from npc_dog_state import NPCDogState
from explosion_state import ExplosionState
from place import Place

from way import Way

# Helper: get the structured flags container from GameState.
def _F(gs: GameState):
    """Return the structured flags container (GameFlags) from GameState."""
    return gs.get_flags()

def o_schluessel_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    #
    # Ich bin der Schlüssel - einzig sinnvolle Applikation: Schuppen
    #
    if pl != None:
        #
        # Haben wir den SChlüssel dabei oder liegt er am aktuellen Ort? --> Anwenden
        #
        loc = pl.location
        if loc != gs.places["p_schuppen"]:
            return "Das ergibt hier keinen Sinn."
        if pl.is_in_inventory(what) or (what in pl.location.place_objects) and (onwhat == gs.objects["o_schuppen"]):
            gs.schuppentuer = True
            return "Klick - die Tür geht auf"

        else:
            return "Das geht hier nicht: "
    else:
        return "... kein Spieler? Wie soll das gehen?"

def o_umschlag_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Hiermit solltest du kein Schindluder treiben!"

def o_warenautomat_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Wie willst du bitte einen Warenautomat auf etwas anwenden? Hast du Superkräfte? Nein!"

def o_muelleimer_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Was soll ich mit dem Mülleimer tun?"

def o_salami_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Das verstehe ich nicht - was soll ich mit der Salami tun?"

def o_geheimzahl_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Ich glaube, du meinst etwas anderes - die Geheimzahl kann ich nicht anwenden!"

def o_tuerschliesser_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    if pl.location != gs.places["p_wagen"]:
        return "Hier ist kein Türschließer"

    if _F(gs).wagen_ubahn2:
        _F(gs).wagen_ubahn2 = False
        gs.ways["w_wagen_ubahn"].visible = True
        gs.ways["w_wagen_ubahn2"].visible = False
        gs.ways["w_ubahn_wagen"].visible = True
        gs.ways["w_ubahn2_wagen"].visible = False
        return "Die Tür schließt sich. Der Wagen setzt sich in Bewegung, und fährt zurück zum ersten Bahnsteig. Die Tür öffnet sich wieder."
    else:
        _F(gs).wagen_ubahn2 = True
        gs.ways["w_wagen_ubahn"].visible = False
        gs.ways["w_wagen_ubahn2"].visible = True
        gs.ways["w_ubahn_wagen"].visible = False
        gs.ways["w_ubahn2_wagen"].visible = True
        return "Die Tür schließt sich. Der Wagen setzt sich in Bewegung, und hält nach kurzer Fahrt an einem zweiten Bahnsteig. Die Tür öffnet sich wieder."

def o_pizzaautomat_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Wie soll ich den Pizza-Automaten an sich anwenden? Ich verstehe nicht, was du meinst!"

def o_geld_lire_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    if pl.location.name == "p_warenautomat" and onwhat.name == "o_warenautomat":
        if not pl.is_in_inventory(gs.objects["o_umschlag"]):
            return "Es wäre alles so schön - leider fällt dir auf, dass du den wichtigen Briefumschlag irgendwo verlegt hast. Finde ihn erst!"
        if not _F(gs).hebel:
            if not _F(gs).hauptschalter:
                return "Eigentlich sollte dies gar nicht passieren können - aber der Automat hat keinen Strom!"
            if gs.objects["o_fahrradkette"].hidden:
                gs.objects["o_fahrradkette"].hidden = False
                return """Du wirfst die italienischen Lira in den Warenautomat - und er akzeptiert sie ohne zu murren.
Du erwirbst eine Fahrradkette, die nun im Ausgabeschacht liegt!"""
            else:
                return "Die Fahrradkette hast Du ja schon aus dem Automaten geholt - eine zweite ist leider nicht darin!"
        else:
            return "Der Automat liegt auf dem Rücken - da kann man gar nichts einwerfen!"
    else:
        return "Das geht hier nicht!"

def o_pizza_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Was soll ich genau mit der Pizza machen?"

def o_geldautomat_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Wie soll ich bitte einen Geldautomaten auf etwas anwenden?"

def o_geld_dollar_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    #
    # Ich bin das Dollar-Bündel - mich kann man auf den Warenautomaten und auf den Pizza-Automaten anwenden, wenn
    # der Raum stimmt
    #

    if pl.location.name == "p_warenautomat" and onwhat.name=="o_warenautomat":
        if _F(gs).hebel:
            return 'Der Warenautomat liegt auf dem Bauch. Er ist zwar völlig intakt, und nicht zerbrochen, aber da kann man kein Geld einwerfen!'
        else:
            if not _F(gs).hauptschalter:
                return "Der Automat ist ausgeschaltet"
            else:
                return 'Der Automat zeigt an: "Mi dispiace molto, ma in questa macchina si accettano solo lire italiane.". Er will also italienische Lira haben - aber wo bekomme ich die her?'

    if pl.location.name == "p_ubahn2" and onwhat.name=="o_pizzaautomat":
        #
        # Wenn der Hund in einem früheren Spielschritt die Pizza gegessen hat, mache eine neue
        #
        if gs.objects.get("o_pizza"):
            gs.objects["o_pizza"].hidden = False
        else:
            gs.objects["o_pizza"] = GameObject("o_pizza","Eine schöne, frisch gemachte Pizza","",False,None)
            gs.objects["o_pizza"].hidden = False
            gs.objects["o_pizza"].ownedby = gs.places["p_ubahn2"]
        gs.objects["o_geld_lire"].hidden = False
        return 'Es dauert, und der Automat bereitet eine wunderschöne Pizza für dich zu, die Du im Ausgabefach findest. Und dann klappert es - es wird Dir Wechselgeld ausgezahlt, **und zwar in italienischen Lira!**'
    return "Du scheinst mit den Dollars hier wenig anfangen zu können..."

def o_schuppen_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Wie willst du einen Schuppen auf etwas anwenden? Das geht nicht!"

def o_blumentopf_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Interessanter Ansatz ... geht aber nicht."

def o_stuhl_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Du setzt dich auf den Stuhl...  oder was meinst du?"

def o_schrott_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Den Schrott anwenden? Das ergibt nun wirklich keinen Sinn!"

def o_hebel_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    #
    # Ich bin der Hebel - ich kann nicht auf "irgendwas" angewandt werden, ich kann nur selber
    # angewandt werden.
    #
    if not _F(gs).hauptschalter:
        return "Du ruckelst am Hebel, aber nichts passiert"
    if pl != None:
        if pl.location == gs.places["p_dach"]:
            if _F(gs).hebel:
                gs.hebel = False
                gs.ways["w_warenautomat_ubahn"].visible = False
                gs.ways["w_ubahn_warenautomat"].visible = False
                gs.places["p_warenautomat"].description = "Hier steht ein Warenautomat, an dem man Fahrradteile kaufen kann."
                gs.objects["o_warenautomat"].examine = "Ein Warenautomat mit Fahrradteilen. Er enthält tatsächlich auch eine Fahrradkette! Jetzt bräuchte man Geld - und zwar italienische Lira. Dieser Automat akzeptiert nur diese!"
                return "Es rumpelt - und der Warenautomat richtet sich wieder auf!"
            else:
                gs.hebel = True
                gs.ways["w_warenautomat_ubahn"].visible = True
                gs.ways["w_ubahn_warenautomat"].visible = True
                gs.objects["o_warenautomat"].examine = "Ein Warenautomat, der auf dem Rücken liegt. Da wo er stand, führt eine Treppe nach unten!"
                gs.places["p_warenautomat"].description = "Hier liegt ein Warenautomat auf dem Rücken. Da wo er wohl gestanden hat, ist eine Öffnung im Boden. Man sieht darin eine Treppe - es geht zu einer U-Bahn-Station!"
                return "Es rumpelt - Die siehst, wie der Warenautomat sich langsam auf den Rücken legt. Da wo er stand, ist nun eine Öffnung - und darin eine Treppe zu einer U-Bahn-Station!"
        else:
            return "Hier ist kein Hebel!"
    else:
        return "??? Kein Spieler ???"

from game_state import GameState
from player_state import PlayerState
def o_sprengladung_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    from explosion_state import ExplosionState

    xpl = ExplosionState(gs, location=pl.location)
    xpl.name = "Explosion"
    gs.players.append(xpl)
    rval=""
    if onwhat != None:
        #
        # Wenn die Sprengladung auf einen Gegenstand angewandt wird, der am selben Ort ist wie der Spieler,
        # wird sie hier am Ort abgelegt. Sonst bleibt sie im Inventory des Spielers und sprengt ihn bald
        # in die Luft!
        #
        l = []
        for i in pl.location.place_objects:
            l.append(i.name)
            for j in i.callnames:
                l.append(j)
        if onwhat.name in l:
            gs.verb_drop(pl, None, "o_sprengladung")
            rval = "Du legst die Sprengladung hier ab. "
    return rval+"Die Sprengladung ist nun scharf gemacht!"

def o_felsen_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Wie willst Du denn den Felsen auf IRGENDWAS anwenden? Du hast keine Superkräfte!"

def o_hauptschalter_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    if gs.hauptschalter:
        return "Du hast den Schalter bereits betätigt - alles hat Strom"
    else:
        gs.hauptschalter = True
        return "Du betätigst den Schalter. Irgendwo läuft ein Generator an - du hörst elektrisches Summen... Strom!"

def o_leiter_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    #
    # Ich bin die Leiter - einzig sinnvolle Applikation: an den Schuppen anlehnen
    #
    if pl != None:
        #
        # Haben wir die Leiter dabei?
        #
        if onwhat != None and isinstance(onwhat,PlayerState) and onwhat.name == "hund":
            #
            # Mit der Leiter gegen den Hund
            #
            dog = None
            for d in gs.players:
                if type(d) is NPCDogState:
                    dog=d
                    break
            if d==None:
                return "Kein Hund hier!"
            retour = gs.find_shortest_path(pl.location,gs.places["p_geldautomat"])
            if retour == None:
                return "Du gehst mit der Leiter auf den Hund los - aber er kann nicht an seinen Stammplatz flüchten!"

            dog.growl=0
            dog.next_location = ""
            dog.next_location_wait = 2
            dog.location = gs.places["p_geldautomat"]

            return "Mit einer Leiter gegen einen Hund! Wie unfair! Aber immerhin: der Hund rennt jammernd an seinen Stammplatz, den Geldautomaten."

        loc = pl.location
        if onwhat != gs.objects["o_schuppen"]:
            return "Die Leiter rutscht ab und fällt um. Das mit der Leiter ergibt hier sowieso keinen Sinn."
        if pl.is_in_inventory(what) or (what in pl.location.place_objects):
            gs.leiter = True
            pl.remove_from_inventory(what)
            loc.place_objects.append(what)
            #
            # Weg Sichtbar machen
            #
            gs.ways["w_schuppen_dach"].visible = True

            return "Du kannst jetzt auf den Schuppen steigen!"
        else:
            return "Das geht hier nicht: "
    else:
        return "... kein Spieler? Wie soll das gehen?"

def o_skelett_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Igitt! Das Skelett rühre ich nicht weiter an!"

def o_geldboerse_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Was genau soll ich mit der Geldbörse tun?"

def o_ec_karte_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    if not _F(gs).hauptschalter:
        return "Sieht so aus, als wäre der Automat ausgeschaltet"

    if pl.location.name!="p_geldautomat" and onwhat.name!="o_geldautomat":
        return "Ich verstehe nicht, was genau du mit der Geldkarte machen willst!"
    #
    # Web-Version oder nicht?
    #
    is_web_interface = (hasattr(gs, 'web_sessions') and
                        len(getattr(gs, 'web_sessions', {})) > 0)
    if not is_web_interface:
        print(f"{'*'*60}")
        print(f"*{' '*58}*")
        s=("Bitte geben sie die Geheimzahl ein!").center(58," ")
        print(f'*{s}*')
        print(f"*{' ' * 58}*")
        print(f"{'*' * 60}")
        z = -1
        while z<0:
            x = input("Geheimzahl: ")
            if x.isdigit():
                z = f'{int(x):04d}'
        if gs.geheimzahl == z:
            gs.objects["o_geld_dollar"].hidden = False
            return "**Die Zahl stimmt!** Du tippst die entsprechenden Tasten - der Automat rattert, und spuckt ein Bündel Scheine aus. Frisch gedruckte US-Dollar!"
        else:
            return " --- Die Zahl ist falsch. ---"
    else:
        #
        # Get number from the web interface, have
        #

#----
        # Statt pl.websocket
        session_id = getattr(pl, 'session_id', None)

        if session_id is None:
            return "Fehler beim Zugriff auf Web-Session."
#---
        # Fordere PIN über Web-GUI an → Command-Queue!
        import hashlib
        md = hashlib.md5(_F(gs).geheimzahl.encode()).hexdigest()
        gs.cmd_q.append({
            "function_call": {
                "name": "check_pinpad",
                "args": {
                    "hash": md
                }
            }
        })
        return "Warte auf Eingabe..."


def o_pinsel_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Schlapp, schlapp, schlapp ... Du hast den Pinsel angewandt."

def o_farbeimer_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Den Farbeimer anwenden..."

def o_fahrradkette_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    if pl.location.name == "p_start":
        if onwhat.name != "o_fahrrad":
            return "Ich habe nicht verstanden, was ich mit der Fahrradkette machen soll!"
        if gs.objects.get("o_umschlag",None) is None:
            gs.game_over = True
            gs.game_won = False
            return "Tja - Du hast zwar die Fahrradkette, aber der Briefumschlag ist irgendwann pulverisiert worden. Schade, ***Du verlierst das Spiel!***"
        if gs.objects["o_umschlag"] in pl.inventory:
            gs.game_over = True
            gs.game_won = True
            if _F(gs).zombie_cooperative:
                return (
                    "Du reparierst Dein Fahrrad mit der neuen Kette. "
                    "Bevor du losfährst, hältst du inne. Der Zombie - Harald Kronstein - "
                    "hat seinen Frieden gefunden. Seine Erlösung hat auch dir den Weg frei gemacht. "
                    "Du schwingst dich auf dein Fahrrad und schaffst es rechtzeitig, "
                    "den Briefumschlag abzugeben. "
                    "***Du bist ein wahrer Held! Du hast nicht nur die Welt gerettet, "
                    "sondern auch eine verlorene Seele erlöst! Du gewinnst das Spiel!***"
                )
            else:
                return (
                    "Du reparierst Dein Fahrrad und schaffst es rechtzeitig, "
                    "den Briefumschlag abzugeben. ***Du gewinnst das Spiel!*** "
                    "Allerdings... irgendwo in der Tiefe der Anlage irrt noch immer "
                    "ein untoter Geschäftsmann umher, gefangen zwischen Leben und Tod. "
                    "Du hättest ihm helfen können. Ein bitterer Beigeschmack bleibt."
                )
        else:
            return "Das wäre schön - aber wo hast du den Briefumschlag abgelegt? Den brauchst Du..."
    else:
        return "Wie soll das gehen?"

def _refill_flasche(gs: GameState) -> str:
    """Fülle die Flasche am Wasserspender auf (beliebig oft, aber immer nur eine
    Flaschenfüllung als Notreserve)."""
    if gs.flasche_voll:
        return "Die Flasche ist bereits randvoll."
    gs.flasche_voll = True
    return "Du füllst die Flasche am Wasserspender auf. Sie ist nun wieder randvoll – eine Notreserve für unterwegs."

def o_wasserspender_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject = None, onwhat: GameObject=None)->str:
    if pl.location.name != "p_ubahn":
        return "Hier ist kein Wasserspender!"
    # Flasche am Wasserspender auffüllen: "anwenden wasserspender flasche"
    if onwhat is not None and getattr(onwhat, "name", None) == "o_flasche":
        return _refill_flasche(gs)
    # Sonst: direkt am Wasserspender trinken
    pl.thirst_counter = 40
    return "***Herrlich!*** Du hast Deinen Durst mit köstlichem, frischen Wasser gestillt. Das reicht wieder für 40 Spielzüge!"

def o_flasche_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject = None, onwhat:GameObject=None) -> str:
    # Flasche am Wasserspender auffüllen: "anwenden flasche wasserspender"
    if onwhat is not None and getattr(onwhat, "name", None) == "o_wasserspender":
        return _refill_flasche(gs)
    # Aus der Flasche trinken – nur wenn sie nicht leer ist
    if not gs.flasche_voll:
        return "Die Flasche ist leer. Du musst sie erst auffüllen – z.B. am Wasserspender in der U-Bahn."
    pl.thirst_counter += 20
    gs.flasche_voll = False
    return f"***Das tat gut!*** Du hast deinen Durst gestillt – nun {pl.thirst_counter} Spielzüge, bevor du verdurstest. Die Flasche ist nun aber leer."

def o_falltuer_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject = None, onwhat:GameObject=None) -> str:
    #
    # Are we at solaranlage?
    #
    if pl.location.name != "p_solaranlage":
        return "Sowas gibt es hier nicht!"

    if gs.falltuer_offen:
        gs.falltuer_offen = False
        gs.werbeplakat_offen = False
        gs.ways["w_ubahn2_solaranlage"].visible = False
        gs.ways["w_solaranlage_ubahn2"].visible = False
        return "Die Falltür fällt krachend in ihren Rahmen und ist nun wieder verschlossen!"
    else:
        return "Da kann man machen, was man will - dir Tür ist zu."

def o_tinktur_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    if onwhat is not None and onwhat.name == "o_umschlag":
        if _F(gs).umschlag_geheimbotschaft:
            return "Die Geheimbotschaft auf dem Umschlag hast du bereits sichtbar gemacht."
        _F(gs).umschlag_geheimbotschaft = True
        gs.objects["o_umschlag"].examine = (
            "Ein dicker grauer Umschlag. Durch die Tinktur ist eine geheime Botschaft sichtbar geworden: "
            "'Zwei Schalter, zwei Räume - Kontrollraum und Generatorraum. "
            "Nur wenn beide gleichzeitig aktiviert werden, öffnet sich der Weg zur Erlösung. "
            "Einer allein kann es nicht schaffen.'"
        )
        return (
            "Du träufelst die Tinktur vorsichtig auf den Umschlag. Langsam erscheinen unsichtbare Buchstaben "
            "auf der Rückseite des Umschlags! Eine geheime Botschaft: "
            "***'Zwei Schalter, zwei Räume - Kontrollraum und Generatorraum. "
            "Nur wenn beide gleichzeitig aktiviert werden, öffnet sich der Weg zur Erlösung. "
            "Einer allein kann es nicht schaffen.'***"
        )
    return "Worauf soll ich die Tinktur anwenden? Versuche es auf einem Gegenstand!"


def o_schalter_kontrollraum_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    _F(gs).schalter_kontrollraum = True
    _F(gs).schalter_kontrollraum_timer = 3
    if _F(gs).schalter_generatorraum and _F(gs).schalter_generatorraum_timer > 0:
        _F(gs).zombie_cooperative = True
        return (
            "Du aktivierst den Schalter - er leuchtet grün auf! "
            "Ein tiefes Summen ertönt, und du spürst eine Vibration im Boden. "
            "***Beide Schalter sind gleichzeitig aktiviert! Ein Mechanismus greift ineinander!***"
        )
    return (
        "Du aktivierst den Schalter - er leuchtet grün auf. "
        "Ein Schild zeigt an: 'Warte auf Schalter 2/2...' "
        "Der zweite Schalter im Generatorraum muss ebenfalls aktiviert werden - und zwar schnell!"
    )


def o_schalter_generatorraum_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    _F(gs).schalter_generatorraum = True
    _F(gs).schalter_generatorraum_timer = 3
    if _F(gs).schalter_kontrollraum and _F(gs).schalter_kontrollraum_timer > 0:
        _F(gs).zombie_cooperative = True
        return (
            "Du aktivierst den Schalter - er leuchtet grün auf! "
            "Ein tiefes Summen ertönt, und du spürst eine Vibration im Boden. "
            "***Beide Schalter sind gleichzeitig aktiviert! Ein Mechanismus greift ineinander!***"
        )
    return (
        "Du aktivierst den Schalter - er leuchtet grün auf. "
        "Ein Schild zeigt an: 'Warte auf Schalter 1/2...' "
        "Der zweite Schalter im Kontrollraum muss ebenfalls aktiviert werden - und zwar schnell!"
    )


# Inhalt des Betriebshandbuchs - wird als Text-Popup im GUI angezeigt (siehe
# o_manual_apply_f). Kernaussage: die Anlage lässt sich nur ZU ZWEIT neu starten.
MANUAL_TEXT = (
    "BETRIEBSANLEITUNG — NOTFALL-NEUSTART DER ANLAGE\n"
    "================================================\n"
    "\n"
    "1. Die Anlage besitzt ZWEI Notfall-Schalter: einen im KONTROLLRAUM,\n"
    "   einen im GENERATORRAUM.\n"
    "\n"
    "2. An jeden Schalter muss sich eine Person stellen. Eine Person allein\n"
    "   schafft es nicht — die beiden Räume liegen zu weit auseinander.\n"
    "\n"
    "3. Beide Schalter müssen GLEICHZEITIG aktiviert werden (innerhalb weniger\n"
    "   Sekunden voneinander).\n"
    "\n"
    "4. Nur bei synchroner Aktivierung springt der Generator an — und der Weg\n"
    "   zur Erlösung öffnet sich.\n"
    "\n"
    "==> Nur gemeinsam. Niemals allein."
)


def o_manual_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    """Das Betriebshandbuch lesen ('anwenden o_manual' / 'lies das Manual').

    Zeigt den Handbuch-Inhalt als Text-Popup im GUI: dazu wird der Text auf der
    GameState zwischengespeichert; die Web-Schicht (command_engine) liest das Feld
    nach der Aktion aus, sendet eine `manual_popup`-Nachricht und leert es wieder.
    """
    gs._pending_manual_popup = MANUAL_TEXT
    base = (
        "Du schlägst das Betriebshandbuch auf und liest die Notfall-Anleitung. "
        "***Zwei Schalter, zwei Räume — und sie müssen gleichzeitig aktiviert werden. "
        "Das schafft niemand allein.***"
    )

    # Übergabe-Route: liest der Spieler die Anleitung neben einem zutraulichen Zombie
    # (COOPERATIVE/DOUBTING) vor, liest dieser mit und versteht die Lösung -> CONVINCED.
    # Ein jagender Zombie würde stattdessen beißen, kein gemeinsames Lesen.
    if pl is not None:
        from npc_zombie_state import NPCZombieState, ZombieState
        zombie = next((z for z in gs.players
                       if isinstance(z, NPCZombieState) and z.location == pl.location), None)
        if zombie is not None and zombie.zombie_state in (ZombieState.COOPERATIVE, ZombieState.DOUBTING):
            zombie._become_convinced(gs)  # Rückgabe (zombie_message) hier nicht nötig
            base += (
                "\n\n***Der Zombie beugt sich über deine Schulter und liest mit. Ein Funke "
                "Verständnis blitzt in seinen Augen auf: 'Zwei Schalter... gleichzeitig... "
                "ich brauche... dich.'***"
            )

    return base


def o_stahltuer_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    """Die Stahltür in der Höhle öffnen: das ist der "Öffner" für die ganze unterirdische
    Anlage. Sie setzt ``korridor_offen`` -> alle Wege hinter dem Korridor-Gate werden
    begehbar (siehe game_obstruction_check_functions._deep_locked).
    """
    if pl is not None and pl.location.name != "p_hoehle":
        return "Hier gibt es keine Stahltür."
    if _F(gs).korridor_offen:
        return "Die Stahltür steht bereits offen."
    _F(gs).korridor_offen = True
    return (
        "Du packst das schwere Handrad und drehst mit aller Kraft. Ein Riegel gleitet zur Seite, "
        "und mit einem dumpfen, hallenden Klacken entriegelt sich die Stahltür. "
        "***Quietschend schwingt sie auf und gibt den Weg in den Korridor frei!*** "
        "Aus der Tiefe der Anlage hörst du fernes Summen - als wäre nun mehr erreichbar als zuvor."
    )


def o_werbeplakat_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject = None, onwhat:GameObject=None) -> str:
    #
    #  Are we in ubahn2?
    #
    if pl.location.name != "p_ubahn2":
        return "Sowas gibt es hier nicht!"

    if gs.werbeplakat_offen:
        gs.falltuer_offen = False
        gs.werbeplakat_offen = False
        gs.ways["w_ubahn2_solaranlage"].visible = False
        gs.ways["w_solaranlage_ubahn2"].visible = False

        return "Die Geheimtür hinter dem Plakat ist nun verschlossen. Auch die Falltür am anderen Ende des Weges ist zu."
    else:
        gs.falltuer_offen = True
        gs.werbeplakat_offen = True
        gs.ways["w_ubahn2_solaranlage"].visible = True
        gs.ways["w_solaranlage_ubahn2"].visible = True

        return "Du hast eine Geheimtür geöffnet, die hinter dem Plakat versteckt war! Dahinter ein Gang - und ein Rumpeln, als würde auch am anderen Ende des Ganges eine Tür aufgehen!"
""" This module contains all the game verbs as well as a super simple parser and execution mechanism"""
#import pylab as p

from GameState import GameState
from GameObject import GameObject
from PlayerState import PlayerState
from NPCPlayerState import NPCPlayerState
from ExplosionState import ExplosionState
from Place import Place
from Way import Way

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

    if gs.ubahn_in_otherstation:
        gs.ubahn_in_otherstation = False
        gs.ways["w_wagen_ubahn"].visible = True
        gs.ways["w_wagen_ubahn2"].visible = False
        gs.ways["w_ubahn_wagen"].visible = True
        gs.ways["w_ubahn2_wagen"].visible = False
        return "Die Tür schließt sich. Der Wagen setzt sich in Bewegung, und fährt zurück zum ersten Bahnsteig. Die Tür öffnet sich wieder."
    else:
        gs.ubahn_in_otherstation = True
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
        if not gs.hebel:
            if not gs.hauptschalter:
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
        if gs.hebel:
            return 'Der Warenautomat liegt auf dem Bauch. Er ist zwar völlig intakt, und nicht zerbrochen, aber da kann man kein Geld einwerfen!'
        else:
            if not gs.hauptschalter:
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
    return "Du scheinst mit den Dollars hier wnig anfangen zu können..."

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
    if not gs.hauptschalter:
        return "Du ruckelst am Hebel, aber nichts passiert"
    if pl != None:
        if pl.location == gs.places["p_dach"]:
            if gs.hebel:
                gs.hebel = False
                gs.ways["w_warenautomat_ubahn"].visible = False
                gs.places["p_warenautomat"].description = "Hier steht ein Warenautomat, an dem man Fahrradteile kaufen kann."
                gs.objects["o_warenautomat"].examine = "Ein Warenautomat mit Fahrradteilen. Er enthält tatsächlich auch eine Fahrradkette! Jetzt bräuchte man Geld - und zwar italienische Lira. Dieser Automat akzeptiert nur diese!"
                return "Es rumpelt - und der Warenautomat richtet sich wieder auf!"
            else:
                gs.hebel = True
                gs.ways["w_warenautomat_ubahn"].visible = True
                gs.objects["o_warenautomat"].examine = "Ein Warenautomat, der auf dem Rücken liegt. Da wo er stand, führt eine Treppe nach unten!"
                gs.places["p_warenautomat"].description = "Hier liegt ein Warenautomat auf dem Rücken. Da wo er wohl gestanden hat, ist eine Öffnung im Boden. Man sieht darin eine Treppe - es geht zu einer U-Bahn-Station!"
                return "Es rumpelt - Die siehst, wie der Warenautomat sich langsam auf den Rücken legt. Da wo er stand, ist nun eine Öffnung - und darin eine Treppe zu einer U-Bahn-Station!"
        else:
            return "Hier ist kein Hebel!"
    else:
        return "??? Kein Spieler ???"

from GameState import GameState
from PlayerState import PlayerState
def o_sprengladung_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    from ExplosionState import ExplosionState

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
            gs.verb_drop(pl,"o_sprengladung")
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
                if type(d) is NPCPlayerState:
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
    if not gs.hauptschalter:
        return "Sieht so aus, als wäre der Automat ausgeschaltet"

    if pl.location.name!="p_geldautomat" and onwhat.name!="o_geldautomat":
        return "Ich verstehe nicht, was genau du mit der Geldkarte machen willst!"

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
            z = int(x)
    if gs.geheimzahl == z:
        gs.objects["o_geld_dollar"].visible = True
        return "**Die Zahl stimmt!** Du tippst die entsprechenden Tasten - der Automat rattert, und spuckt ein Bündel Scheine aus. Frisch gedruckte US-Dollar!"
    else:
        return " --- Die Zahl ist falsch. ---"

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
            return "Tja - Du hast zwar die Fahrradkette, aber der Briefumschlag ist irgendwann pulverisiert worden. Schade, ***Du verlierst das Spiel!***"
        if gs.objects["o_umschlag"] in pl.inventory:
            gs.game_over = True
            gs.game_won = True
            return "Du reparierst Dein Fahrrad, und schaffst es rechtzeitig, den Briefumschlag abzugeben. Du bist ein Held, rettest die Welt, und ***gewinnst das Spiel!***"
        else:
            return "Das wäre schön - aber wo hast du den Briefumschlag abgelegt? Den brauchst Du..."
    else:
        return "Wie soll das gehen?"

def o_wasserspender_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject = None, onwhat: GameObject=None)->str:
    if pl.location.name == "p_ubahn":
        pl.thirst_counter = 40
        return "***Herrlich!*** Du hast Deinen Durst mit köstlichem, frischen Wasser gestillt. Das reicht wieder für 40 Spielzüge!"
    else:
        return "Hier ist kein Wasserspender!"
"""Verb / command execution for GameState.

GameVerbsMixin contributes verb_execute_json (the command dispatch table) and all
verb_* handlers to GameState. Extracted from GameState (Step 2.2 refactor) as a
mixin so the method bodies stay byte-for-byte identical; GameState inherits it.

Relies on the host class (GameState) for: world access (objects/places/ways,
obj_name_from_friendly_name, find_shortest_path), flags (gs.<flag>), players, llm,
compile_current_game_context*, get_flags, check_game_over, and the web-session
state (web_sessions / cmd_q) used by async_verb_interact. NPCDogState / pprint /
WebDialogs / asyncio are imported locally inside the methods (kept that way to
avoid an import cycle with GameState).
"""
from __future__ import annotations
import json

from PlayerState import PlayerState
from Utils import tw_print, dprint, dpprint, dl


class GameVerbsMixin:
    def verb_execute_json(self, pl: PlayerState, command_dict: dict, session_id=None) -> str:
        """ Instead of a string (see verb_execute) cmd is a dictionary as was returned by the LLM as structured
            return to LLM user input"""
        # self.cur_session_id = session_id
        if "function_call" not in command_dict:
            return "Interner Fehler: Ungültiges Befehlsformat."

        dpprint(dl.GAMESTATE,command_dict)

        func_call = command_dict["function_call"]
        func_name = func_call["name"]
        args = func_call.get("args", {})
        #
        # Python magic
        #

        vtab = {
            "anwenden":(self.verb_apply,2),
            "nimm":(self.verb_take,1),
            "ablegen":(self.verb_drop,1),
            "umsehen":(self.verb_context,0),
            "untersuche": (self.verb_examine,1),
            "hilfe":(self.verb_help,0),
            "gehe":(self.verb_walk,1),
            "toeten": (self.verb_kill,1),
            "angreifen": (self.verb_attack,0),
            "inventory": (self.verb_inventory,0),
            "context": (self.verb_context,0),
            "dogstate": (self.verb_dogstate,0),
            "quit": (self.verb_quit,0),
            "nichts": (self.verb_noop,0),
            #"interagiere": (self.verb_interact,2),
            #"interaktion": (self.verb_interact, 2),
            "zurueckweisen": (self.verb_reject,1),
            "zurückweisen": (self.verb_reject, 1),
            "unbekannt": (self.verb_unknown,0),
            "json_write": (self.verb_json_write,0)
        }
        verb,numargs = vtab.get(func_name,(None,None))
        if verb is None:
            dprint(dl.GAMESTATE, f"verb_execute_json: Unknown verb '{func_name}' — not in vtab")
            return f"Das Kommando '{func_name}' wurde nicht erkannt."
        r=verb(pl,session_id, **args)
        return r




    def verb_unknown(self, pl: PlayerState, session_id=None):
        from pprint import pprint
        print("LLM did not understand input correctly. Current Player atomic command queue:")
        pprint(pl.cmd_q)
        return "nichts"

    def verb_dogstate(self, pl: PlayerState, session_id=None):
        from NPCDogState import NPCDogState
        from pprint import pprint
        dgf = None
        for p in self.players:
            if type(p) is NPCDogState:
                dgf = p
                break
        if not dgf:
            return ("Kein Hund mehr im Spiel!!")
        else:
            pprint(dgf,depth=2)
            return "nichts"



    async def async_verb_interact(self, pl: PlayerState, session_id, who, firstmessage=""):
        #
        # Check if there is a npc named who, and if (s)he is in the same location as pl
        # This verb is called
        #
        import asyncio
        pl_who = next((p for p in self.players if p.name == who), None)
        if not pl_who:
            return f"{who}? Kenne ich nicht"

        if pl_who == pl:
            return "Selbstgespräche werden hier lieber nicht geführt."

        if pl.location != pl_who.location:
            return f"{who} ist nicht hier."

        if session_id in self.web_sessions:
            if "WebDialogs" in self.web_sessions[session_id]:
                wd: object = self.web_sessions[session_id]["WebDialogs"]
                #await wd.do_chat(self, pl, pl_who, firstmessage)
                #asyncio.run(wd.do_chat(self, pl, pl_who, firstmessage))
                await wd.do_chat(self, pl, pl_who, firstmessage)
        return "nichts"


    def verb_apply(self, pl: PlayerState, session_id, what, towhat=None):

        r="Nichts anzuwenden"
        if what is None:
            return r

        found_what = self.obj_name_from_friendly_name(what)
        found_towhat = self.obj_name_from_friendly_name(towhat) if towhat is not None else None
        if found_what:
            o_what = self.objects.get(found_what)
            if not ( o_what in pl.inventory or o_what in pl.location.place_objects):
                return f"Ein/eine {what} gibt es hier nicht."
        else:
            return "Sowas kenne ich nicht"

        if found_towhat:
            o_towhat = self.objects.get(found_towhat)
            if not (o_towhat in pl.inventory or o_towhat in pl.location.place_objects):
                return f"Ein/eine {towhat} gibt es hier nicht."

        if towhat is not None:
            # r = f"apply {what} to {towhat} in this context"
            r=""
            if o_what is not None:
                r = r+ "\n" + o_what.apply_f(self, pl, o_what, o_towhat)
        else:
            # r = f"apply {what} in this context"
            r=""
            if o_what is not None:
                r = r+ "\n"+ o_what.apply_f(self, pl, o_what, None)

        return r

    def verb_take(self, pl: PlayerState, session_id, whato):
        what = self.obj_name_from_friendly_name(whato)
        loc = pl.location
        # obj = loc.place_objects.get(what) - egal
        obj = None
        for o in loc.place_objects:
            if o.name == what:
                obj = o
                break
        if obj == None:
            r= "Sowas gibt es hier nicht."
        else:
            if not obj.fixed:

                pl.add_to_inventory(obj)
                if obj.take_f != None:
                    r= obj.take_f(self,pl)
                else:
                    r= f"Du hast {what} nun bei dir"
            else:
                r = f"Du kannst {what} nicht aufnehmen"
        return r

    def verb_drop(self, pl: PlayerState, session_id, whato):
        what = self.obj_name_from_friendly_name(whato)
        if what is None:
            return "Sowas kenne ich nicht"

        obj = self.objects.get(what)
        if obj == None:
            return "Sowas gibt es in diesem Spiel nicht!"

        if pl.is_in_inventory(obj):
            pl.remove_from_inventory(obj)
            obj.hidden = False
            obj.ownedby = pl.location
            pl.location.place_objects.append(obj)
            r = f'Objekt {what} in/auf/am {pl.location.name} abgelegt'
            return r

        r= f'{what} ist nicht in {pl.name} inventory'

        return r

    def verb_lookaround_old(self, pl: PlayerState, session_id):
        loc = pl.location
        retstr = f"""**Ort: {pl.location.name}**
{pl.location.place_prompt_f(self,pl) if pl.location.place_prompt_f else pl.location.place_prompt}


Am Ort sind folgende Objekte zu sehen:"""
        rs = ""
        for i in pl.location.place_objects:
            if not i.hidden:
                rs = rs+f'\n- {i.callnames[0]} - {i.examine}'
        if rs == "":
            rs="(keine)"
        dogfound = None
        from NPCDogState import NPCDogState
        for d in self.players:
            if type(d) is NPCDogState:
                dogfound = d
        if dogfound and dogfound.location == pl.location:
            print("\n!!!! Da ist ein großer Hund bei dir  !!!!\n")
        can_go = []
        for p in pl.location.ways:
            if p.visible and p.obstruction_check(self) == "Free":
                can_go.append(p.destination)
        if dogfound and dogfound.location in can_go:
            print(f"\n!! Da ist ein großer Hund in deiner Nachbarschaft (bei/beim) {dogfound.location.callnames[0]} !!\n")

        retstr = retstr+rs+"\n\nDu kannst folgende wege gehen:\n"
        loc = pl.location
        for w in loc.ways:
            if w.visible:
                retstr = retstr + f'- {w.destination.callnames[0]} ({w.destination.name})\n'
        return retstr

    def verb_lookaround_llm(self, pl: PlayerState, session_id):

        rval = self.llm.generate_scene_description(self.compile_current_game_context(pl))
        return rval

    def verb_lookaround(self, pl: PlayerState, session_id):
        r=self.llm.narrate(self,pl)
        return r


    def verb_help(self, pl: PlayerState, session_id):
        rval = """
    Du musst Dein Fahrrad reparieren, um rechtzeitig den Umschlag, den Du 
    hoffentlich noch bei dir hast, an sein Ziel zu bringen. Sonst geht die 
    Welt unter. 
    
    Folgende Kommandos kannst du absetzen:
    
    hilfe  ............................ Diese Hilfe
    nichts ............................ Eine Spielrunde abwarten
    quit .............................. Spiel beenden
    
    Ansonsten gib als Freitext das ein, was du tun möchtest 
    
    Beispiele:
    
    "Gehe zum Schuppen und untersuche den Stuhl"
    "Gehe dahin, wo der Hund ist"
    "Nimm die Geheimzahl an dich"
    
    Achtung
    =======
    * Achte auf den Hund! Dieser ist dir nicht wohlgesonnen! Du kannst ihn 
      für einige Runden besänftigen, indem du ihn mit etwas fütterst!
    * Du wirst im Laufe der Zeit Durst bekommen. Suche dir etwas, wo du
      trinken kannst, sonst ist das Spiel zu Ende
    
        """
        return rval

    def verb_walk(self, pl: PlayerState, session_id, direction: str):
        #
        # Player walks into "direction" (either name of way or name of destination)
        #
        # (1) Is there a way from his current location?
        #   (1a) if yes, is there an obstacle in the way?
        #     (1aa) if no --> walk, return success message
        #     (1ab) else --> return failure message (Obstacle in way)
        # (2) return failure message ("There is no path here")
        w_found = None
        direction_found = self.place_name_from_friendly_name(direction)
        w_found = next((w for w in pl.location.ways if w.destination.name==direction_found), None)

        if w_found is None:
            return f"Es existiert kein Weg zum Ort {direction}"
        if not w_found.visible:
            return "Diesen Weg sehe ich hier nicht!"
        ob = w_found.obstruction_check(self)

        if ob != "Free":
            return ob  # If there is an obstacle, function returns string different from "Free"

        #
        # Finally - we can go the way
        #
        pl.location = w_found.destination
        r = f"{pl.name} ist nun hier: {pl.location.callnames[0]} "
        return r

    def verb_examine(self, pl: PlayerState, session_id, what: str):
        #
        # Does an object with that name exist in the users inventory or in the current location?
        # if so, return its examine string, if not, return failure ("No such thing here")
        obj_here = None
        what_found = self.obj_name_from_friendly_name(what)
        retstr = "So etwas gibt es hier nicht, und du hast sowas auch nicht bei dir."
        if what_found is None:
            return retstr

        for i in pl.inventory:
            if i.name == what_found:
                obj_here = i
                retstr = f"Du trägst {i.name} gerade bei dir."
                break
        if obj_here == None:
            retstr = ""
            for i in pl.location.place_objects:
                if i.name == what_found:
                    obj_here = i
                    break
        if obj_here != None:

            #
            # Sometimes examinig one thing reveals another thing
            #
            """
            if what == "o_blumentopf":
                if self.objects["o_schluessel"].hidden:
                    retstr = retstr + "Ein alter Blumentopf - aber warte: **unter dem Blumentopf liegt ein Schlüssel!!!**"
                    self.objects["o_blumentopf"].examine = "Unter diesem Blumentopf hast Du den Schlüssel gefunden"
                    self.objects["o_schluessel"].hidden = False
            elif what == "o_skelett":
                if self.objects["o_geldboerse"].hidden:
                    retstr = retstr + "Oh weh, der sitzt wohl schon länger hier! Ein Skelett, welches einen verschlissenen Anzug trägt. **Im Anzug findest du eine Geldboerse!**"
                    self.objects["o_geldboerse"].hidden = False
                    self.objects["o_skelett"].examine = "Bei diesem Knochenmann hast Du eine Geldbörse gefunden!"
            elif what == "o_geldboerse":
                if self.objects["o_ec_karte"].hidden:
                    self.objects["o_ec_karte"].hidden = False
                    self.objects["o_geldboerse"].examine = "In dieser Geldbörse hast Du eine EC-Karte gefunden"
                    retstr = retstr + "Fein! Hier ist eine EC-Karte! Die passt bestimmt in einen Geldautomaten!"
            elif what == "o_muelleimer":
                if self.objects["o_geheimzahl"].hidden:
                    from random import randint
                    self.geheimzahl = randint(1,9999)
                    self.objects["o_geheimzahl"].hidden = False
                    self.objects["o_geheimzahl"].examine = f"Eine Geheimzahl: {self.geheimzahl:04}"
                    retstr = retstr + f"Im Mülleimer findest Du einen Zettel mit einer Geheimzahl! Die Geheimzahl ist: {self.geheimzahl:04}"
"""
            if self.objects[what_found].reveal_f != None:
                retstr = retstr + self.objects[what_found].reveal_f(self,pl,what_found, None)

            else:
                retstr = retstr + f"{obj_here.examine}"
        else:
            retstr = f'{what_found} - sowas gibt es hier nicht!'
        return retstr

    def verb_llm(self, pl:PlayerState, session_id):
        from pprint import pprint
        from rich.prompt import Prompt
        user_input = ""
        while user_input == "":
            ui = Prompt.ask(f"(llm-test) Was tust du jetzt, {pl.name}? Deine Eingabe")
            if ui != None:
                user_input = ui.strip().lower()
            else:
                user_input = ""
        gi = (self.llm.parse_user_input_to_commands(
            user_input,

            self.compile_current_game_context(pl)
        ))
        pprint(gi)
        return "nichts"

    def verb_kill(self, pl: PlayerState, session_id, whom):
        self.game_over = True
        return f"{pl.name} tötet {whom} in heldischem Kampf"

    def verb_inventory(self, pl: PlayerState, session_id):
        tw_print("**Du trägst bei dir:**")
        for i in pl.get_inventory():
            tw_print(f'- "{i.name}" --> {i.examine}')
        return "nichts"

    def verb_context(self, pl: PlayerState, session_id):
        """ERWEITERTE Kontext-Ausgabe mit Web-Interface Info"""
        from pprint import pprint

        # Bestehende Kontext-Ausgabe
        r = self.compile_current_game_context(pl)
        pprint(r)

        # NEUE Web-Interface Debug-Info
        if self.is_web_interface_active():
            print("\n=== WEB-INTERFACE STATUS ===")
            self.debug_web_status()

    def verb_quit(self, pl: PlayerState, session_id):
        self.game_over  = True
        return f"{pl.name} beendet das Spiel."

    def verb_noop(self, pl: PlayerState, session_id):
        if type(pl) is PlayerState:
            return "Du tust nichts"
        else:
            return ""

    #def verb_interact(self, pl: PlayerState, whom, input):
    #    return f'{pl.name} an {whom}:  "{input}"'

    def verb_reject(self, pl: PlayerState, session_id, why, **kwargs)->str:
        """ LLM rejects to do something because it did not understand user input and provides explanation in "why" """
        return f'***Nachricht von der Spielleitung:*** {why}'


    def verb_attack(self, pl: PlayerState, session_id, whom="")->str:
        """ Player attacks dog which needs to be in the same place as Player"""
        from NPCDogState import NPCDogState
        dog = next(d for d in self.players if type(d) is NPCDogState)
        #dog = None
        #for d in self.players:
        #    if type(d) is NPCDogState:
        #        dog = d
        #        break
        if dog is None:
            return "Es gibt gar keinen Hund mehr im Spiel"

        if dog.location != pl.location:
            return "Da ist gar kein Hund bei dir, den Du angreifen könntest"

        else:
            r = dog.gets_attacked(self, pl)
            return ""
            #return f"(Angriff auf den Hund abgeschlossen)"

    def verb_json_write(self,pl:PlayerState, session_id) -> str:
        """
        Write structures as JSON
        :param pl:
        :return:
        """
        from json import dump
        # Writing to a JSON file with skipkeys=True
        with open("output.json", "w") as outfile:
            json.dump(self.places, outfile, skipkeys=True)


    # Zusätzlich: Neuer Befehl für Layout-Wechsel
    def verb_layout(gs, pl: PlayerState, session_id) -> str:
        """Wechsle Layout-Modus"""
        # Diese Funktion würde in GameState hinzugefügt
        return "layout_toggle"  # Spezieller Return-Code

    #
    # Additional code for web based mini games
    #

    from WebDialogs import WebDialogs

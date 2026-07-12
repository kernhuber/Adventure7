"""Verb / command execution for GameState.

GameVerbsMixin contributes verb_execute_json (the command dispatch table) and all
verb_* handlers to GameState. Extracted from GameState (Step 2.2 refactor) as a
mixin so the method bodies stay byte-for-byte identical; GameState inherits it.

Relies on the host class (GameState) for: world access (objects/places/ways,
obj_name_from_friendly_name, find_shortest_path), flags (gs.<flag>), players, llm,
compile_current_game_context*, get_flags, check_game_over. Interactive dialogs are
injected via the PlayerDialogs port (async_verb_interact's ``dialogs`` argument), so
the engine no longer reaches into web_sessions. NPCDogState / pprint / asyncio are
imported locally inside the methods (kept that way to avoid an import cycle with
GameState).
"""
from __future__ import annotations
import json

from player_state import PlayerState
from utils import tw_print, dprint, dpprint, dl


class GameVerbsMixin:
    def verb_execute_json(self, pl: PlayerState, command_dict: dict, session_id=None) -> str:
        """ Instead of a string (see verb_execute) cmd is a dictionary as was returned by the LLM as structured
            return to LLM user input"""
        # Reset per call; set True below if the command cannot be dispatched
        # (malformed LLM tool-call / unknown verb). Callers read this so a failed
        # command is not counted as a real game turn.
        self.last_command_was_system_error = False
        # self.cur_session_id = session_id
        if "function_call" not in command_dict:
            self.last_command_was_system_error = True
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
            "gib":(self.verb_give,2),
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
            "zombiestate": (self.verb_zombiestate,0),
            "zombie_versteinern": (self.verb_zombie_versteinern,0),
            "zombie_erloesen": (self.verb_zombie_erloest,0),
            "zombie_erlösen": (self.verb_zombie_erloest,0),
            "tokenstate": (self.verb_tokenstats,0),
            "tokenstats": (self.verb_tokenstats, 0),
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
            self.last_command_was_system_error = True
            return f"Das Kommando '{func_name}' wurde nicht erkannt."
        try:
            r = verb(pl, session_id, **args)
        except TypeError as e:
            # Malformed LLM tool-call (e.g. missing/extra args). Fail soft: log it,
            # return a clean rejection, and flag it as a system error so it does not
            # cost the player a turn. The full error is logged for debugging.
            dprint(dl.GAMESTATE, f"verb_execute_json: ungültiger Tool-Call '{func_name}' (args={args}): {e}")
            self.last_command_was_system_error = True
            return "Das habe ich leider nicht richtig verstanden – bitte formuliere es anders."
        return r




    def verb_unknown(self, pl: PlayerState, session_id=None):
        from pprint import pprint
        print("LLM did not understand input correctly. Current Player atomic command queue:")
        pprint(pl.cmd_q)
        return "nichts"

    def verb_dogstate(self, pl: PlayerState, session_id=None):
        from npc_dog_state import NPCDogState
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

    def verb_zombiestate(self, pl: PlayerState, session_id=None):
        """Debug-Kommando analog zu dogstate: den kompletten Zombie-Zustand in die Shell
        ausgeben - Flags/State/Koordinaten UND das Gedächtnis (Notizbuch + episodisch),
        damit man beim Spielen sieht, wie der Zombie 'arbeitet'."""
        from npc_zombie_state import NPCZombieState
        z = next((p for p in self.players if isinstance(p, NPCZombieState)), None)
        if not z:
            print("Kein Zombie im Spiel (noch nicht erwacht?).")
            return "nichts"
        loc = z.location.callnames[0] if (z.location and z.location.callnames) else (z.location.name if z.location else "?")
        inv = [i.callnames[0] if i.callnames else i.name for i in z.inventory]
        out = [
            "",
            "==================== ZOMBIE-STATE ====================",
            f" Ort:              {loc}   ({z.location.name if z.location else '?'})",
            f" State:            {z.zombie_state.name}   -> {z.zombie_state_message}",
            f" Vertrauen(trust): {z.trust}      Lebensenergie: {z.zombie_thirst}",
            f" Inventar:         {inv}",
            f" Flags:            cooperation_agreed={z.cooperation_agreed}  awaiting_share={z.awaiting_share_response}  "
            f"share_agreed={z.share_agreed}  remembered_control_room={z.remembered_control_room}",
            f" Cooldowns/Zähler: move={z.move_cooldown}  share={z.share_cooldown}  "
            f"turns_since_contact={z.turns_since_player_contact}  turn={z.turn_counter}",
            f" player_last_seen: {z.player_last_seen_location}",
            "  --- Notizbuch (notes / Arbeitsgedächtnis) ---",
            f"  {z.notes}",
            "  --- Episodisches Gesprächs-Gedächtnis (last_chat, über Gespräche hinweg) ---",
            f"  {z.last_chat}",
            "======================================================",
            "",
        ]
        print("\n".join(out))
        return "nichts"

    def _zombie_event_text(self, event: dict, fallback: str) -> str:
        """Zieht die Erzähltext-Nachricht aus einem zombie_event-Command (wie es
        _do_petrify/_do_redemption zurückgeben) heraus - für die Verb-Rückgabe."""
        try:
            return event["function_call"]["args"].get("message") or fallback
        except Exception:
            return fallback

    def verb_zombie_versteinern(self, pl: PlayerState, session_id=None):
        """TEST-Kommando (schaltbar via utils.ZOMBIE_TESTCMDS): löst das Versteinern des
        Zombies aus - er zerfällt, sein Inventar vergeht mit ihm, der Wasserspender trocknet
        aus, und er verschwindet sofort aus dem Spiel."""
        from npc_zombie_state import NPCZombieState
        z = next((p for p in self.players if isinstance(p, NPCZombieState)), None)
        if z is None:
            return "Es ist kein Zombie (mehr) im Spiel."
        event = z._do_petrify(self)
        if z in self.players:          # im Verb-Kontext sicher sofort entfernen
            self.players.remove(z)
        return self._zombie_event_text(event, "Der Zombie wurde versteinert und ist verschwunden.")

    def verb_zombie_erloest(self, pl: PlayerState, session_id=None):
        """TEST-Kommando (schaltbar via utils.ZOMBIE_TESTCMDS): löst die Erlösung des
        Zombies aus - er lässt alles Getragene am Ort fallen, bedankt sich und verschwindet
        aus dem Spiel."""
        from npc_zombie_state import NPCZombieState
        z = next((p for p in self.players if isinstance(p, NPCZombieState)), None)
        if z is None:
            return "Es ist kein Zombie (mehr) im Spiel."
        event = z._do_redemption(self)
        if z in self.players:          # im Verb-Kontext sicher sofort entfernen
            self.players.remove(z)
        return self._zombie_event_text(event, "Der Zombie wurde erlöst und ist verschwunden.")

    def verb_tokenstats(self, pl: PlayerState, session_id=None):
        """Debug-Kommando analog zu dogstate/zombiestate: den kumulierten LLM-Token-
        Verbrauch der laufenden Session nach Quelle (caller) aufschlüsseln - die Baseline
        fürs Prompt-Optimierungs-Projekt. Datenquelle: GeminiInterface.token_report()."""
        llm = getattr(self.llm, "_impl", self.llm)   # ggf. am Adapter vorbei auf die echte LLM
        report_fn = getattr(llm, "token_report", None)
        if not callable(report_fn):
            print("Kein Token-Report verfügbar (Demo-Modus / kein GeminiInterface).")
            return "nichts"
        report = report_fn()
        gesamt = report.pop("_gesamt", {"calls": 0, "tokens": 0, "cached": 0})
        rows = sorted(report.items(), key=lambda kv: kv[1].get("tokens", 0), reverse=True)
        def _pct(cached, tok):
            return f"{100 * cached / tok:.0f}%" if tok else "-"
        out = [
            "",
            "======================== TOKEN-REPORT (Session) ========================",
            f" {'Quelle (caller)':<40}{'Calls':>6}{'Tokens':>9}{'Cached':>8}{'Cache%':>7}{'Ø/Call':>8}",
            " " + "-" * 78,
        ]
        for caller, s in rows:
            calls, tok, cached = s.get("calls", 0), s.get("tokens", 0), s.get("cached", 0)
            avg = (tok / calls) if calls else 0
            out.append(f" {caller:<40}{calls:>6}{tok:>9}{cached:>8}{_pct(cached, tok):>7}{avg:>8.0f}")
        g_tok, g_cached = gesamt.get('tokens', 0), gesamt.get('cached', 0)
        out += [
            " " + "-" * 78,
            f" {'GESAMT':<40}{gesamt.get('calls', 0):>6}{g_tok:>9}{g_cached:>8}{_pct(g_cached, g_tok):>7}",
            " (Cached = implizit gecachte Prompt-Tokens, Gemini 2.5, ~75% billiger)",
            "========================================================================",
            "",
        ]
        print("\n".join(out))
        return (f"Token-Report in der Shell ausgegeben — Gesamt: {g_tok} Tokens "
                f"({g_cached} cached, {_pct(g_cached, g_tok)}) / {gesamt.get('calls', 0)} Calls.")



    async def async_verb_interact(self, pl: PlayerState, session_id, who, firstmessage="", dialogs=None):
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

        # Dialogs (PlayerDialogs port) are injected by the caller; the engine no
        # longer looks up WebDialogs via web_sessions.
        if dialogs is not None:
            await dialogs.do_chat(self, pl, pl_who, firstmessage)
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
                    r= f"Du hast {obj.callnames[0].capitalize()} nun bei dir"
            else:
                r = f"Du kannst {obj.callnames[0].capitalize()} nicht aufnehmen"
        return r

    def verb_give(self, pl: PlayerState, session_id, what=None, towhom=None):
        """Der Spieler gibt einen Gegenstand aus seinem Inventar an einen ANWESENDEN NPC.

        Analog zu verb_drop/verb_apply: obj_name_from_friendly_name liefert nur die ID -
        das GameObject kommt aus self.objects.get(...). is_in_inventory/add_to_inventory
        arbeiten auf GameObjects, nicht auf IDs. Ziel muss ein NPC am selben Ort sein.
        """
        if what is None or towhom is None:
            return "Ich bin verwirrt - wem soll ich was geben?"
        from npc_dog_state import NPCDogState
        from npc_zombie_state import NPCZombieState

        # ID -> GameObject (der Zweischritt, der vorher fehlte)
        obj = self.objects.get(self.obj_name_from_friendly_name(what))
        if obj is None:
            return "Sowas gibt es hier nicht."
        if not pl.is_in_inventory(obj):
            return "Sowas hast Du nicht bei dir."

        # Ziel: ein ANWESENDER NPC (Hund/Zombie) - der Spieler selbst zählt nicht.
        here = pl.location
        towhom_l = (towhom or "").lower()
        target = next((p for p in self.players
                       if p is not pl and p.location == here
                       and isinstance(p, (NPCDogState, NPCZombieState))
                       and p.name.lower() == towhom_l), None)
        if target is None:
            return f"Hier ist niemand namens {towhom}, dem du etwas geben könntest."

        # Der NPC entscheidet selbst, was mit dem Geschenk geschieht (annehmen/fressen/
        # ablegen) und liefert die Spieler-Rückmeldung. gets_given nimmt obj ggf. selbst
        # aus dem Spielerinventar - so kann ein NPC ein Geschenk auch ablehnen.
        return target.gets_given(self, pl, obj)

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
            r = f'{obj.callnames[0].capitalize()} in/auf/am {pl.location.callnames[0].capitalize()} abgelegt'
            return r

        r= f'{obj.callnames[0].capitalize()} ist nicht in {pl.name} inventory'

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
        from npc_dog_state import NPCDogState
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
                retstr = "Du trägst es gerade bei dir. "
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
            retstr = f'{self.objects[what_found].callnames[0].capitalize()} - sowas gibt es hier nicht!'
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
        """Kontext-Ausgabe (Debug)"""
        from pprint import pprint

        r = self.compile_current_game_context(pl)
        pprint(r)

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
        """Spieler greift einen NPC am selben Ort an (Hund oder Zombie).

        Ein Angriff auf den Zombie ist zugleich der härteste Vertrauensbruch
        (siehe NPCZombieState.gets_attacked). Welcher NPC gemeint ist, ergibt sich
        aus ``whom`` (falls eindeutig) bzw. daraus, wer gerade anwesend ist.
        """
        from npc_dog_state import NPCDogState
        from npc_zombie_state import NPCZombieState

        here = pl.location
        dog = next((d for d in self.players if isinstance(d, NPCDogState) and d.location == here), None)
        zombie = next((z for z in self.players if isinstance(z, NPCZombieState) and z.location == here), None)

        # Zielwahl: explizite Nennung hat Vorrang, sonst der anwesende NPC
        # (Zombie zuerst, da der Hund im Spiel meist abwesend ist).
        whom_l = (whom or "").lower()
        target = None
        if zombie is not None and any(k in whom_l for k in ("zombie", "kronstein", "harald", "untot")):
            target = zombie
        elif dog is not None and any(k in whom_l for k in ("hund", "dog", "köter", "koeter")):
            target = dog
        elif zombie is not None:
            target = zombie
        elif dog is not None:
            target = dog

        if target is None:
            return "Hier ist niemand, den du angreifen könntest."

        result = target.gets_attacked(self, pl)
        if isinstance(target, NPCZombieState):
            return result or ""
        # Hund: Rückgabe wird wie bisher verworfen (Ablauf läuft über command_after_fight
        # bzw. das Minispiel, nicht über die Befehlsantwort).
        return ""

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


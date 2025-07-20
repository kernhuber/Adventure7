# Enhanced UI System
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.progress import Progress
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
import time


class EnhancedUI:
    def __init__(self):
        self.console = Console()

    def display_status_panel(self, player: 'PlayerState') -> Panel:
        """Zeige Player-Status in einem Panel"""
        status_content = []

        # Durst-Anzeige
        thirst_percent = (player.thirst_counter / 40) * 100
        thirst_color = "green" if thirst_percent > 50 else "yellow" if thirst_percent > 25 else "red"
        status_content.append(f"🚰 Durst: [{thirst_color}]{player.thirst_counter}/40[/{thirst_color}]")

        # Aktueller Ort
        status_content.append(f"📍 Ort: {player.location.callnames[0]}")

        # Inventar
        if player.inventory:
            inventory_text = ", ".join([obj.callnames[0] for obj in player.inventory])
            status_content.append(f"🎒 Inventar: {inventory_text}")
        else:
            status_content.append("🎒 Inventar: leer")

        return Panel(
            "\n".join(status_content),
            title=f"[bold]{player.name}[/bold]",
            border_style="blue"
        )

    def display_location_info(self, player: 'PlayerState', gs: 'GameState') -> Panel:
        """Zeige Ort-Informationen"""
        content = []

        # Objekte am Ort
        visible_objects = [obj for obj in player.location.place_objects if not obj.hidden]
        if visible_objects:
            content.append("**Objekte hier:**")
            for obj in visible_objects:
                content.append(f"• {obj.callnames[0]}")

        # Verfügbare Wege
        available_ways = [way for way in player.location.ways if way.visible and way.obstruction_check(gs) == "Free"]
        if available_ways:
            content.append("\n**Wohin kannst du gehen:**")
            for way in available_ways:
                content.append(f"• {way.destination.callnames[0]}")

        return Panel(
            "\n".join(content),
            title="[bold]Umgebung[/bold]",
            border_style="green"
        )

    def display_game_screen(self, player: 'PlayerState', gs: 'GameState', last_action: str = ""):
        """Zeige den Haupt-Spielbildschirm"""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )

        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )

        # Header
        layout["header"].update(Panel(
            f"[bold]🏜️ Wüsten-Adventure[/bold] - Runde {gs.time}",
            style="bold white on blue"
        ))

        # Hauptbereich - Szenenbeschreibung
        scene_description = gs.llm.narrate(gs, player) if gs.llm else "Beschreibung nicht verfügbar"
        layout["left"].update(Panel(
            scene_description,
            title="[bold]Aktuelle Szene[/bold]",
            border_style="yellow"
        ))

        # Rechter Bereich - Status und Umgebung
        layout["right"].split_column(
            Layout(self.display_status_panel(player)),
            Layout(self.display_location_info(player, gs))
        )

        # Footer - Letzte Aktion
        if last_action:
            layout["footer"].update(Panel(
                last_action,
                title="[bold]Letzte Aktion[/bold]",
                border_style="cyan"
            ))

        self.console.clear()
        self.console.print(layout)

    def display_help(self):
        """Zeige erweiterte Hilfe"""
        help_table = Table(title="🎮 Spielhilfe")
        help_table.add_column("Befehl", style="cyan", no_wrap=True)
        help_table.add_column("Beschreibung", style="white")
        help_table.add_column("Beispiel", style="green")

        commands = [
            ("Bewegung", "Gehe zu einem anderen Ort", "gehe zum Schuppen"),
            ("Untersuchen", "Betrachte Objekte genauer", "untersuche den Blumentopf"),
            ("Nehmen", "Objekte ins Inventar", "nimm den Schlüssel"),
            ("Anwenden", "Benutze Gegenstände", "wende Schlüssel auf Schuppen an"),
            ("Umsehen", "Überblick über aktuelle Umgebung", "sieh dich um"),
            ("Inventar", "Zeige dein Inventar", "inventory"),
            ("Speichern", "Speichere den Spielstand", "speichere spiel"),
            ("Laden", "Lade einen Spielstand", "lade spiel"),
            ("Hilfe", "Zeige diese Hilfe", "hilfe"),
            ("Beenden", "Spiel verlassen", "quit")
        ]

        for cmd, desc, example in commands:
            help_table.add_row(cmd, desc, example)

        self.console.print(help_table)

    def display_combat_ui(self, player: 'PlayerState', npc: 'NPCPlayerState'):
        """Spezielle UI für Kampfszenen"""
        combat_panel = Panel(
            f"⚔️ **KAMPF!** ⚔️\n\n"
            f"Du kämpfst gegen: {npc.name}\n"
            f"Ort: {player.location.callnames[0]}",
            title="[bold red]KAMPF[/bold red]",
            border_style="red"
        )
        self.console.print(combat_panel)

    def display_typing_effect(self, text: str, delay: float = 0.03):
        """Zeige Text mit Schreibmaschinen-Effekt"""
        for char in text:
            self.console.print(char, end="")
            time.sleep(delay)
        self.console.print()  # Neue Zeile

# Verbesserte UI mit flexiblem Ausgabebereich
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.columns import Columns
from collections import deque
import textwrap


class EnhancedUI:
    def __init__(self):
        self.console = Console()
        self.action_history = deque(maxlen=50)  # Behalte die letzten 50 Aktionen
        self.current_layout_mode = "detailed"  # "compact", "detailed", "history"

    def add_action_to_history(self, action: str, action_type: str = "action"):
        """Füge eine Aktion zur Historie hinzu"""
        self.action_history.append({
            'text': action,
            'type': action_type,
            'timestamp': len(self.action_history)
        })

    def display_status_panel(self, player: 'PlayerState') -> Panel:
        """Kompakter Status-Panel"""
        status_lines = []

        # Durst mit Balken
        thirst_percent = (player.thirst_counter / 40) * 100
        thirst_bar = "█" * int(thirst_percent / 10) + "░" * (10 - int(thirst_percent / 10))
        thirst_color = "green" if thirst_percent > 50 else "yellow" if thirst_percent > 25 else "red"
        status_lines.append(f"🚰 [{thirst_color}]{thirst_bar}[/{thirst_color}] {player.thirst_counter}/40")

        # Ort
        status_lines.append(f"📍 {player.location.callnames[0]}")

        # Inventar (kompakt)
        if player.inventory:
            items = [obj.callnames[0] for obj in player.inventory[:3]]  # Nur erste 3
            if len(player.inventory) > 3:
                items.append(f"(+{len(player.inventory) - 3})")
            status_lines.append(f"🎒 {', '.join(items)}")
        else:
            status_lines.append("🎒 leer")

        return Panel(
            "\n".join(status_lines),
            title=f"[bold]{player.name}[/bold]",
            border_style="blue",
            padding=(0, 1)
        )

    def display_action_output(self, recent_actions: list = None) -> Panel:
        """Zeige Aktionsausgabe mit automatischer Größenanpassung"""
        if not recent_actions:
            recent_actions = list(self.action_history)[-5:]  # Letzte 5 Aktionen

        if not recent_actions:
            return Panel("Noch keine Aktionen ausgeführt.",
                         title="[bold]Spielverlauf[/bold]",
                         border_style="cyan")

        content_lines = []
        for i, action in enumerate(recent_actions):
            # Formatiere jede Aktion
            action_text = action['text'] if isinstance(action, dict) else str(action)

            # Umbruch für lange Zeilen
            wrapped_lines = textwrap.wrap(action_text, width=60,
                                          subsequent_indent="  ")

            if len(recent_actions) > 1:
                # Füge Separator zwischen Aktionen hinzu
                if i > 0:
                    content_lines.append("─" * 40)
                content_lines.extend(wrapped_lines)
            else:
                content_lines.extend(wrapped_lines)

        return Panel(
            "\n".join(content_lines),
            title="[bold]Spielverlauf[/bold]",
            border_style="cyan",
            expand=True  # Wichtig: Panel kann sich ausdehnen
        )

    def display_location_info(self, player: 'PlayerState', gs: 'GameState') -> Panel:
        """Kompakte Umgebungsinfo"""
        content = []

        # Objekte (kompakt)
        visible_objects = [obj for obj in player.location.place_objects if not obj.hidden]
        if visible_objects:
            obj_names = [obj.callnames[0] for obj in visible_objects[:4]]
            if len(visible_objects) > 4:
                obj_names.append(f"(+{len(visible_objects) - 4})")
            content.append(f"📦 {', '.join(obj_names)}")

        # Wege (kompakt)
        available_ways = [way for way in player.location.ways
                          if way.visible and way.obstruction_check(gs) == "Free"]
        if available_ways:
            way_names = [way.destination.callnames[0] for way in available_ways[:3]]
            if len(available_ways) > 3:
                way_names.append(f"(+{len(available_ways) - 3})")
            content.append(f"🚶 {', '.join(way_names)}")

        return Panel(
            "\n".join(content),
            title="[bold]Umgebung[/bold]",
            border_style="green",
            padding=(0, 1)
        )

    def display_game_screen_v2(self, player: 'PlayerState', gs: 'GameState',
                               last_actions: list = None, layout_mode: str = None):
        """Verbesserte Spielanzeige mit flexiblem Layout"""
        if layout_mode:
            self.current_layout_mode = layout_mode

        layout = Layout()

        if self.current_layout_mode == "compact":
            # Kompaktes Layout: Mehr Platz für Ausgabe
            layout.split_column(
                Layout(name="header", size=1),
                Layout(name="main"),
                Layout(name="actions", ratio=1)  # Flexibel!
            )

            layout["main"].split_row(
                Layout(name="scene", ratio=3),
                Layout(name="sidebar", ratio=1)
            )

            # Sidebar mit kompakten Infos
            layout["sidebar"].split_column(
                Layout(self.display_status_panel(player)),
                Layout(self.display_location_info(player, gs))
            )

        elif self.current_layout_mode == "detailed":
            # Detailliertes Layout
            layout.split_column(
                Layout(name="header", size=1),
                Layout(name="main", ratio=2),
                Layout(name="actions", ratio=1)  # Flexibel, aber weniger Platz
            )

            layout["main"].split_row(
                Layout(name="scene", ratio=2),
                Layout(name="sidebar", ratio=1)
            )

            layout["sidebar"].split_column(
                Layout(self.display_status_panel(player)),
                Layout(self.display_location_info(player, gs))
            )

        elif self.current_layout_mode == "history":
            # Verlaufs-Layout: Maximaler Platz für Aktionen
            layout.split_column(
                Layout(name="header", size=1),
                Layout(name="status_bar", size=3),
                Layout(name="actions")  # Nimmt den Rest!
            )

            # Kompakte Status-Zeile
            status_columns = Columns([
                self.display_status_panel(player),
                self.display_location_info(player, gs)
            ], equal=True)
            layout["status_bar"].update(status_columns)

        # Header (immer gleich)
        layout["header"].update(
            f"🏜️ Wüsten-Adventure - Runde {gs.time} | "
            f"Layout: {self.current_layout_mode} | "
            f"[dim]Strg+L: Layout wechseln[/dim]"
        )

        # Szene (nur wenn nicht history-Modus)
        if self.current_layout_mode != "history":
            scene_description = gs.llm.narrate(gs, player) if gs.llm else "Beschreibung nicht verfügbar"
            layout["scene"].update(Panel(
                scene_description,
                title="[bold]Aktuelle Szene[/bold]",
                border_style="yellow"
            ))

        # Aktionsausgabe (das Wichtigste!)
        actions_to_show = last_actions or list(self.action_history)[-10:]
        layout["actions"].update(self.display_action_output(actions_to_show))

        self.console.clear()
        self.console.print(layout)

    def toggle_layout_mode(self):
        """Wechsle zwischen Layout-Modi"""
        modes = ["compact", "detailed", "history"]
        current_index = modes.index(self.current_layout_mode)
        self.current_layout_mode = modes[(current_index + 1) % len(modes)]
        return f"Layout gewechselt zu: {self.current_layout_mode}"

    def display_long_text(self, text: str, title: str = "Information"):
        """Zeige langen Text in scrollbarem Panel"""
        # Für sehr lange Texte - separates Panel
        wrapped_text = textwrap.fill(text, width=80)

        panel = Panel(
            wrapped_text,
            title=f"[bold]{title}[/bold]",
            border_style="magenta",
            expand=True
        )

        self.console.clear()
        self.console.print(panel)
        self.console.input("\n[dim]Drücke Enter um fortzufahren...[/dim]")

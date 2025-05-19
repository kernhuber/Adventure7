#from Adventure6 import places, state, items, gehe, nimm, untersuche, anwenden, umsehen, inventory
# from Door import Door
# from InteractLLM import PromptGenerator
#

class SysTest:
    def __init__(self):
        pass





    def test6(self):
        print("🎮 Starte Adventure-Simulator (manuell ohne LLM)")
        from GameState import init_game
        game = init_game()
        if not game.players:
            print("❌ Keine Spieler vorhanden.")
            return
        player = game.players[0]

        while True:
            current_room = player.location
            print("\n📍 Du bist in:", current_room.name)
            print(current_room.description.strip())

            if current_room.place_objects:
                print("\n🧸 Gegenstände hier:")
                for obj in current_room.place_objects:
                    print(f"- 📦 {obj.name}")
            else:
                print("\n🧸 Keine Gegenstände hier.")

            if current_room.ways:
                print("\n🚪 Wege:")
                for way in current_room.ways:
                    status = "versperrt" if way.obstruction_check(game) else "offen"
                    print(f" - {way.text_direction.capitalize()}: {status} ➔ {way.destination.name}")
            else:
                print("\n🚪 Keine Ausgänge.")

            user_input = input("\n🧍 Was tust du? ➔ ").strip().lower()
            if not user_input:
                continue
            parts = user_input.split()
            command = parts[0]
            args = parts[1:]

            if command == "gehe" and len(args) == 1:
                richtung = args[0]
                found = False
                for way in current_room.ways:
                    if way.text_direction == richtung:
                        found = True
                        if way.obstruction_check(game):
                            print("🚫 Der Weg ist versperrt.")
                        else:
                            player.location = way.destination
                            print("🚶‍♂️ Du gehst", richtung)
                        break
                if not found:
                    print("❓ In diese Richtung gibt es keinen Weg.")
            elif command in ["ende", "quit", "exit"]:
                print("🏁 Spiel beendet.")
                break
            else:
                print("❓ Unbekannter Befehl oder noch nicht implementiert.")



st = SysTest()
st.test6()
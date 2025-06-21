"""
Minigames for situations where Dog and Players have to fight
"""
import random

from Utils import tw_print
from NPCPlayerState import DogFight



class MiniGames:
    def __init__(self):
        self.glist = [self.circle_fight,self.sum_fight, self.odd_even_fight, self.close_fight]

    def fight(self):
        g = random.choice(self.glist)
        return g()

    def circle_fight(self) -> DogFight:
        """
        Minigame: does number provided by player beat number provided by dog?
        * both numbers one from 1,2,3,4
        * 4 beats 3, 3 beats 2, 2 beats 1, 1 beats 4
        * All other combinations -> TIE
        * Check if dog has won -> return WON
        * Check if player has lost -> return LOST
        :param:
        :return: DogFight state (WON, LOST, TIE) from Dog's perspective
        """
        import random
        d = random.randint(1,4)


        print("****************************")
        print("***  Kampf mit dem Hund  ***")
        print("****************************\n\n")
        print("Regeln:  4 schlägt 3, 3 schlägt 2, 2 schlägt 1, 1 schlägt 4 ... sonst: Unentschieden.\n\n")

        inp = ""
        while inp not in ["1","2","3","4"]:
            inp = input("Gib eine Zahl aus 1,2,3,4 ein: ")
        p = int(inp.strip())
        tw_print(f"Du hast: {p}")
        tw_print(f"Hund hat: {d}")
        #
        # Modulo calc: scale 1,2,3 to 0,1,2
        #
        d=d-1
        p=p-1
        if (d+1)%4 == p:
            tw_print("***Der Hund verliert den Kampf!***")
            return DogFight.LOST
        if (p+1)%4 == d:
            tw_print("***Du verlierst den Kampf gegen den Hund!***")
            return DogFight.WON
        tw_print("***Unentschieden!***")
        return DogFight.TIE

    def sum_fight(self) -> DogFight:
        """
        Given are 10 numbers and a value "reach" the system randomly creates out of them.

        The Goal of the game is to reach the "reach" value by mutually picking a value from
        the remaining values of the inital list and throw it on a "stack" (sum).

        A player who exactly reaches "reach" wins the game

        A player who places the last possible number, wins the game (last possible number:
        any other from the numbers left would overstep the "reach" limit)

        :return: DogFight
        """

        stones = []
        stack=[]
        stack_sum = 0
        print("""
################################        
###   Spiel um Dein Leben!   ###
################################

Gegeben eine Liste von zehn Zahlen und eine Zielzahl.

Die Spieler wählen immer abwechselnd eine Zahl aus der Liste und addieren sie
iauf eine laufende Summe, die anfänglich bei 0 startet; die Zahl wird aus der 
Liste entfernt.

- Wenn ein Spieler die Zielzahl genau erreicht, hat er das Spiel gewonnen.
- Wenn ein Spieler die Zahl überschreitet, hat er verloren.
  --> Wenn nach dem Zug eines Spielers nur noch solche Zahlen übrig bleiben,
      die zu einem überschreiten der Zielsumme führen würden, hat der andere
      Spieler verloren
        """)

        for i in range(0,10):
            stones.append(random.randint(1,10))
        z=0
        max = 0
        for i in stones:
            z = z+i
            if i> max:
                max = i
        reach = 0
        while reach < max:
            reach = random.randint(1,z)
        tw_print("\n\nMünzwurf: wer fängt an - Spieler oder Hund?")
        whosnext = random.choice([0,1])
        if whosnext == 0:
            tw_print("***Dog fängt an!***\n\n")
        else:
            tw_print("***Spieler fängt an!***\n\n")
        while True:
            tw_print(f"{'-'*40}")
            print(f"Verfügbare Zahlen: {stones}")
            print(f"Ziel: {reach}")
            print(f"Stapel: {stack_sum}")
            print("\n\n")
            if whosnext == 0:
                #
                # Dog draws:
                #

                # i = random.randrange(0,len(stones))
                # stack.append((stones[i],"Dog"))
                # stack_sum += stones[i]
                # tw_print(f"***Dog wählt: {stones[i]}")


                i = 0
                for t in stones:
                    if t+stack_sum == reach:
                        i=t
                        break
                    elif t+stack_sum < reach:
                        if t>i:
                            i = t

                stack.append((i,"Dog"))
                stack_sum += i
                tw_print(f"***Dog wählt: {i}")
                if stack_sum == reach:
                    tw_print("Dog hat den Zielwert genau getroffen und ***gewinnt*** damit!")
                    return DogFight.WON
                if stack_sum > reach:
                    tw_print("Dog hat am Zielwert vorbeigeschossen und ***verliert*** das Spiel!")
                    return DogFight.LOST
                stones.remove(i)
            else:
                #
                # Player draws
                #
                inp = 9999
                while inp not in stones:
                    try:
                        inp = int(input("Wähle eine Zahl aus den verfügbaren Zahlen: "))
                    except ValueError:
                        print("Ungültige Eingabe. Bitte eine ganze Zahl eingeben.")
                        inp = 9999
                stack.append((inp,"Spieler"))
                stack_sum += inp
                if stack_sum == reach:
                    tw_print("Spieler hat den Zielwert genau getroffen - ***Dog verliert*** das Spiel")
                    return DogFight.LOST
                if stack_sum > reach:
                    tw_print("Spieler hat dam Zielwert vorbeigeschossen und verliert das Spiel. ***Dog gewinnt!***")
                    return DogFight.WON
                stones.remove(inp)




            #
            # Check if it is still possible for any player to continue the game:
            #
            lastone = True
            for i in stones:
                if stack_sum+i <= reach:
                    lastone = False
                    break

            #
            # lastone: The game is over
            #
            if lastone:
                tw_print(f"\n***Game over*** - jede weitere Wahl aus  {stones} würde {reach} überschreiten.")
                if whosnext == 0:
                    tw_print("***--> Dog hat gewonnen!***")
                    return DogFight.WON
                else:
                    tw_print("***--> Dog hat verloren!***")
                    return DogFight.LOST

            whosnext = (whosnext + 1) % 2

    def odd_even_fight(self) -> DogFight:
        """
        Mini-Spiel: Odd or Even – Summe entscheidet.
        - Beide Spieler (Mensch & Hund) wählen eine Zahl zwischen 1 und 5.
        - Ist die Summe gerade, gewinnt der Hund.
        - Ist die Summe ungerade, gewinnt der Spieler.
        - Sonderregel: Wenn beide dieselbe Zahl wählen, endet das Spiel unentschieden.
        """
        tw_print("""
    ## 🃏 Zahlenduell – Odd or Even ##
    - Beide wählen eine Zahl von 1 bis 5.
    - Gerade Summe: Der Hund gewinnt.
    - Ungerade Summe: Der Spieler gewinnt.
    - Gleiche Zahl: Unentschieden!
    """)

        dog_choice = random.randint(1, 5)
        player_input = None
        while player_input not in ["1", "2", "3", "4", "5"]:
            player_input = input("Wähle eine Zahl zwischen 1 und 5: ").strip()
        player_choice = int(player_input)

        tw_print(f"Du hast {player_choice} gewählt.")
        tw_print(f"Der Hund hat {dog_choice} gewählt.")

        if player_choice == dog_choice:
            tw_print("***Beide haben dieselbe Zahl gewählt! Es steht unentschieden.***")
            return DogFight.TIE

        total = player_choice + dog_choice
        if total % 2 == 0:
            tw_print("***Die Summe ist gerade – der Hund gewinnt!***")
            return DogFight.WON
        else:
            tw_print("***Die Summe ist ungerade – du gewinnst!***")
            return DogFight.LOST

    def close_fight(selfs) -> DogFight:
        tw_print("""
        ## 🃏 Wer ist am nächsten dran? ##
        - Das System erstellt eine zufällige geheime Zahl zwischen 1 und 100
        - Beide wählen eine Zahl zwischen 1 bis 100.
        - Es gewinnt derjenige, der am nächsten an der geheimen Zahl liegt.
        - Gleiche Zahl: Unentschieden!
        """)

        secret = random.randint(1,100)
        dog_choice = random.randint(1,100)
        plr_choice = -1
        while plr_choice < 1 or plr_choice > 100:
            try:
                plr_choice = int(input("Bitte eine Zahl zwischen 1 und 100 (inklusive) wählen: ").strip())
            except ValueError():
                print("Das war gar keine Zahl!")
                plr_choice = -1
        print(f"Der Hund hat {dog_choice} gewählt.")
        print(f"Das System hat {secret} gewürfelt")
        dd = abs(secret-dog_choice)
        dp = abs(secret-plr_choice)
        if plr_choice == dog_choice:
            print("Gleiche Zahl - unentschieden!")
            return DogFight.TIE
        elif dp == dd:
            print("Gleicher Abstand! - unentschieden")
            return DogFight.TIE
        elif dp > dd:
            print(f"Der Hund ist näher dran (Abstand {dd}). Dein Abstand ist {dp}. Der Hund gewinnt!")
            return DogFight.WON
        else:
            print(f"Du bist näher dran (Abstand {dp}). Abstand des Hundes ist {dd}. Der Hund verliert!")
            return DogFight.LOST
g = MiniGames()
print(g.fight())
from random import uniform
from time import sleep
from .DelugeAPI import *

# class BotMode:
#     bot: DelugeBot
#     def __init__(self):

#     def run(self) -> None:
#         pass

# class LevelUpMode(BotMode):
#     def run():

class DelugeBot:
    def __init__(self, phpsessid: str, password: str, username: str = None) -> None:
        if not phpsessid:
            raise Exception("No session cookie provided to bot.")

        self.cookie = phpsessid
        self.http = DelugeAPIClient(phpsessid, password, username)

    def levelFarmBattle(self, poke_type: str):
        user = f"s-{poke_type}"

        battle = self.http.startUserBattle(user)

        curr_poke_no = 5 

        # Basic battle strategy, go through every poke in order
        while not battle.game_over:
            self.http.doBattleMove(BattleMove(MoveType.POKE_SELECT_MOVE, poke_select=curr_poke_no))

            sleep(2)

            while not battle.current_duel_over: 
                self.http.doBattleMove(BattleMove(MoveType.ATTACK_MOVE, selected_attack=2))
                sleep(uniform(1, 2))
            
            if battle.isPokeFainted(curr_poke_no):
                curr_poke_no += 1

                if curr_poke_no > 6:
                    print("Battle over")
                    break
        
        results = self.http.getBattleResults()
        print (f"Winner is {battle.winner}. Earnings: {results['money']}, Exp : {results['exp']}")
    def openMap():
        pass

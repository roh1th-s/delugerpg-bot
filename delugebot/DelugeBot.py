from random import uniform, randrange
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

    def catchPoke(self, poke, catch_token: str, catch_poke_no : int, catch_attack_no: int):
        wild_battle = self.http.startWildBattle(poke["url"], poke["secret"], catch_token)

        curr_poke_no = catch_poke_no 

        # can't put them to sleep if they're metallic (unless catching pokemon is shadow type)
        # pokeball = poke["name"].lower().find("metallic") == -1 and 'greatball' or 'masterball'
        is_legend = poke["legend"] != 0
        pokeball =  is_legend and 'masterball' or 'greatball'

        while not wild_battle.game_over:
            self.http.doBattleMove(BattleMove(MoveType.POKE_SELECT_MOVE, selected_poke=curr_poke_no))
            sleep(uniform(1, 2))

            while not (wild_battle.current_duel_over or wild_battle.game_over):
                self.http.doBattleMove(BattleMove(MoveType.ATTACK_MOVE, selected_attack=catch_attack_no))  # hypnosis
                sleep(uniform(1, 2))

                while (is_legend or wild_battle.opponent.current_poke.current_ailment == "slp") and (
                        not wild_battle.game_over):
                    self.http.doBattleMove(BattleMove(MoveType.ITEM_MOVE, selected_item=pokeball))
                    sleep(uniform(1, 2))

            if wild_battle.isPokeFainted(curr_poke_no):
                curr_poke_no += 1

                if wild_battle.player.pokes_left <= 0:
                    print("Battle over")
                    break

                if curr_poke_no > 6:
                    curr_poke_no = 1

        results = self.http.getBattleResults()

        wild_poke = wild_battle.opponent.team[0]

        if results.get("cancelled"):
            print("Battle was cancelled. [Most probably due to a timeout / invalid creds]")
        elif results.get("capture_failed"):
            print(f"{wild_poke.name} could not be captured.")
        elif results.get("defeat"):
            print(f"Battle was lost. Winner is {wild_poke.name}")
        else:
            print(
                f"Caught {results['poke_caught']} with stats {results['stats']}"
            )
            return True

        return False

    def startPokemonHunt(self, map_name: str, **kwargs):
        limit = kwargs.get("limit") or 1
        legends_only = kwargs.get("legends_only") or False
        catch_poke_no = kwargs.get("catch_poke") or 1
        catch_attack_no = kwargs.get("attack_no") or 1

        directions = ["n", "s", "e", "w", "ne", "nw", "se", "sw"]

        moves_before_cooldown = 100

        while limit > 0:
            if moves_before_cooldown <= 0:
                sleep(50)
                moves_before_cooldown = 100

            rand_direction = directions[randrange(0, len(directions))]
            result = self.http.moveInMap(map_name, rand_direction)
            
            if result == []:
                # cannot move in this direction
                continue
            
            moves_before_cooldown -= 1
            
            debug_coords = result.get("debug")
            if debug_coords:
                print(rand_direction, debug_coords[0], debug_coords[1], end="\r")
            else:
                captcha_path = result.get('goto')
                if captcha_path:
                    self.http.get(f"{Urls.base_url}{captcha_path}")
                else:
                    print("DEBUG : ", result)

            poke = result.get("poke")
            if poke:
                if legends_only and poke["legend"] == 0:
                    # If we're only searching for legends and the poke is not a legend, continue
                    sleep(uniform(2, 5))
                    continue

                print(f"Found {poke['name']}")

                if (not legends_only) and poke["name"].lower().find("metallic") != -1:
                    print("It is metallic. Skipping...")
                elif (not legends_only) and result["haveit"] != "none":
                    print("Already have it. Skipping...")
                else:
                    if self.catchPoke(poke, result["catch_token"], catch_poke_no, catch_attack_no):
                        print()
                        limit -= 1

            # if we move onto a new map
            newmap = result.get("newmap")
            if newmap:
                map_name = newmap

            sleep(uniform(2, 5))

    def basicBattleStrategy(self, battle: Battle, start_poke_no: int = None, attack_no: int = 2):
        curr_poke_no = start_poke_no or 1

        # Basic battle strategy, go through every poke in order
        while not battle.game_over:
            self.http.doBattleMove(BattleMove(
                MoveType.POKE_SELECT_MOVE, selected_poke=curr_poke_no))

            sleep(uniform(1, 2))

            while not (battle.current_duel_over or battle.game_over):
                self.http.doBattleMove(BattleMove(MoveType.ATTACK_MOVE, selected_attack=attack_no))
                sleep(uniform(1, 2))

            if battle.isPokeFainted(curr_poke_no):
                curr_poke_no += 1

                if battle.player.pokes_left <= 0:
                    print("Battle over")
                    break

                if curr_poke_no > 6:
                    curr_poke_no = 1

    def levelFarmBattle(self, poke_type: str, start_poke_no: int = None, attack_no: int = None):
        user = f"s-{poke_type}"

        battle = self.http.startUserBattle(user)

        self.basicBattleStrategy(battle, start_poke_no, attack_no)

        results = self.http.getBattleResults()

        if results.get("cancelled"):
            print("Battle was cancelled. [Most probably due to a timeout / invalid creds]")
        elif results.get("defeat"):
            print(f"Battle was lost. Winner is {battle.winner.name}")
        else:
            print(
                f"Winner is {battle.winner.name}. Earnings: {results['money']}, Exp : {results['exp']}")
    
    def defeatGym(self, gym_id):
        try:
            gym_battle = self.http.startGymBattle(gym_id)
        except GymNotFoundException as e:
            print(e)
            return False
        
        self.basicBattleStrategy(gym_battle)

        results = self.http.getBattleResults()

        if results.get("cancelled"):
            print("Battle was cancelled. [Most probably due to a timeout / invalid creds]")
        elif results.get("defeat"):
            print(f"Battle was lost. Winner is {gym_battle.winner.name}")
        else:
            print(
                f"Defeated {gym_battle.opponent.name}. Earnings: {results['money']}, Exp : {results['exp']}")             

        return True

    def defeatAllGyms(self, region_no: int = None):
        start_no = region_no or 1
        end_no = region_no and region_no + 1 or 9

        for region_no in range(start_no, end_no):
            base_no = region_no * 100

            # max gyms in a region is 13

            # normal gym leaders
            for gym_no in range(1, 14):
                success = self.defeatGym(base_no + gym_no)
                sleep(10)
                print()
                if not success:
                    break
            
            # elite 4
            for el4 in range(51, 55):
                success = self.defeatGym(base_no + el4)
                sleep(10)
                print()
                if not success:
                    break
    
    def defeatGymsWithCodes(self, codes: list[int]):
        for code in codes:
            self.defeatGym(code)
            sleep(10)
            print()
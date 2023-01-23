import requests
import os
import re
from .constants import Urls
from .BattleMove import *
from .Battle import *

class DelugeAPIClient:
    def __init__(self, sessCookie: str):
        if not sessCookie or sessCookie == "":
            raise Exception("Session cookie not provided.")

        session = requests.Session()
        session.cookies.set("PHPSESSID", sessCookie)
        session.headers.update({
            "User-Agent": os.getenv("USER_AGENT")
        })

        self.session: requests.Session = session

        self.current_battle = None

    def get(self, url, *kwargs) -> requests.Response:
        r"""Wrapper around requests.Session#get()

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """
        res = self.session.get(url, *kwargs)
        # TODO: check for timeouts
        # req gets redirected to https://www.delugerpg.com/login/timeout
        # login with https://www.delugerpg.com/login/validate
        # request body (form data)
        # {
        #     "username": "",
        #     "password": "",
        #     "DBhYWU": "jg2NjM2MzU", ( found in timeout page )
        #     "Login": "Login"
        # }

        # two codes need to passed with login/validate, found on login/timeout page
        # also have to clean up current battle if this happens while its going on

        return res

    def post(self, url, data=None, json=None, *kwargs) -> requests.Response:
        r"""Wrapper around requests.Session#post()

        :param url: URL for the new :class:`Request` object.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json to send in the body of the :class:`Request`.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """
        res = self.session.post(url, data, json, *kwargs)
        # check for timeouts
        return res

    def startUserBattle(self, user: str) -> Battle:
        res = self.get(f"{Urls.user_battle}/u/{user}")

        if res.text.find("No such User.") != -1:
            raise Exception("No such user found!")

        # create a battle object from the html with necessary metadata
        self.current_battle = Battle(BattleType.COMP_BATTLE, self).fromHtml(res.text)

        print("Battle succesfully created")

        return self.current_battle

    def getMapHashes(self, mapName: str):
        response = self.get(f"{Urls.map}/{mapName}")
        results = re.search(
            r"<script>\s*var\s*m_h1\s=\s*['|\"](.+)['|\"]\s*,m_h2\s*=\s*['|\"](.+)['|\"]\s*,\s*m_h3\s*=\s*['|\"](.+)['|\"]\s*;\s*</script>",
            response.text)

        if not results:
            raise Exception("Couldn't find map hashes in html")

        map_hash1 = results.group(1)
        map_hash2 = results.group(2)
        map_hash3 = results.group(3)

        if not (map_hash1 and map_hash2 and map_hash3):
            raise Exception("Couldn't find all the required map hashes")

        return [map_hash1, map_hash2, map_hash3]

    def moveInMap(self, mapName: str, dir: str):
        hashes = self.getMapHashes(mapName)
        response = self.post(f"{Urls.map_update_ajax}/{hashes[2]}/{hashes[0]}", {
            "direction": dir,
            "maphash": hashes[1],
            "mhx": os.getenv("MHX")
        })
        return response.json()

    def startWildBattle(
            self, pokeName: str, level: int, poke_secret: str, catch_secret: str) -> Battle:
        """Start a wild battle with a pokemon found on a map. This requires two secrets, both
            of which are accquired when finding a pokemon on any map.
        """

        response = self.post(f"{Urls.catch_poke}/{pokeName}/{level}", {
            "do": "catch_pokemon",
            "secret": poke_secret,
            f"catch_{catch_secret}": "Try to Catch It"
        })

        if response.status_code == 200:
            wild_battle = Battle(BattleType.WILD_BATTLE, self).fromHtml(response.text)
            print(f"Wild battle started with {pokeName}, level : {level}")

            return wild_battle
        else:
            raise Exception(f"Error starting wild battle with {pokeName}, level : {level}")


    def doBattleMove(self, move: BattleMove):
        res = None
        battle = self.current_battle
        if battle.move_count == 0:
            # if this is the first move
            res = self.post(
                Urls.user_battle if battle.type == BattleType.COMP_BATTLE else Urls.catch_poke,
                {
                    "pokeselect": move.selectedPokemon,
                    "do": "showattacks",
                }
            )

            if (res.status_code == 200):
                result = re.search(
                    r".*<input\s*type=\"hidden\"\s*name=\"battletoken\"\s*value=\"(.+)\"\s*/?>.*",
                    res.text)

                if not result:
                    raise Exception("Battle token not found")

                battle_token = result.group(1)

                if battle_token:
                    battle.battle_token = battle_token
                    print(f"First move : Poke is {self.current_battle.player.team[move.selectedPokemon - 1].name} ")
                else:
                    raise Exception("Battle token not found")
        else:
            json = {
                "do": move.do,
                "battletoken": battle.battle_token
            }
            if move.type == MoveType.ATTACK_MOVE:
                json["selected"] = move.selectedAttack
            elif move.type == MoveType.POKE_SELECT_MOVE:
                json["pokeselect"] = move.selectedPokemon

            res = self.post(
                Urls.comp_battle_ajax if battle.type == BattleType.COMP_BATTLE else Urls.wild_battle_ajax,
                json
            )

            if move.type == MoveType.ATTACK_MOVE:
                print(f"Doing attack {move.selectedAttack}")
            elif move.type == MoveType.POKE_SELECT_MOVE:
                print(f"Selected pokemon {move.selectedPokemon}")

        battle.move_count += 1;
        battle.update(res)
    
    def getBattleResults(self):
        battle = self.current_battle
        
        if not battle.game_over:
            print("Battle is not over!")
            return

        res = self.post(
            Urls.comp_battle_ajax if battle.type == BattleType.COMP_BATTLE else Urls.wild_battle_ajax,
            {
                "do" : "select"
            }
        )

        return battle.parseResults(res.text)
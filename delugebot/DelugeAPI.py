import requests
import os
import re
import json
from sys import argv
from bs4 import BeautifulSoup
from .constants import Urls
from .BattleMove import *
from .Battle import *

class GymNotFoundException(Exception):
    pass

class DelugeAPIClient:
    def __init__(self, sessCookie: str, password: str, username: str = None):
        if not sessCookie or sessCookie == "":
            raise Exception("Session cookie not provided.")

        session = requests.Session()
        session.cookies.set("PHPSESSID", sessCookie)
        session.headers.update({
            "User-Agent": os.getenv("USER_AGENT")
        })

        self.session: requests.Session = session

        self.username = username or self.get_username()
        self.password = password

        self.current_battle = None

        self.map_hash_cache = {}

    def get_username(self):
        res = self.get(Urls.profile)

        soup = BeautifulSoup(res.text, 'html.parser')

        info_box = soup.find("div", class_="infobox")

        # should be first proffield div (that contains username)
        username_field = info_box.find("div", class_="proffield")
        name = username_field.h4.text

        return name

    def should_revalidate(self, res: requests.Response):
        soup = BeautifulSoup(res.text, 'html.parser')
        meta_equiv = soup.select_one('meta[http-equiv="refresh"]')

        is_captcha = False

        if meta_equiv:
            content = meta_equiv["content"]
            if content.find(Urls.captcha) != -1:
                is_captcha = True

        if res.url.find(Urls.captcha) != -1:
            is_captcha = True

        if is_captcha:
            print("Encountered captcha.")
            self.logout()
            
        return res.url.startswith(Urls.timeout) or is_captcha or (not res.ok)

    def revalidate_cookie(self):
        print("Attempting to revalidate cookie...")
        # Request the login/timeout page, which contains necessary tokens for login
        timeout_res = self.session.get(Urls.timeout)

        soup = BeautifulSoup(timeout_res.text, 'html.parser')
        login_form = soup.find(id="loginformform")
        hidden_input = login_form.select_one('input[type="hidden"]')

        name = hidden_input.attrs["name"]
        value = hidden_input.attrs["value"]

        if not (hasattr(self, 'username') or hasattr(self, 'password')):
            raise Exception(
                "Username / Password could not be found. Session cookie is probably invalid.")

        # calling the login/validate endpoint with credentials
        res = self.session.post(Urls.login_validate, {
            "username": f"{self.username}",
            "password": f"{self.password}",
            f"{name}": f"{value}",
            "Login": "Login"
        })

        # response is an intermediate loading page with a redirect link
        # also sets a token which is checked later on presumably
        soup = BeautifulSoup(res.text, 'html.parser')
        loggin_in_div = soup.find(id="loggingin")

        # looks roughly like /home/ad3ad8ac93ceabb2c/17527905
        relative_href = loggin_in_div.select_one("a").attrs["href"]

        # requesting the home page with the extra stuff specified in the redirect link
        # cookie should be revalidated after this
        res = self.session.get(f"{Urls.base_url}{relative_href}")

        if res.ok:
            print("Revalidated cookie successfully. Proceeding.")
        else:
            raise Exception("Unable to revalidate cookie!")
    
    def clean_up(self):
        if self.current_battle:
            self.current_battle.terminate(invalidated=True)

    def logout(self):
        self.get(Urls.logout_ajax)
        print("Logged out.")

    def get(self, url, *kwargs) -> requests.Response:
        r"""Wrapper around requests.Session#get()

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """
        res = self.session.get(url, *kwargs)

        if self.should_revalidate(res):
            self.revalidate_cookie()
            self.clean_up()
            res = self.session.get(url, *kwargs)

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

        if self.should_revalidate(res):
            self.revalidate_cookie()
            self.clean_up()
            res = self.session.post(url, data, json, *kwargs)

        return res

    def getMapHashes(self, mapName: str):
        response = self.get(f"{Urls.map}/{mapName}")
        results = re.search(
            r"<script>\s*var\s*m_h1\s=\s*['|\"](.+)['|\"]\s*,m_h2\s*=\s*['|\"](.+)['|\"]\s*,\s*m_h3\s*=\s*['|\"](.+)['|\"]\s*;\s*</script>",
            response.text)

        if not results:
            if len(argv) >= 2:
                if argv[1] == "-debug":
                    with open("./experiments/test.html", "w") as f:
                        f.write(response.text)

            raise Exception("Couldn't find map hashes in html")

        map_hash1 = results.group(1)
        map_hash2 = results.group(2)
        map_hash3 = results.group(3)

        if not (map_hash1 and map_hash2 and map_hash3):
            raise Exception("Couldn't find all the required map hashes")

        return [map_hash1, map_hash2, map_hash3]

    def moveInMap(self, mapName: str, dir: str) -> list | dict:
        hashes = self.map_hash_cache.get(mapName)
        if not hashes:
            hashes = self.getMapHashes(mapName)
            self.map_hash_cache[mapName] = hashes

        res = self.post(f"{Urls.map_update_ajax}/{hashes[2]}/{hashes[0]}", {
            "direction": dir,
            "maphash": hashes[1],
            "mhx": os.getenv("MHX")
        })
        return json.loads(res.text)

    def startUserBattle(self, user: str) -> Battle:
        res = self.get(f"{Urls.comp_battle}/u/{user}")

        if res.text.find("No such User.") != -1:
            raise Exception("No such user found!")

        # create a battle object from the html with necessary metadata
        self.current_battle = Battle(BattleType.COMP_BATTLE, self).fromHtml(res.text)

        print("Battle succesfully created")

        return self.current_battle

    def startGymBattle(self, gym_id: int) -> Battle:
        """Start a gym battle
        """

        response = self.get(f"{Urls.gym_battle}/{gym_id}")

        if response.text.find("No such") != -1:
            raise GymNotFoundException("Invalid gym url")
        
        self.current_battle = Battle(BattleType.GYM_BATTLE, self).fromHtml(response.text)

        print("Gym battle started")

        return self.current_battle

    def startWildBattle(
            self, poke_catch_url: str, poke_secret: str, catch_secret: str) -> Battle:
        """Start a wild battle with a pokemon found on a map. This requires two secrets, both
            of which are accquired when finding a pokemon on any map.
        """

        response = self.post(f"{Urls.catch_poke}/{poke_catch_url}", {
            "do": "catch_pokemon",
            "secret": poke_secret,
            f"catch_{catch_secret}": "Try to Catch It"
        })

        self.current_battle = Battle(BattleType.WILD_BATTLE, self).fromHtml(response.text)
        poke = self.current_battle.opponent.team[0]
        print(f"Wild battle started with {poke.name}, level : {poke.level}")

        return self.current_battle

    def doBattleMove(self, move: BattleMove):
        res = None
        battle = self.current_battle
        if battle.move_count == 0:
            # if this is the first move
            res = self.post(
                battle.getMoveUrl(),
                move.toDict()
            )

            if self.current_battle.invalidated:
                # Don't do anything more if the battle has been terminated
                return

            result = re.search(
                r".*<input\s*type=\"hidden\"\s*name=\"battletoken\"\s*value=\"(.+)\"\s*/?>.*",
                res.text)

            if not result:
                raise Exception("Battle token not found")

            battle_token = result.group(1)

            if battle_token:
                battle.battle_token = battle_token
                print(
                    f"First move : Poke is {self.current_battle.player.team[move.selectedPokemon - 1].name} ")
            else:
                raise Exception("Battle token not found")
        else:
            json = move.toDict() | {
                "battletoken": battle.battle_token
            }

            res = self.post(battle.getMoveUrl(), json)

            if self.current_battle.invalidated:
                # Don't do anything more if the battle has been terminated
                return

            if move.type == MoveType.ATTACK_MOVE:
                print(f"Doing attack {move.selectedAttack}")
            elif move.type == MoveType.POKE_SELECT_MOVE:
                print(f"Selected pokemon {move.selectedPokemon} : {battle.player.team[move.selectedPokemon - 1].name}")
            elif move.type == MoveType.ITEM_MOVE:
                print(f"Selected item : {move.selectedItem}")

        battle.move_count += 1
        battle.update(res)

    def getBattleResults(self):
        battle = self.current_battle

        if not battle.game_over:
            print("Battle is not over!")
            return

        if battle.invalidated:
            # If the battle ended early due to timeout / creds invalidation
            return {
                "cancelled": True
            }

        # If win/loss page was returned previously, use the previously returned html
        # because any request now won't be able to fetch it.
        end_html = battle.game_end_html

        if not end_html:
            res = self.post(battle.getMoveUrl(), {"do": "select"})
            end_html = res.text

        soup = BeautifulSoup(end_html, 'html.parser')

        if battle.type == BattleType.COMP_BATTLE or battle.type == BattleType.GYM_BATTLE:
            notif_div = soup.find("div", class_="notify_done")

            if (not notif_div):
                meta_tag = soup.select_one('meta[http-equiv="refresh"]')
                if meta_tag:
                    content = meta_tag["content"]
                    if content:
                        if content.find("/gyms") != -1:
                            return {
                                "money": "unknown",
                                "exp" : "unknown"
                            }

                # if the meta tag wasn't found, see if there was an error
                if soup.find("div", class_="notify_error"):
                    return {
                        "money": "unknown",
                        "exp" : "unknown"
                    }

                # Returning 3 things seperately, in case they need to be changed individually later 
                return {
                    "money": "unknown",
                    "exp" : "unknown"
                }
                

            notif_text: str = notif_div.decode_contents()
            

            res = re.search(r"won ([0-9,]+)\b.+gained ([0-9,]+) exp.", notif_text)

            if res:
                money = res.group(1).replace(",", "", -1)
                exp = res.group(2).replace(",", "", -1)

                return {
                    "money": int(money),
                    "exp": int(exp)
                }
            elif notif_text.find("lost") != -1:
                return {
                    "defeat": True
                }
        elif battle.type == BattleType.WILD_BATTLE:
            info_box = soup.find("div", class_="infobox")

            if len(argv) >= 2:
                if argv[1] == "-debug":
                    with open('./experiments/wild_battle.html', 'w') as f:
                        f.write(end_html)
                
            if info_box and (info_box.text.find("captured") != -1):
                poke_caught = info_box.find("b")

                stat_btns = info_box.select("i.sbtn")

                stats = []

                for stat_btn in stat_btns:
                    classes = stat_btn["class"]
                    for class_ in classes:
                        if class_.startswith("sbtn-"):
                            res = re.search(r"sbtn-(.+)\b", class_)
                            if res:
                                stats.append(res.group(1))

                return {
                    "poke_caught": poke_caught.text,
                    "stats": stats
                }
            elif soup.find("div", class_="notify_warning"):
                return {
                    "poke_caught": battle.opponent.team[0].name,
                    "stats": ['unknown']
                }
            else:
                notify_done_div = soup.find("div", class_="notify_done")

                if notify_done_div.text.find("defeated") != -1:
                    # We defeated it, but  couldn't capture
                    return {
                        "capture_failed": True
                    }

                # otherwise we lost
                return {
                    "defeat": True
                }

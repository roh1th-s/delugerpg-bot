import os
import re
import json
from typing import TypedDict
from sys import argv
from bs4 import BeautifulSoup
from .constants import Urls
from .BattleMove import BattleMove, MoveType
from .Battle import Battle, BattleType
from .utils import beep


class GymNotFoundException(Exception):
    pass


class GymLeader(TypedDict):
    leader_name: str
    is_defeated: bool
    battle_code: str | None
    battle_url: str | None


class MockResponse:
    def __init__(self, text, url, status_code=200):
        self.text = text
        self.url = url
        self.status_code = status_code
        self.ok = status_code < 400


class DelugeAPIClient:
    def __init__(
        self, sessCookie: str, password: str, username: str = None, use_tls_client: bool = False
    ):
        if not sessCookie or sessCookie == "":
            raise Exception("Session cookie not provided.")

        import undetected_chromedriver as uc

        options = uc.ChromeOptions()
        # Headless mode can be easily detected so we leave it headed
        self.driver = uc.Chrome(options=options)

        # Navigate to a base page to set cookies
        self.driver.get("https://www.delugerpg.com")
        sess_cookie = self.driver.get_cookie("PHPSESSID")
        if not sess_cookie or sess_cookie["value"] != sessCookie:
            self.driver.delete_cookie("PHPSESSID")
            self.driver.add_cookie(
                {"name": "PHPSESSID", "value": sessCookie, "domain": "www.delugerpg.com"}
            )

        self.wait_for_cloudflare()

        self.username = username or self.get_username()
        self.password = password

        self.current_battle = None
        self.map_hash_cache = {}

    def wait_for_cloudflare(self):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(self.driver, 5).until(lambda d: "Just a moment..." not in d.title)

    def get_username(self):
        res = self.get(Urls.profile)
        soup = BeautifulSoup(res.text, "html.parser")
        info_box = soup.find("div", class_="infobox")
        username_field = info_box.find("div", class_="proffield")
        name = username_field.h4.text
        return name

    def should_revalidate(self, res):
        return False  # Let selenium handle Cloudflare organically for now

    def revalidate_cookie(self):
        pass

    def clean_up(self):
        if self.current_battle:
            self.current_battle.terminate(invalidated=True)

    def logout(self):
        self.get(Urls.logout_ajax)
        print("Logged out.")

    def get(self, url, *args, **kwargs):
        self.driver.get(url)
        self.wait_for_cloudflare()
        page_source = self.driver.page_source

        # search any case with regex
        if (
            re.search(r"/unlock/verify\b", page_source)
            or re.search(r"Please fill in the captcha to proceed", page_source, re.IGNORECASE)
            or re.search(
                r"This is to check if you are a human or a bot\b", page_source, re.IGNORECASE
            )
        ):
            # We've hit captcha
            beep(1000)
            input(
                "Captcha detected. Please solve the captcha in the opened browser window, then press Enter here to continue..."
            )

        return MockResponse(self.driver.page_source, self.driver.current_url)

    def post(self, url, data=None, json_=None, *args, **kwargs):
        content_type = "application/x-www-form-urlencoded; charset=UTF-8"
        import urllib.parse

        if isinstance(data, dict):
            body_str = urllib.parse.urlencode(data)
        elif data:
            body_str = data
        else:
            body_str = ""

        fetch_js = f"""
        var callback = arguments[arguments.length - 1];
        fetch('{url}', {{
            method: 'POST',
            headers: {{
                'Content-Type': '{content_type}',
                'X-Requested-With': 'XMLHttpRequest'
            }},
            body: `{body_str}`
        }}).then(response => response.text().then(text => {{
            callback({{status: response.status, url: response.url, text: text}});
        }})).catch(error => callback({{error: error.message}}));
        """

        result = self.driver.execute_async_script(fetch_js)
        if "error" in result:
            raise Exception("Fetch failed: " + result["error"])

        return MockResponse(result["text"], result["url"], result["status"])

    def getMapHashes(self, mapName: str):
        response = self.get(f"{Urls.map}/{mapName}")

        results = re.search(
            r"<script>\s*var\s+m_h1\s*=\s*[\'\"]([^\'\"]+)[\'\"]\s*,\s*m_h2\s*=\s*[\'\"]([^\'\"]+)[\'\"]\s*,\s*m_h3\s*=\s*[\'\"]([^\'\"]+)[\'\"]",
            response.text,
        )

        if not results:
            if len(argv) >= 2:
                if argv[1] == "--debug":
                    with open("./map_hashes.html", "w") as f:
                        f.write(response.text)

            raise Exception("Couldn't find map hashes in html")

        map_hash1 = results.group(1)
        map_hash2 = results.group(2)
        map_hash3 = results.group(3)

        if not (map_hash1 and map_hash2 and map_hash3):
            raise Exception("Couldn't find all the required map hashes")

        return [map_hash1, map_hash2, map_hash3]

    def getGymsInfo(self) -> dict[str, list[GymLeader]]:
        res = self.get(Urls.gyms)
        gyms_page = res.text
        soup = BeautifulSoup(gyms_page, "html.parser")

        region_links = soup.select("#gymlinks a")
        region_names = [link.text.strip() for link in region_links]

        gyms_info = {}
        for region_name in region_names:
            region_tab = soup.select(f"#tab_{region_name.lower()}")[0]
            leader_cards = region_tab.select(".trainerbox")

            region_leaders: list[GymLeader] = []

            for card in leader_cards:
                leader_name = card.select_one(".name").text.strip()
                is_defeated = card.select_one(".gymdefeated") is not None
                battle_btn = card.select_one("a.btn-battle")
                battle_url = battle_btn["href"] if battle_btn else None
                battle_code = battle_url.split("/")[-1] if battle_url else None
                region_leaders.append(
                    {
                        "leader_name": leader_name,
                        "is_defeated": is_defeated,
                        "battle_code": battle_code,
                        "battle_url": battle_url,
                    }
                )
            gyms_info[region_name] = region_leaders

        return gyms_info

    def moveInMap(self, mapName: str, dir: str) -> list | dict:
        hashes = self.map_hash_cache.get(mapName)
        if not hashes:
            hashes = self.getMapHashes(mapName)
            self.map_hash_cache[mapName] = hashes

        res = self.post(
            f"{Urls.map_update_ajax}/{hashes[2]}/{hashes[0]}",
            {"direction": dir, "maphash": hashes[1], "mhx": os.getenv("MHX")},
        )
        return json.loads(res.text)

    def startUserBattle(self, user: str) -> Battle:
        res = self.get(f"{Urls.comp_battle}/u/{user}")

        if res.text.find("No such User.") != -1:
            raise Exception("No such user found!")

        # create a battle object from the html with necessary metadata
        self.current_battle = Battle(BattleType.COMP_BATTLE, self).fromHtml(res.text)

        print("Started a battle against user " + user)

        return self.current_battle

    def startGymBattle(self, gym_id: int) -> Battle:
        """Start a gym battle"""

        response = self.get(f"{Urls.gym_battle}/{gym_id}")

        if response.text.find("No such") != -1:
            raise GymNotFoundException("Invalid gym url")

        self.current_battle = Battle(BattleType.GYM_BATTLE, self).fromHtml(response.text)

        print("Gym battle started")

        return self.current_battle

    def startWildBattle(self, poke_catch_url: str, poke_secret: str, catch_secret: str) -> Battle:
        """Start a wild battle with a pokemon found on a map. This requires two secrets, both
        of which are accquired when finding a pokemon on any map.
        """

        response = self.post(
            f"{Urls.catch_poke}/{poke_catch_url}",
            {
                "do": "catch_pokemon",
                "secret": poke_secret,
                f"catch_{catch_secret}": "Try to Catch It",
            },
        )

        self.current_battle = Battle(BattleType.WILD_BATTLE, self).fromHtml(response.text)
        poke = self.current_battle.opponent.team[0]
        print(f"Wild battle started with {poke.name}, level : {poke.level}")

        return self.current_battle

    def doBattleMove(self, move: BattleMove):
        res = None
        battle = self.current_battle
        if battle.move_count == 0:
            # if this is the first move
            res = self.post(battle.getMoveUrl(), move.toDict())

            if self.current_battle.invalidated:
                # Don't do anything more if the battle has been terminated
                return

            result = re.search(
                r".*<input\s*type=\"hidden\"\s*name=\"battletoken\"\s*value=\"(.+)\"\s*/?>.*",
                res.text,
            )

            if not result:
                raise Exception("Battle token not found")

            battle_token = result.group(1)

            if battle_token:
                battle.battle_token = battle_token
                battle.player.current_poke = battle.player.team[move.selectedPokemon - 1]
                print(
                    f"First move : Selected pokemon is {self.current_battle.player.team[move.selectedPokemon - 1].name} "
                )
            else:
                raise Exception("Battle token not found")
        else:
            json = move.toDict() | {"battletoken": battle.battle_token}

            res = self.post(battle.getMoveUrl(), json)

            if self.current_battle.invalidated:
                # Don't do anything more if the battle has been terminated
                return

            if move.type == MoveType.ATTACK_MOVE:
                print(f"Doing attack {move.selectedAttack}: {battle.player.current_poke.attacks[move.selectedAttack - 1].name}")
            elif move.type == MoveType.POKE_SELECT_MOVE:
                print(
                    f"Selected pokemon no. {move.selectedPokemon} : {battle.player.team[move.selectedPokemon - 1].name}"
                )
            elif move.type == MoveType.ITEM_MOVE:
                print(f"Selected item : {move.selectedItem}")

            # Show result of moves
            soup = BeautifulSoup(res.text, "html.parser")
            user_div = soup.find(id="user")
            user_damage = user_div.find("div", class_="damage")
            if user_damage:
                result_text = user_damage.decode_contents().strip()
                if result_text != "":
                    print(result_text)

            opponent_div = soup.find(id="opponent")
            opponent_damage = opponent_div.find("div", class_="damage")
            if opponent_damage:
                result_text = opponent_damage.decode_contents().strip()
                if result_text != "":
                    print(f"{result_text}")

        battle.move_count += 1
        battle.update(res)

    def getBattleResults(self):
        battle = self.current_battle

        if not battle.game_over:
            print("Battle is not over!")
            return

        if battle.invalidated:
            # If the battle ended early due to timeout / creds invalidation
            return {"cancelled": True}

        # If win/loss page was returned previously, use the previously returned html
        # because any request now won't be able to fetch it.
        end_html = battle.game_end_html

        if not end_html:
            res = self.post(battle.getMoveUrl(), {"do": "select"})
            end_html = res.text

        soup = BeautifulSoup(end_html, "html.parser")

        if battle.type == BattleType.COMP_BATTLE or battle.type == BattleType.GYM_BATTLE:
            if battle.winner.name != battle.player.name:
                return {"defeat": True, "winner": battle.winner.name}

            notif_div = soup.find("div", class_="notify_done")

            if not notif_div:
                meta_tag = soup.select_one('meta[http-equiv="refresh"]')
                if meta_tag:
                    content = meta_tag["content"]
                    if content:
                        if content.find("/gyms") != -1:
                            return {"money": "unknown", "exp": "unknown"}

                # if the meta tag wasn't found, see if there was an error
                if soup.find("div", class_="notify_error"):
                    return {"money": "unknown", "exp": "unknown"}

                # Returning 3 things seperately, in case they need to be changed individually later
                return {"money": "unknown", "exp": "unknown"}

            notif_text: str = notif_div.decode_contents()

            res = re.search(r"won ([0-9,]+)\b.+gained ([0-9,]+) exp.", notif_text)

            if res:
                money = res.group(1).replace(",", "", -1)
                exp = res.group(2).replace(",", "", -1)

                return {"money": int(money), "exp": int(exp)}
            elif notif_text.find("lost") != -1:
                return {"defeat": True}
        elif battle.type == BattleType.WILD_BATTLE:
            info_box = soup.find("div", class_="infobox")

            if len(argv) >= 2:
                if argv[1] == "-debug":
                    with open("./experiments/wild_battle.html", "w") as f:
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

                return {"poke_caught": poke_caught.text, "stats": stats}
            elif soup.find("div", class_="notify_warning"):
                return {"poke_caught": battle.opponent.team[0].name, "stats": ["unknown"]}
            else:
                notify_done_div = soup.find("div", class_="notify_done")

                if notify_done_div.text.find("defeated") != -1:
                    # We defeated it, but  couldn't capture
                    return {"capture_failed": True}

                # otherwise we lost
                return {"defeat": True}

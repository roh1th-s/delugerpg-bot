import re
from bs4 import BeautifulSoup, Tag
from enum import Enum
from .constants import Urls


class Poke:
    def __init__(self, name: str, types: list[str], level: int, hp: int):
        self.name = name
        self.types = types
        self.level = level
        self.hp = hp
        self.hp_max = None
        self.current_ailment: str = None


class BattlePlayer:
    def __init__(self, name: str, pokemon: list[Poke]):
        self.name = name
        self.team = pokemon
        self.pokes_left = len(pokemon)

        # Current poke active
        self.current_poke: Poke = None


class BattleType(Enum):
    COMP_BATTLE = 1
    WILD_BATTLE = 2
    GYM_BATTLE = 3


class Battle:
    def __init__(self, type: BattleType, apiClient):
        self.player = None
        self.opponent = None

        self.http = apiClient
        self.type: BattleType = type
        self.battle_token = ""
        self.move_count = 0

        # To store the html which has match results
        self.game_end_html = None

        # Was battle cut short due to cookie invalidation / timeout
        self.invalidated = False

        # Indicates if current duel is over, so a new pokemon can be selected.
        # Set to true when either the player's or opponent's poke has fainted.
        self.current_duel_over = False

        self.game_over = False
        self.winner = None

    @staticmethod
    def parseInitialBattleData(htmlNode):
        opp_name = htmlNode.select("h2")[0].string
        res = re.search(r"(.+)'s Team", opp_name)

        if res:
            opp_name = res.group(1)
        else:
            opp_name = ""

        poke_list = htmlNode.select(".battlelister")[0]
        poke_list_items = poke_list.select(".battlelistitem")

        opp_pokemon = []
        for li in poke_list_items:
            poke_types: list[str] = []  # List of types for this poke
            poke_name = li.select(".batname span")[0].string
            poke_type_containers = li.select(".batname .tbtn")

            for type_container in poke_type_containers:
                class_string = ''.join(type_container["class"])

                # types are in one of the classes as 'tbtn-{type}'
                results = re.search(r"tbtn-([a-zA-Z]+)\b", class_string)

                poke_types.append(results.group(1))

            level_hp_span = li.select(".battlelistlvlhp span")[0]
            # <span><b>Level:</b> 100<br><br><b>HP:</b> 400</span>
            level = level_hp_span.contents[1]
            hp = level_hp_span.contents[5]

            opp_pokemon.append(Poke(poke_name, poke_types, int(level), int(hp)))

        return [opp_name, opp_pokemon]

    @staticmethod
    def parsePokemonData(div: Tag):
        pokemonDiv = div.find("div", class_="pokemon")
        poke_name: str = pokemonDiv.select_one("span.smallcaps").string.strip()
        hp_text: str = div.find("div", class_="hp").string

        res = re.search(r"HP: ([0-9]+)/([0-9]+)", hp_text)

        hp_remaining: int = int(res.group(1))
        hp_max: int = int(res.group(2))

        ail_btn = div.select_one("i.ailbtn")

        ailment = None
        if ail_btn:
            classes = ail_btn["class"]
            for class_ in classes:
                if class_.startswith("ailbtn-"):
                    # eg. ailbtn-slp
                    result = re.search(r"ailbtn-(.+)\b", class_)
                    if result:
                        ailment = result.group(1)
                        break

        return {
            "poke_name": poke_name,
            "hp_rem": hp_remaining,
            "hp_max": hp_max,
            "ailment": ailment
        }

    def fromHtml(self, html: str):
        soup = BeautifulSoup(html, 'html.parser')

        oppTeamDiv = soup.find(id="teamleft")
        selfTeamDiv = soup.find(id="teamright")

        if not (oppTeamDiv or selfTeamDiv):
            raise Exception("Invalid html")

        opp_name, opp_pokes = Battle.parseInitialBattleData(oppTeamDiv)
        self.opponent = BattlePlayer(opp_name, opp_pokes)

        _, self_pokes = Battle.parseInitialBattleData(selfTeamDiv)

        self_name = self.http.username

        name_dropdown = soup.find(id="ndright")
        if name_dropdown:
            self_name = name_dropdown.find(id="uname").string

        self.player = BattlePlayer(self_name, self_pokes)

        return self

    def getMoveUrl(self):
        if self.type == BattleType.COMP_BATTLE:
            if self.move_count == 0:
                return Urls.comp_battle
            return Urls.comp_battle_ajax
        elif self.type == BattleType.WILD_BATTLE:
            return Urls.wild_battle_ajax
        elif self.type == BattleType.GYM_BATTLE:
            return Urls.gym_battle_ajax

    def updatePokemon(self, poke_data, player: BattlePlayer):
        found = False
        for i in range(len(player.team)):
            poke = player.team[i]
            if poke.hp == 0:
                continue

            if poke.name == poke_data["poke_name"]:
                found = True
                player.current_poke = poke
                poke.hp = poke_data["hp_rem"]
                poke.hp_max = poke_data["hp_max"]
                poke.current_ailment = poke_data["ailment"]

                if poke_data["hp_rem"] == 0:
                    player.pokes_left -= 1
                    self.current_duel_over = True
                break

        if not found:
            print(f"Pokemon {poke_data['poke_name']} of {player.name} was not found in local state.")

    def isPokeFainted(self, poke_no, player: BattlePlayer = None):
        if not player:
            # The bot user by default
            player = self.player

        # poke_no starts at 1
        if player.team[poke_no - 1].hp <= 0:
            return True

        return False

    def update(self, http_res):
        html = http_res.text
        soup = BeautifulSoup(html, 'html.parser')

        if self.current_duel_over:
            # If in the previous move the duel was over, this must be a fresh duel.
            self.current_duel_over = False

        # Sometimes gives us the game over page directly???
        game_end_div = soup.find("div", class_="notify_done")
        if not game_end_div:
            game_end_div = soup.find(
                "div", class_="infobox") or soup.find(
                "div", class_="notify_warning") or soup.find(
                "div", class_="notify_error")
                
            meta_tag = soup.select_one('meta[http-equiv="refresh"]')
            if meta_tag:
                content = meta_tag["content"]
                if content:
                    game_end_div = meta_tag

        if game_end_div:
            self.terminate()
            self.game_end_html = html

            game_end_text = game_end_div.text
            if game_end_text.find("defeated") != -1 or game_end_text.find("captured") != -1:
                # if there is 'defeated' or 'captured' then we won / captured the wild pokemon
                self.winner = self.player
            else:
                self.winner = self.opponent

            return

        # Update opponents pokemon
        opponent_div = soup.find(id="opponent")
        poke_data = Battle.parsePokemonData(opponent_div)
        self.updatePokemon(poke_data, self.opponent)

        # Update players pokemon
        player_div = soup.find(id="user")
        poke_data = Battle.parsePokemonData(player_div)
        self.updatePokemon(poke_data, self.player)

        if self.player.pokes_left == 0:
            self.winner = self.opponent
            self.terminate()
        elif self.opponent.pokes_left == 0:
            self.winner = self.player
            self.terminate()

    def terminate(self, **kwargs):
        self.game_over = True
        self.current_duel_over = True

        if kwargs.get("invalidated"):
            self.invalidated = True

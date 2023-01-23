import re
from bs4 import BeautifulSoup, Tag
from enum import Enum

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


def parsePokemonData(div: Tag):
    pokemonDiv = div.find("div", class_="pokemon")
    poke_name: str = pokemonDiv.select_one("span.smallcaps").string.strip()
    hp_text: str = div.find("div", class_="hp").string

    res = re.search(r"HP: ([0-9]+)/([0-9]+)", hp_text)

    hp_remaining: int = int(res.group(1))
    hp_max: int = int(res.group(2))

    return [poke_name, hp_remaining, hp_max]


class Poke:
    def __init__(self, name: str, types: list[str], level: int, hp: int):
        self.name = name
        self.types = types
        self.level = level
        self.hp = hp
        self.hp_max = None


class Player:
    def __init__(self, name: str, pokemon: list[Poke]):
        self.name = name
        self.team = pokemon
        self.pokes_left = len(pokemon)


class BattleType(Enum):
    COMP_BATTLE = 1
    WILD_BATTLE = 2


class Battle:
    def __init__(self, type: BattleType, apiClient):
        self.player = None
        self.opponent = None

        self.http = apiClient
        self.type: BattleType = type
        self.battle_token = ""
        self.move_count = 0

        # Indicates if current duel is over, so a new pokemon can be selected.
        # Set to true when either the player's or opponent's poke has fainted.
        self.current_duel_over = False

        self.game_over = False
        self.winner = None

    def fromHtml(self, html: str):
        soup = BeautifulSoup(html, 'html.parser')

        oppTeamDiv = soup.find(id="teamleft")
        selfTeamDiv = soup.find(id="teamright")

        if not (oppTeamDiv or selfTeamDiv):
            raise Exception("Invalid html")

        opp_name, opp_pokes = parseInitialBattleData(oppTeamDiv)
        self.opponent = Player(opp_name, opp_pokes)

        _, self_pokes = parseInitialBattleData(selfTeamDiv)

        self_name = ""

        name_dropdown = soup.find(id="ndright")
        if name_dropdown:
            self_name = name_dropdown.find(id="uname").string

        self.player = Player(self_name, self_pokes)

        return self

    def updatePokemon(self, poke_name, hp_rem, hp_max, player: Player):
        found = False
        for i in range(len(player.team)):
            poke = player.team[i]
            if poke.hp == 0:
                continue

            if poke.name == poke_name:
                found = True
                poke.hp = hp_rem
                poke.hp_max = hp_max
                if hp_rem == 0:
                    player.pokes_left -= 1
                    self.current_duel_over = True
                break

        if not found:
            print(f"Pokemon {poke_name} of {player.name} was not found in local state.")

    def isPokeFainted(self, poke_no, player: Player = None):
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

        # Update opponents pokemon
        opponent_div = soup.find(id="opponent")
        poke_name, hp_rem, hp_max = parsePokemonData(opponent_div)
        self.updatePokemon(poke_name, hp_rem, hp_max, self.opponent)

        # Update players pokemon
        player_div = soup.find(id="user")
        poke_name, hp_rem, hp_max = parsePokemonData(player_div)
        self.updatePokemon(poke_name, hp_rem, hp_max, self.player)

        if self.player.pokes_left == 0:
            self.winner = "opponent"
            self.game_over = True
        elif self.opponent.pokes_left == 0:
            self.winner = "player"
            self.game_over = True

    def parseResults(self, html):
        soup = BeautifulSoup(html, 'html.parser')

        notif_div = soup.find("div", class_="notify_done")
        win_text: str = notif_div.decode_contents()

        res = re.search(r"won ([0-9,]+)\b.+gained ([0-9,]+) exp.", win_text)

        if res:
            money = res.group(1).replace(",", "", -1)
            exp = res.group(2).replace(",", "", -1)

            return {
                "money": int(money),
                "exp": int(exp)
            }
import unittest
from os import path
from delugebot.Battle import *

class BattleParserTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        file_path = path.join(path.dirname(__file__), 'battle_test.html')
        html = open(file_path, "r")
        self.battle = Battle(BattleType.COMP_BATTLE, {}).fromHtml(html)
        html.close()

    def test_opponent_name(self):
        self.assertEqual(self.battle.opponent.name, "test-opponent")

    def test_player_name(self):
        self.assertEqual(self.battle.player.name, "test_user12345")

    def test_player_pokemon(self):
        self_team = self.battle.player.team

        pokes = [
            {'name': 'Froakie', 'types': ['water'], 'level': 15, 'hp': 60},
            {'name': 'Weedle', 'types': ['bug', 'poison'], 'level': 9, 'hp': 36},
            {'name': 'Mawile', 'types': ['steel', 'fairy'], 'level': 75, 'hp': 300},
            {'name': 'Chrome Slakoth', 'types': ['normal'], 'level': 16, 'hp': 87}
        ]

        for i in range(len(self_team)):
            poke = self_team[i]
            self.assertEqual(poke.__dict__, poke.__dict__ | pokes[i])

    def test_opponent_pokemon(self):
        opp_team = self.battle.opponent.team
        
        pokes = [
            {'name': 'Larvitar', 'types': ['rock', 'ground'], 'level': 100, 'hp': 400},
            {'name': 'Pupitar', 'types': ['rock', 'ground'], 'level': 100, 'hp': 400},
            {'name': 'Onix', 'types': ['rock', 'ground'], 'level': 100, 'hp': 400},
            {'name': 'Golem', 'types': ['rock', 'ground'], 'level': 100, 'hp': 400},
            {'name': 'Rhydon', 'types': ['ground', 'rock'], 'level': 100, 'hp': 400},
            {'name': 'Rhyperior', 'types': ['ground', 'rock'], 'level': 100, 'hp': 400}
        ]

        for i in range(len(opp_team)):
            poke = opp_team[i]
            self.assertEqual(poke.__dict__, poke.__dict__ | pokes[i])
            
if __name__ == "__main__":
    unittest.main()

from enum import Enum


class MoveType(Enum):
    ATTACK_MOVE = 0
    POKE_SELECT_MOVE = 1


class BattleMove:
    def __init__(self, moveType: MoveType, **kwargs):
        """For attack moves: Specify `selected_attack`: Number from 1 - 4 describing attack to be performed.
            For poke selection, specifiy `poke_select`: Number from 1 - 6 describing pokemon selected.
        """
        self.type: MoveType = moveType

        if moveType == MoveType.ATTACK_MOVE:
            selected_attack = kwargs.get("selected_attack")
            if not selected_attack:
                raise Exception(
                    "Selected move not specified. Cannot create attack move")

            self.__selected_attack = selected_attack
            self.__do = "attack"

        elif moveType == MoveType.POKE_SELECT_MOVE:
            poke_select = kwargs.get("poke_select")
            if not poke_select:
                raise Exception(
                    "Selected pokemon not specified. Cannot create poke_select move")

            self.__poke_select = poke_select
            self.__do = "showattacks"

    @property
    def do(self):
        return self.__do

    @property
    def selectedAttack(self):
        if not self.type == MoveType.ATTACK_MOVE:
            raise Exception("Move is not attack move.")
        return self.__selected_attack

    @property
    def selectedPokemon(self):
        if not self.type == MoveType.POKE_SELECT_MOVE:
            raise Exception("Move is not poke_select move.")
        return self.__poke_select

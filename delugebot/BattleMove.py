from enum import Enum


class MoveType(Enum):
    ATTACK_MOVE = 0
    POKE_SELECT_MOVE = 1
    ITEM_MOVE = 2


class BattleMove:
    def __init__(self, moveType: MoveType, **kwargs):
        """For attack moves: Specify `selected_attack`: Number from 1 - 4 describing attack to be performed.
            For poke selection, specify `selected_poke`: Number from 1 - 6 describing pokemon selected.
            For item selection, specify `selected_item`: Name of item
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
            selected_poke = kwargs.get("selected_poke")
            if not selected_poke:
                raise Exception(
                    "Selected pokemon not specified. Cannot create poke_select move")

            self.__selected_poke = selected_poke
            self.__do = "showattacks"

        elif moveType == MoveType.ITEM_MOVE:
            selected_item = kwargs.get("selected_item")
            if not selected_item:
                raise Exception("Selected item not specified.")

            self.__selected_item = selected_item
            self.__do = "attack"
        else:
            raise Exception("Invalid move type")

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
        return self.__selected_poke

    @property
    def selectedItem(self):
        if not self.type == MoveType.ITEM_MOVE:
            raise Exception("Move is not item_select move")
        return self.__selected_item
    
    def toDict(self):
        json = {
            "do": self.__do
        }

        if self.type == MoveType.ATTACK_MOVE:
            json["selected"] = self.__selected_attack
        elif self.type == MoveType.POKE_SELECT_MOVE:
            json["pokeselect"] = self.__selected_poke
        elif self.type == MoveType.ITEM_MOVE:
            json["selectitem"] = self.__selected_item
            json["useitem"] = 1
        
        return json
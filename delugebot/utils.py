from delugebot.Battle import PokeAttack


def beep(time_in_ms=500):
    from winsound import Beep

    Beep(600, time_in_ms)


def get_best_move(attacks: list[PokeAttack], opponent_poke_type: str):
    best_move = None
    best_multiplier = 0

    for attack in attacks:
        multiplier = 1.0

        if opponent_poke_type in attack.strong_against:
            multiplier *= 2
        elif opponent_poke_type in attack.weak_against:
            multiplier *= 0.5

        if multiplier > best_multiplier:
            best_multiplier = multiplier
            best_move = attack

    return best_move

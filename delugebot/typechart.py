type_chart = {
    "normal": {
        "weak": ["fighting"],
        "resist": [],
        "immunity": ["ghost"],
    },
    "fire": {
        "weak": ["water", "ground", "rock"],
        "resist": ["fire", "grass", "ice", "bug", "steel", "fairy"],
        "immunity": [],
    },
    "water": {
        "weak": ["electric", "grass"],
        "resist": ["fire", "water", "ice", "steel"],
        "immunity": [],
    },
    "electric": {
        "weak": ["ground"],
        "resist": ["electric", "flying", "steel"],
        "immunity": [],
    },
    "grass": {
        "weak": ["fire", "ice", "poison", "flying", "bug"],
        "resist": ["water", "electric", "grass", "ground"],
        "immunity": [],
    },
    "ice": {
        "weak": ["fire", "fighting", "rock", "steel"],
        "resist": ["ice"],
        "immunity": [],
    },
    "fighting": {
        "weak": ["flying", "psychic", "fairy"],
        "resist": ["bug", "rock", "steel"],
        "immunity": [],
    },
    "poison": {
        "weak": ["ground", "psychic"],
        "resist": ["grass", "fighting", "poison", "bug", "fairy"],
        "immunity": [],
    },
    "ground": {
        "weak": ["water", "grass", "ice"],
        "resist": ["poison", "rock"],
        "immunity": ["electric", "flying"],
    },
    "flying": {
        "weak": ["electric", "ice", "rock"],
        "resist": ["grass", "fighting", "bug"],
        "immunity": ["ground"],
    },
    "psychic": {
        "weak": ["bug", "ghost", "dark"],
        "resist": ["fighting", "psychic"],
        "immunity": [],
    },
    "bug": {
        "weak": ["fire", "flying", "rock"],
        "resist": ["grass", "fighting", "ground"],
        "immunity": [],
    },
    "rock": {
        "weak": ["water", "grass", "fighting", "ground", "steel"],
        "resist": ["normal", "fire", "poison", "flying"],
        "immunity": [],
    },
    "ghost": {
        "weak": ["ghost", "dark"],
        "resist": ["poison", "bug"],
        "immunity": ["normal", "fighting"],
    },
    "dragon": {
        "weak": ["ice", "dragon", "fairy"],
        "resist": ["fire", "water", "electric", "grass"],
        "immunity": [],
    },
    "dark": {
        "weak": ["fighting", "bug", "fairy"],
        "resist": ["dragon"],
        "immunity": ["psychic"],
    },
    "steel": {
        "weak": ["fire", "fighting", "ground"],
        "resist": [
            "normal",
            "grass",
            "ice",
            "flying",
            "psychic",
            "bug",
            "rock",
            "ghost",
            "dark",
            "steel",
            "fairy",
        ],
        "immunity": ["poison"],
    },
    "fairy": {
        "weak": ["poison", "steel"],
        "resist": ["fighting", "bug", "dark"],
        "immunity": ["dragon"],
    },
}


def get_attack_multiplier(attack_type: str, opponent_types: list[str]) -> float:
    if attack_type not in type_chart:
        raise ValueError(f"Invalid attack type: {attack_type}")
    if not opponent_types:
        raise ValueError("Opponent types cannot be empty")

    multiplier = 1.0

    for opponent_type in opponent_types:
        if opponent_type not in type_chart:
            raise ValueError(f"Invalid opponent type: {opponent_type}")

        if attack_type in type_chart[opponent_type]["weak"]:
            multiplier *= 2.0
        elif attack_type in type_chart[opponent_type]["resist"]:
            multiplier *= 0.5
        elif attack_type in type_chart[opponent_type]["immunity"]:
            multiplier *= 0.0

    return multiplier

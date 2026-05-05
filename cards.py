__author__ = "Liam Gornshtein"

CARDS = {
    # --- NEUTRAL HEROES ---
    "Geralt": {"power": 15, "row": "melee", "hero": True, "limit": 1},
    "Ciri": {"power": 15, "row": "melee", "hero": True, "limit": 1},
    "Triss": {"power": 7, "row": "melee", "hero": True, "limit": 1},
    "Yennefer": {"power": 7, "row": "ranged", "hero": True, "ability": "medic", "limit": 1},
    "Mysterious Elf": {"power": 0, "row": "melee", "hero": True, "ability": "spy", "limit": 1},

    # --- NORTHERN REALMS HEROES ---
    "Vernon Roche": {"power": 10, "row": "melee", "hero": True, "limit": 1},
    "John Natalis": {"power": 10, "row": "melee", "hero": True, "limit": 1},
    "Esterad Thyssen": {"power": 10, "row": "melee", "hero": True, "limit": 1},
    "Philippa Eilhart": {"power": 10, "row": "ranged", "hero": True, "limit": 1},

    # --- NEUTRAL NORMAL CARDS ---
    "Vesemir": {"power": 6, "row": "melee", "limit": 1},
    "Zoltan": {"power": 5, "row": "melee", "limit": 1},
    "Dandelion": {"power": 2, "row": "melee", "ability": "morale", "limit": 1},
    "Villentretenmerth": {"power": 7, "row": "melee", "ability": "melee_scorch", "limit": 1},
    "Emiel Regis": {"power": 5, "row": "melee", "limit": 1},

    # --- NORTHERN REALMS NORMAL CARDS ---
    "Sigismund Dijkstra": {"power": 4, "row": "melee", "ability": "spy", "limit": 1},
    "Prince Stennis": {"power": 5, "row": "melee", "ability": "spy", "limit": 1},
    "Thaler": {"power": 1, "row": "siege", "ability": "spy", "limit": 1},
    "Dun Banner Medic": {"power": 5, "row": "siege", "ability": "medic", "limit": 1},
    "Keira": {"power": 5, "row": "ranged", "limit": 1},
    "Dethmold": {"power": 6, "row": "ranged", "limit": 1},
    "Sabrina Glevissig": {"power": 4, "row": "ranged", "limit": 1},
    "Sile de Tansarville": {"power": 5, "row": "ranged", "limit": 1},
    "Sheldon Skaggs": {"power": 4, "row": "ranged", "limit": 1},
    "Redanian Foot Soldier": {"power": 1, "row": "melee", "limit": 2},
    "Siegfried of Denesle": {"power": 5, "row": "melee", "limit": 1},
    "Ves": {"power": 5, "row": "melee", "limit": 1},
    "Yarpen Zigrin": {"power": 2, "row": "melee", "limit": 1},
    "Catapult": {"power": 8, "row": "siege", "ability": "tight_bond", "limit": 2},
    "Trebuchet": {"power": 6, "row": "siege", "limit": 2},
    "Ballista": {"power": 6, "row": "siege", "limit": 2},
    "Siege Tower": {"power": 6, "row": "siege", "limit": 1},
    "Kaedweni Siege Expert": {"power": 1, "row": "siege", "ability": "boost", "limit": 3},
    "Blue Stripes": {"power": 4, "row": "melee", "ability": "tight_bond", "limit": 3},
    "Dragon Hunter": {"power": 5, "row": "ranged", "ability": "tight_bond", "limit": 3},
    "Poor Infantry": {"power": 1, "row": "melee", "ability": "tight_bond", "limit": 3},

    # --- SPECIAL CARDS ---
    "Biting Frost": {"power": 0, "row": "weather", "ability": "frost", "limit": 2},
    "Impenetrable Fog": {"power": 0, "row": "weather", "ability": "fog", "limit": 2},
    "Torrential Rain": {"power": 0, "row": "weather", "ability": "rain", "limit": 2},
    "Clear Skies": {"power": 0, "row": "weather", "ability": "clear_weather", "limit": 2},
    "Scorch": {"power": 0, "row": "special", "ability": "scorch", "limit": 2},
    "Commander's Horn": {"power": 0, "row": "any", "ability": "horn", "limit": 3},
    "Decoy": {"power": 0, "row": "any", "ability": "decoy", "limit": 3}
}
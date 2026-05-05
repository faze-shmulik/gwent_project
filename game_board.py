__author__ = "Liam Gornshtein"

import random
from cards import CARDS

class GameBoard:
    def __init__(self):
        self.players = {
            1: {"deck": [], "hand": [], "board": {"melee": [], "ranged": [], "siege": []}, "passed": False,
                "rounds_won": 0, "horns": [], "graveyard": []},
            2: {"deck": [], "hand": [], "board": {"melee": [], "ranged": [], "siege": []}, "passed": False,
                "rounds_won": 0, "horns": [], "graveyard": []}
        }
        self.current_turn = random.choice([1, 2])
        self.round_number = 1
        self.game_over = False
        self.weather_zone = []

    def reset_player(self, player_id):
        """Wipes a player's state so they can log back in fresh."""
        self.players[player_id] = {
            "deck": [], "hand": [], "board": {"melee": [], "ranged": [], "siege": []},
            "passed": False, "rounds_won": 0, "horns": [], "graveyard": []
        }

    def redraw_card(self, player_id, card_name):
        """Swaps a card from the hand with a random card from the deck."""
        if card_name in self.players[player_id]["hand"] and len(self.players[player_id]["deck"]) > 0:
            self.players[player_id]["hand"].remove(card_name)
            new_card = self.players[player_id]["deck"].pop()
            self.players[player_id]["hand"].append(new_card)
            self.players[player_id]["deck"].append(card_name)
            random.shuffle(self.players[player_id]["deck"])
            return True
        return False

    def load_deck(self, player_id, deck_list):
        """Loads a deck for a player and draws 10 cards."""
        valid_deck = [card for card in deck_list if card in CARDS]
        random.shuffle(valid_deck)
        self.players[player_id]["deck"] = valid_deck

        draw_count = min(10, len(valid_deck))
        self.players[player_id]["hand"] = [self.players[player_id]["deck"].pop() for _ in range(draw_count)]

    def get_card_power(self, player_id, card_name, row_name):
        """Helper to get a card's current power while checking for weather, horns, and heroes."""
        card_data = CARDS[card_name]
        is_hero = card_data.get("hero", False)

        if is_hero:
            return card_data["power"]

        is_weathered = False
        if row_name == "melee" and "Biting Frost" in self.weather_zone:
            is_weathered = True
        elif row_name == "ranged" and "Impenetrable Fog" in self.weather_zone:
            is_weathered = True
        elif row_name == "siege" and "Torrential Rain" in self.weather_zone:
            is_weathered = True

        base_power = 1 if is_weathered else card_data["power"]
        row_list = self.players[player_id]["board"][row_name]
        boost_count = sum(1 for c in row_list if CARDS[c].get("ability") == "boost")

        if card_data.get("ability") == "boost":
            base_power += max(0, boost_count - 1)
        else:
            base_power += boost_count

        if card_data.get("ability") == "tight_bond":
            row_list = self.players[player_id]["board"][row_name]
            base_power *= row_list.count(card_name)

        has_physical_horn = row_name in self.players[player_id]["horns"]
        dandelion_present = "Dandelion" in self.players[player_id]["board"][row_name]
        row_horn_active = has_physical_horn or dandelion_present

        if row_horn_active and card_name != "Dandelion":
            return base_power * 2

        return base_power

    def apply_melee_scorch(self, player_id):
        """Villentretenmerth's ability: Burns strongest opponent melee card(s) if row power >= 10."""
        opp_id = 2 if player_id == 1 else 1

        melee_total = 0
        for card_name in self.players[opp_id]["board"]["melee"]:
            melee_total += self.get_card_power(opp_id, card_name, "melee")

        if melee_total >= 10:
            max_power = -1

            for card_name in self.players[opp_id]["board"]["melee"]:
                if not CARDS[card_name].get("hero", False):
                    pwr = self.get_card_power(opp_id, card_name, "melee")
                    if pwr > max_power:
                        max_power = pwr

            if max_power > 0:
                survivors = []
                for card_name in self.players[opp_id]["board"]["melee"]:
                    if not CARDS[card_name].get("hero", False) and self.get_card_power(opp_id, card_name,
                                                                                       "melee") == max_power:
                        self.players[opp_id]["graveyard"].append(card_name)
                        continue
                    else:
                        survivors.append(card_name)

                self.players[opp_id]["board"]["melee"] = survivors

    def apply_scorch(self):
        """Finds the highest power non-hero card(s) on the board and destroys them."""
        max_power = -1

        for p in [1, 2]:
            for row_name, card_list in self.players[p]["board"].items():
                for card_name in card_list:
                    if not CARDS[card_name].get("hero", False):
                        pwr = self.get_card_power(p, card_name, row_name)
                        if pwr > max_power:
                            max_power = pwr

        if max_power > 0:
            for p in [1, 2]:
                for row_name in self.players[p]["board"]:
                    survivors = []
                    for card_name in self.players[p]["board"][row_name]:
                        if not CARDS[card_name].get("hero", False) and self.get_card_power(p, card_name,
                                                                                           row_name) == max_power:
                            self.players[p]["graveyard"].append(card_name)
                            continue
                        else:
                            survivors.append(card_name)
                    self.players[p]["board"][row_name] = survivors

    def get_score(self, player_id):
        """Calculates the current board score for a player, applying weather and horn rules."""
        score = 0

        for row_name, card_list in self.players[player_id]["board"].items():
            is_weathered = False
            if row_name == "melee" and "Biting Frost" in self.weather_zone:
                is_weathered = True
            elif row_name == "ranged" and "Impenetrable Fog" in self.weather_zone:
                is_weathered = True
            elif row_name == "siege" and "Torrential Rain" in self.weather_zone:
                is_weathered = True

            has_physical_horn = row_name in self.players[player_id]["horns"]
            dandelion_present = "Dandelion" in card_list
            row_horn_active = has_physical_horn or dandelion_present

            boost_count = sum(1 for c in card_list if CARDS[c].get("ability") == "boost")

            for card_name in card_list:
                card_data = CARDS[card_name]
                is_hero = card_data.get("hero", False)

                if is_weathered and not is_hero:
                    card_power = 1
                else:
                    card_power = card_data["power"]

                if not is_hero:
                    if card_data.get("ability") == "boost":
                        card_power += max(0, boost_count - 1)
                    else:
                        card_power += boost_count

                if card_data.get("ability") == "tight_bond":
                    card_power *= card_list.count(card_name)

                if row_horn_active and not is_hero and card_name != "Dandelion":
                    score += card_power * 2
                else:
                    score += card_power

        return score

    def play_card(self, player_id, card_name, row, target_card=None):
        """Attempts to play a card."""
        if self.game_over:
            return False, "Game is already over."

        if player_id != self.current_turn:
            return False, "It is not your turn."

        if self.players[player_id]["passed"]:
            return False, "You have already passed this round."

        if card_name not in self.players[player_id]["hand"]:
            return False, "You don't have that card in your hand."

        if row not in ["melee", "ranged", "siege", "weather", "special"]:
            return False, "Invalid row."

        if CARDS[card_name]["row"] != "any" and CARDS[card_name]["row"] != row:
            return False, f"{card_name} must be played in the {CARDS[card_name]['row']} row."

        if CARDS[card_name].get("ability") == "horn":
            if row not in ["melee", "ranged", "siege"]:
                return False, "Commander's Horn must be played on a valid row."

            dandelion_present = "Dandelion" in self.players[player_id]["board"][row]
            if row in self.players[player_id]["horns"] or dandelion_present:
                return False, "That row already has a Commander's Horn effect!"

            self.players[player_id]["hand"].remove(card_name)
            self.players[player_id]["horns"].append(row)
            self.next_turn()
            return True, f"Player {player_id} played Commander's Horn on {row}!"

        if CARDS[card_name].get("ability") == "decoy":
            if not target_card:
                return False, "You must select a card to decoy."
            if target_card not in self.players[player_id]["board"][row]:
                return False, "Target card not found on the board."
            if CARDS[target_card].get("hero", False):
                return False, "Cannot decoy a Hero card!"
            if target_card == "Decoy":
                return False, "Cannot decoy a Decoy!"

            self.players[player_id]["hand"].remove(card_name)
            self.players[player_id]["board"][row].remove(target_card)
            self.players[player_id]["board"][row].append(card_name)
            self.players[player_id]["hand"].append(target_card)

            self.next_turn()
            return True, f"Player {player_id} used a Decoy on {target_card}!"

        if CARDS[card_name].get("ability") == "medic":
            valid_targets = [c for c in self.players[player_id]["graveyard"]
                             if not CARDS[c].get("hero", False) and CARDS[c].get("row") not in ["weather", "special",
                                                                                                "any"]]

            if valid_targets and not target_card:
                return True, f"REQ_CHAIN|{card_name}"

            if target_card:
                if target_card not in valid_targets:
                    return False, "Invalid graveyard target."

                self.players[player_id]["hand"].remove(card_name)
                self.players[player_id]["board"][row].append(card_name)

                self.players[player_id]["graveyard"].remove(target_card)
                self.players[player_id]["hand"].append(target_card)
                target_row = CARDS[target_card]["row"]

                self.current_turn = player_id
                success, inner_msg = self.play_card(player_id, target_card, target_row)

                if inner_msg.startswith("REQ_CHAIN|"):
                    return True, inner_msg
                else:
                    return True, f"Player {player_id} played {card_name} and revived {target_card}!"

            self.players[player_id]["hand"].remove(card_name)
            self.players[player_id]["board"][row].append(card_name)
            self.next_turn()
            return True, f"Player {player_id} played {card_name}!"

        if row == "special":
            ability = CARDS[card_name].get("ability")
            self.players[player_id]["hand"].remove(card_name)
            msg = f"Player {player_id} played {card_name}!"
            if ability == "scorch":
                self.apply_scorch()
                msg = f"Player {player_id} played Scorch! The strongest cards burned."
            self.next_turn()
            return True, msg

        if row == "weather":
            ability = CARDS[card_name].get("ability")
            self.players[player_id]["hand"].remove(card_name)

            if ability == "clear_weather":
                self.weather_zone = []
                msg = f"Player {player_id} played Clear Skies! The sun is out."
            else:
                if card_name not in self.weather_zone:
                    self.weather_zone.append(card_name)
                msg = f"Player {player_id} played {card_name}!"

            self.next_turn()
            return True, msg

        if CARDS[card_name].get("ability") == "spy":
            opp_id = 2 if player_id == 1 else 1

            self.players[player_id]["hand"].remove(card_name)
            self.players[opp_id]["board"][row].append(card_name)

            drawn_cards = 0
            for _ in range(2):
                if len(self.players[player_id]["deck"]) > 0:
                    drawn_card = self.players[player_id]["deck"].pop()
                    self.players[player_id]["hand"].append(drawn_card)
                    drawn_cards += 1

            self.next_turn()
            return True, f"Player {player_id} played a Spy and drew {drawn_cards} cards!"

        self.players[player_id]["hand"].remove(card_name)
        self.players[player_id]["board"][row].append(card_name)

        if CARDS[card_name].get("ability") == "melee_scorch":
            self.apply_melee_scorch(player_id)

        self.next_turn()
        return True, f"Player {player_id} played {card_name} in {row}."

    def pass_turn(self, player_id):
        if self.game_over:
            return False, "The game is already over!", None

        if player_id != self.current_turn:
            return False, "It is not your turn.", None

        self.players[player_id]["passed"] = True

        other_player = 2 if player_id == 1 else 1
        if self.players[other_player]["passed"]:
            return self.resolve_round()
        else:
            self.current_turn = other_player
            return True, f"Player {player_id} passed.", None

    def next_turn(self):
        other_player = 2 if self.current_turn == 1 else 1
        if not self.players[other_player]["passed"]:
            self.current_turn = other_player

    def resolve_round(self):
        p1_score = self.get_score(1)
        p2_score = self.get_score(2)

        msg = f"Round {self.round_number} Over! P1: {p1_score}, P2: {p2_score}. "
        round_winner = None

        if p1_score > p2_score:
            self.players[1]["rounds_won"] += 1
            msg += "Player 1 wins the round."
            round_winner = "p1"
            self.current_turn = 1

        elif p2_score > p1_score:
            self.players[2]["rounds_won"] += 1
            msg += "Player 2 wins the round."
            round_winner = "p2"
            self.current_turn = 2

        else:
            self.players[1]["rounds_won"] += 1
            self.players[2]["rounds_won"] += 1
            msg += "It's a draw! Both players get a crown."
            round_winner = "draw"

        if self.players[1]["rounds_won"] >= 2 or self.players[2]["rounds_won"] >= 2:
            self.game_over = True
            msg += " GAME OVER!"
            return True, msg, round_winner

        self.round_number += 1
        for p in [1, 2]:
            for r_name in ["melee", "ranged", "siege"]:
                self.players[p]["graveyard"].extend(self.players[p]["board"][r_name])
            self.players[p]["board"] = {"melee": [], "ranged": [], "siege": []}
            self.players[p]["horns"] = []
            self.players[p]["passed"] = False
        self.weather_zone = []

        return True, msg, round_winner

    def get_state_dict(self):
        """Returns the board state to be sent with JSON."""
        return {
            "turn": self.current_turn,
            "round": self.round_number,
            "p1_score": self.get_score(1),
            "p2_score": self.get_score(2),
            "p1_crowns": self.players[1]["rounds_won"],
            "p2_crowns": self.players[2]["rounds_won"],
            "p1_board": self.players[1]["board"],
            "p2_board": self.players[2]["board"],
            "weather_zone": self.weather_zone,
            "p1_horns": self.players[1]["horns"],
            "p2_horns": self.players[2]["horns"],
            "p1_graveyard": self.players[1]["graveyard"],
            "p2_graveyard": self.players[2]["graveyard"]
        }
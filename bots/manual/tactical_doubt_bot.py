import random
from bots.base import BotBase
from dubito.game_data import TurnData


class TacticalDoubtBot(BotBase):
    """
    Doubts when the previous player opened the round or played 3 cards;
    otherwise plays cards, bluffing randomly half the time.
    """

    def bluff_first_hand(self, p: TurnData) -> bool:    return random.choice([True, False])
    def maximize_first_hand(self, p: TurnData) -> bool: return True

    def should_doubt(self, p: TurnData) -> bool:
        return self.prev_player_started_turn(p) or p.n_cards_played == 3

    def bluff_regular(self, p: TurnData) -> bool:       return random.choice([True, False])
    def maximize_regular(self, p: TurnData) -> bool:    return True

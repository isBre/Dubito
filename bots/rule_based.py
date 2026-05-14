import random
from typing import Dict
from bots.base import BotBase


class AlwaysTruthful(BotBase):
    """Plays honestly whenever possible, doubts when it can't."""

    def bluff_first_hand(self, p: Dict) -> bool:   return False
    def maximize_first_hand(self, p: Dict) -> bool: return True
    def should_doubt(self, p: Dict) -> bool:        return not self.can_play_truthfully(p)
    def bluff_regular(self, p: Dict) -> bool:       return False
    def maximize_regular(self, p: Dict) -> bool:    return True


class MrNoDoubt(BotBase):
    """Never doubts. Plays honestly when possible, bluffs otherwise."""

    def bluff_first_hand(self, p: Dict) -> bool:   return False
    def maximize_first_hand(self, p: Dict) -> bool: return True
    def should_doubt(self, p: Dict) -> bool:        return False
    def bluff_regular(self, p: Dict) -> bool:       return False
    def maximize_regular(self, p: Dict) -> bool:    return True


class JustPutCards(BotBase):
    """Always bluffs with 3 cards."""

    def bluff_first_hand(self, p: Dict) -> bool:   return True
    def maximize_first_hand(self, p: Dict) -> bool: return True
    def should_doubt(self, p: Dict) -> bool:        return False
    def bluff_regular(self, p: Dict) -> bool:       return True
    def maximize_regular(self, p: Dict) -> bool:    return True


class RandomBoi(BotBase):
    """Everything random."""

    def bluff_first_hand(self, p: Dict) -> bool:   return random.choice([True, False])
    def maximize_first_hand(self, p: Dict) -> bool: return False

    def should_doubt(self, p: Dict) -> bool:
        if self.can_play_truthfully(p):
            return random.random() < 1/3   # 1 in 3: bluff / honest / doubt
        return random.choice([True, False]) # 50/50: doubt or bluff

    def bluff_regular(self, p: Dict) -> bool:       return random.choice([True, False])
    def maximize_regular(self, p: Dict) -> bool:    return False


class MrDoubt(BotBase):
    """Always doubts on regular turns."""

    def bluff_first_hand(self, p: Dict) -> bool:   return random.choice([True, False])
    def maximize_first_hand(self, p: Dict) -> bool: return True
    def should_doubt(self, p: Dict) -> bool:        return True
    def bluff_regular(self, p: Dict) -> bool:       return True   # unreachable
    def maximize_regular(self, p: Dict) -> bool:    return True   # unreachable


class StefaBot(BotBase):
    """Doubts when prev started the round or played 3 cards; otherwise plays."""

    def bluff_first_hand(self, p: Dict) -> bool:   return random.choice([True, False])
    def maximize_first_hand(self, p: Dict) -> bool: return True

    def should_doubt(self, p: Dict) -> bool:
        return self.prev_player_started_turn(p) or p.n_cards_played == 3

    def bluff_regular(self, p: Dict) -> bool:       return random.choice([True, False])
    def maximize_regular(self, p: Dict) -> bool:    return True

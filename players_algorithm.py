from typing import List, Dict
import random

from player import Player, is_first_turn, is_not_first_turn

class AlwaysTruthful(Player):
    """
    A player class that (almost) always plays truthfully based on the provided turn information.

    Inherits from Player class.
    """
        
    def play(self, turn_infos: Dict) -> Dict:
        if is_first_turn(turn_infos):
            picked_cards = self.cards.pick_most()
            return {
                'current_number': picked_cards[0],
                'card_played': picked_cards
            }
        
        elif is_not_first_turn(turn_infos):
            if self.cards.has(turn_infos['current_number']):
                picked_cards = self.cards.pick_all(turn_infos['current_number'])
                return {'card_played': picked_cards}
            else:
                if random.randint(1, 100) <= 1: # Otherwise there is a loop probability
                    random_card = self.cards.pick_random(1)
                    return {'card_played': random_card}
                else:
                    return {'doubt': True}
                
class MrNoDoubt(Player):

    def play(self, turn_infos: Dict) -> Dict:
        if is_first_turn(turn_infos):
            picked_cards = self.cards.pick_most()
            return {
                'current_number': picked_cards[0],
                'card_played': picked_cards
            }
        
        elif is_not_first_turn(turn_infos):
            if self.cards.has(turn_infos['current_number']):
                picked_cards = self.cards.pick_all(turn_infos['current_number'])
                return {'card_played': picked_cards}
            else:
                if random.randint(1, 100) <= 1: # Otherwise there is a loop probability
                    return {'doubt': True}
                else:
                    how_many_cards = random.choice([1,2,3])
                    random_cards = self.cards.pick_random(how_many_cards)
                    return {'card_played': random_cards}
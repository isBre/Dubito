import random
from typing import Dict
from player import PlayerAI


class AdptyBoi(PlayerAI):
    '''
    Adapt plays based on surrounding players
    '''
    def __init__(self, id: int) -> None:
        super().__init__(id)
        self.prev_honesty_prob = 0.5 # Higher when the previous player is honest
        self.next_doubt_prob = 0.5 # Higher when the next player doubt a lot
    
    def play(self, input_player: Dict) -> Dict:
        self.update(input_player = input_player)
        return super().play(input_player)
    
    def play_first_turn(self, input_player: Dict) -> Dict:
        if random.random() < self.next_doubt_prob:
            # Next player doubts a lot, let's play safe (honest)
            return self.play_truthfully(input_player, first_turn = True, uncertainty = False, maximize = True)
        else:
            # Next player is not doubting, let's play aggressive
            return self.bluff(input_player, first_turn = True, uncertainty = False, maximize = True)
    
    def play_regular_turn(self, input_player: Dict) -> Dict:
        if random.random() < self.prev_honesty_prob:
            # Prev player is honest
            if random.random() < self.next_doubt_prob:
                # Next player is doubting a lot, I should play safe somehow
                if self.can_play_truthfully(input_player):
                    # I can play truthfully
                    return self.play_truthfully(input_player, first_turn = False, uncertainty = False, maximize = True)
                # Ok now I need either to risk the bluff or to risk the doubt
                elif self.prev_honesty_prob > self.next_doubt_prob:
                    return self.bluff(input_player, first_turn = False, uncertainty = False, maximize = True)
                else:
                    return self.doubt(input_player, uncertainty = False)
            else:
                # Next player is not doubting a lot, i can play aggressive
                return self.bluff(input_player, first_turn = False, uncertainty = False, maximize = True)
        else:
            # Prev player is bluffing a lot
            return self.doubt(input_player, uncertainty = False)

    def update(self, input_player : Dict) -> None:
        if input_player['prev']['honest_times'] + input_player['prev']['dishonest_times'] > 0: 
            prev_honest_ratio = input_player['prev']['honest_times'] / (input_player['prev']['honest_times'] + input_player['prev']['dishonest_times'])
            self.prev_honesty_prob = min(1.00 - self.uncertainty_value, max(self.uncertainty_value, prev_honest_ratio))
        if input_player['next']['not_first_turns'] > 0:
            next_doubts_ratio = input_player['next']['doubts'] / input_player['next']['not_first_turns']
            self.next_doubt_prob = min(1.00 - self.uncertainty_value, max(self.uncertainty_value, next_doubts_ratio))



class SusBoi(PlayerAI):
    """
    Doubt with higher probability if the previous player plays a lot of cards
    Otherwise is honest
    """
    
    def play_first_turn(self, input_player: Dict) -> Dict:
        return self.play_truthfully(input_player, first_turn = True, uncertainty = True, maximize = True)
    
    def play_regular_turn(self, input_player: Dict) -> Dict:
        if ((input_player['n_cards_played'] == 1 and random.random() < 0.3) or
            (input_player['n_cards_played'] == 2 and random.random() < 0.6) or 
            (input_player['n_cards_played'] == 3 and random.random() < 0.9)):
            return self.doubt(input_player, uncertainty = False)
        else:
            # If you have the correct number play truthfully otherwise doubt
            if self.can_play_truthfully(input_player):
                return self.play_truthfully(input_player, first_turn = False, uncertainty = True, maximize = True)
            else:
                return self.doubt(input_player, uncertainty = True)



class UsualBot(PlayerAI):
    """
    Doubt with higher probability if the previous player plays a lot of cards
    Doubt when the previous player has 0 cards
    Don't doubt when the prev_player start
    Bluffs 67% of the times
    """
    
    def play_first_turn(self, input_player: Dict) -> Dict:
        if random.random() < 0.67:
            return self.bluff(input_player, first_turn = True, uncertainty = False, maximize = True)
        else:
            return self.play_truthfully(input_player, first_turn = True, uncertainty = True, maximize = True)
    
    def play_regular_turn(self, input_player: Dict) -> Dict:
        
        if self.prev_player_started_turn(input_player):
            # Prev_Player was first
            if random.random() < 0.67:
                return self.bluff(input_player, first_turn = False, uncertainty = False, maximize = True)
            else:
                return self.play_truthfully(input_player, first_turn = False, uncertainty = True, maximize = True)
        
        if input_player['prev']['n_cards'] == 0:
            return self.doubt(input_player, uncertainty = False)
        
        if ((input_player['n_cards_played'] == 1 and random.random() < 0.3) or
            (input_player['n_cards_played'] == 2 and random.random() < 0.6) or 
            (input_player['n_cards_played'] == 3 and random.random() < 0.9)):
            return self.doubt(input_player, uncertainty = False)
        else:
            if random.random() < 0.67:
                return self.bluff(input_player, first_turn = False, uncertainty = False, maximize = False)
            else:
                return self.play_truthfully(input_player, first_turn = False, uncertainty = True, maximize = True)


class RiskCounter(PlayerAI):
    """
    Aggressive when the streak is low otherwise Honest
    Calculate the risk_value considering: next_player_n_cards, my_n_cards and streak
    """
    def __init__(self, id: int) -> None:
        super().__init__(id)
        self.risk = 0.01 # Low-Risk: play aggressive, High-Risk play safe
    
    def play_first_turn(self, input_player: Dict) -> Dict:
        self.update_risk(input_player, first_turn = True)
        if random.random() < self.risk:
            return self.bluff(input_player, first_turn = True, uncertainty = False, maximize = True)
        else:
            return self.play_truthfully(input_player, first_turn = True, uncertainty = True, maximize = True)
    
    def play_regular_turn(self, input_player: Dict) -> Dict:
        self.update_risk(input_player, first_turn = False)
        
        if input_player['prev']['n_cards'] == 0:
            return self.doubt(input_player, uncertainty = False)
        
        if random.random() < self.risk:
            return self.bluff(input_player, first_turn = True, uncertainty = False, maximize = True)
        else:
            if self.can_play_truthfully(input_player):
                return self.play_truthfully(input_player, first_turn = False, uncertainty = True, maximize = True)
            else:
                return self.doubt(input_player, uncertainty = False)
    
    def update_risk(self, input_player : Dict, first_turn : bool) -> None:
        if first_turn:
            if self.all_equal(): 
                self.risk = 1.0 # If u have equal cards just win bro
            else:
                prev_player_cards = input_player['next']['n_cards']
                self.risk = max(0, min(0.99, - (1/30)*prev_player_cards**2 + 1))
        else:
            self.risk = max(0, min(0.99, (1/40) * input_player['board_cards'] ** 2))
            
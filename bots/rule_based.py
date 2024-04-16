import random
from typing import Dict
from player import PlayerAI



class AlwaysTruthful(PlayerAI):
    """
    A player that (almost) always plays truthfully based on the provided turn information.
    """
        
    def play_first_turn(self, input_player: Dict) -> Dict:
        return self.play_truthfully(input_player, first_turn = True, uncertainty = True, maximize = True)

    def play_regular_turn(self, input_player: Dict) -> Dict:
        # If you have the correct number play truthfully otherwise doubt
        if self.can_play_truthfully(input_player):
            return self.play_truthfully(input_player, first_turn = False, uncertainty = True, maximize = True)
        else:
            return self.doubt(input_player, uncertainty = True)



class MrNoDoubt(PlayerAI):
    """
    A player that (almost) never doubt, it just try to put cards on the field.
    If can play correctly, he will.
    """
    
    def play_first_turn(self, input_player: Dict) -> Dict:
        return self.play_truthfully(input_player, first_turn = True, uncertainty = True, maximize = True)
    
    def play_regular_turn(self, input_player: Dict) -> Dict:
        # If you have the correct number play truthfully otherwise bluff
        if self.can_play_truthfully(input_player):
            return self.play_truthfully(input_player, first_turn = False, uncertainty = True, maximize = True)
        else:
            return self.bluff(input_player, first_turn = False, uncertainty = True, maximize = False)



class JustPutCards(PlayerAI):
    """
    A player that want to maximize the amount of cards placed in the field.
    Will always bluff placing 3 cards.
    """

    def play_first_turn(self, input_player: Dict) -> Dict:
        return self.bluff(input_player, first_turn = True, uncertainty = True, maximize = True)

    def play_regular_turn(self, input_player: Dict) -> Dict:
        return self.bluff(input_player, first_turn = False, uncertainty = True, maximize = True)



class RandomBoi(PlayerAI):
    """
    Just Everything random.
    """

    def play_first_turn(self, input_player: Dict) -> Dict:
        if random.choice([True, False]):
            return self.bluff(input_player, first_turn = True, uncertainty = False, maximize = False)
        else:
            return self.play_truthfully(input_player, first_turn = True, uncertainty = False, maximize = False)

    def play_regular_turn(self, input_player: Dict) -> Dict:
        if self.can_play_truthfully(input_player):
            move = random.choice(['bluff', 'truthful', 'doubt'])
            if move == 'bluff': return self.bluff(input_player, first_turn = False, uncertainty = False, maximize = False)
            elif move == 'truthful': return self.play_truthfully(input_player, first_turn = False, uncertainty = False, maximize = False)
            elif move == 'doubt': return self.doubt(input_player, uncertainty = False)
        elif random.choice([True, False]):
            return self.doubt(input_player, uncertainty = False)
        else:
            return self.bluff(input_player, first_turn = False, uncertainty = False, maximize = False)



class MrDoubt(PlayerAI):
    """
    A player that (almost) always doubt.
    """

    def play_first_turn(self, input_player: Dict) -> Dict:
        if random.choice([True, False]):
            return self.bluff(input_player, first_turn = True, uncertainty = False, maximize = True)
        else:
            return self.play_truthfully(input_player, first_turn = True, uncertainty = False, maximize = True)
        
    def play_regular_turn(self, input_player: Dict) -> Dict:
        return self.doubt(input_player, uncertainty = True)



class StefaBot(PlayerAI):
    """
    If prev_player was playing first turn, then doubt
    If prev_player was not playing first turn, then plays (normally or bluffs) if prev_player has played 2 or 1. 
    Bot Stefano doubts if prev_player has played 3 cards.
    """

    def play_first_turn(self, input_player: Dict) -> Dict:
        if random.choice([True, False]):
            return self.bluff(input_player, first_turn = True, uncertainty = False, maximize = True)
        else:
            return self.play_truthfully(input_player, first_turn = True, uncertainty = False, maximize = True)
        
    def play_regular_turn(self, input_player: Dict) -> Dict:
        if self.prev_player_started_turn(input_player) or input_player['n_cards_played'] == 3:
            return self.doubt(input_player, uncertainty = True)
        elif self.can_play_truthfully(input_player):
            if random.choice([True, False]):
                return self.play_truthfully(input_player, first_turn = False, uncertainty = False, maximize = True)
        return self.bluff(input_player, first_turn = False, uncertainty = False, maximize = True)    
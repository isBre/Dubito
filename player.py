from abc import ABC, abstractmethod
from typing import List, Dict
import random
from hand import Hand


class Player(ABC):
    """
    Abstract base class representing a player in a game.
    """

    def __init__(self, id: int) -> None:
        """
        Initializes a player with an empty hand, an ID, and default game position.

        Args:
            id (int): The unique identifier for the player.
        """
        self.cards: Hand = Hand(hand = [])
        self.id = id
    
    @abstractmethod
    def play(self, turn_infos: Dict) -> Dict:
        """
        Abstract method representing the player's move during their turn.
        Must be implemented by subclasses.

        Args:
            turn_infos (Dict): Information about the current game state.

        Returns:
            OutputPlayerRecorder: Information about the player's move.
        """
        pass

    def add_cards(self, new_cards: List) -> None:
        """
        Adds new cards to the player's hand.

        Args:
            new_cards (List): List of new cards to be added to the player's hand.
        """
        self.cards.add(new_cards)

    def discard_cards(self) -> List[int]:
        """
        Discards cards from the player's hand.

        Returns:
            List[int]: List of discarded card values.
        """
        return self.cards.discard(amount = 4)

    def has_no_cards(self) -> bool:
        """
        Checks if the player has no cards left in their hand.

        Returns:
            bool: True if the player has no cards, False otherwise.
        """
        return not len(self.cards)
    
    def n_cards(self) -> int:
        """
        Returns the number of cards in the player's hand.

        Returns:
            int: Number of cards in the player's hand.
        """
        return len(self.cards)
    
    def reset(self) -> None:
        """
        Resets the player's hand to an empty state.
        """
        self.cards = Hand(hand = [])
        
    def all_equal(self) -> bool:
        """
        Check if all cards in the player's hand are the same.

        Returns:
            bool: True if all cards in the hand are the same, False otherwise.
        """
        return self.cards.all_equal()



class PlayerAI(Player):
    """
    Base class for AI player behavior.
    """
    def __init__(self, id: int) -> None:
        """
        Initializes an AI player with an ID and sets the uncertainty value.

        Args:
            id (int): The unique identifier for the AI player.
        """
        self.uncertainty_value = 0.05
        super().__init__(id)
        
    def can_play_truthfully(self, input_player: Dict) -> bool:
        """
        Checks if the AI player can play truthfully based on the current game state.

        Args:
            input_player (Dict): Information provided to the AI about the game state.

        Returns:
            bool: True if the AI player can play truthfully, False otherwise.
        """
        return self.cards.has(input_player['current_number'])
    
    def is_first_turn(self, input_player: Dict) -> bool:
        """
        Checks if it's the first turn of the game.

        Args:
            input_player (Dict): Information provided to the AI about the game state.

        Returns:
            bool: True if it's the first turn, False otherwise.
        """
        return input_player['board_cards'] == 0
    
    def prev_player_started_turn(self, input_player: Dict) -> bool:
        """
        Checks if the previous player started the current turn.

        Args:
            input_player (Dict): Information provided to the AI about the game state.

        Returns:
            bool: True if the previous player started the turn, False otherwise.
        """
        return input_player['n_cards_played'] == input_player['board_cards']

    def play(self, input_player: Dict) -> Dict:
        """
        Main method to determine the AI player's move during its turn.

        Args:
            input_player (Dict): Information provided to the AI about the game state.

        Returns:
            Dict: Information about the AI player's move.
        """
        if self.is_first_turn(input_player):
            return self.play_first_turn(input_player)
        else:
            return self.play_regular_turn(input_player)

    def play_first_turn(self, input_player: Dict) -> Dict:
        """
        Abstract method representing the AI player's move on the first turn.
        Must be implemented by subclasses.

        Args:
            input_player (Dict): Information provided to the AI about the game state.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """
        raise NotImplementedError("Subclasses must implement play_first_turn method.")

    def play_regular_turn(self, input_player: Dict) -> Dict:
        """
        Abstract method representing the AI player's move on regular turns.
        Must be implemented by subclasses.

        Args:
            input_player (Dict): Information provided to the AI about the game state.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """
        raise NotImplementedError("Subclasses must implement play_regular_turn method.")

    def doubt(self, input_player: Dict, uncertainty : bool) -> Dict:
        '''
        Doubt Decision for AI Player

        Determines whether the player should doubt the previous player's move.

        Parameters:
            input_player (Dict): Information provided to the AI about the game state.
            uncertainty (bool): Flag indicating uncertainty about the previous player's move.

        Returns:
            Dict: Decision dictionary containing:
                - doubt: Boolean indicating whether to doubt.
                - number: Number declared by the player (if first hand).
                - cards: Cards played by the player.
        '''
        if uncertainty:
            if random.random() > self.uncertainty_value:
                return {'doubt': True, 'number': None, 'cards': None}
            else:
                if self.can_play_truthfully(input_player):
                    if random.choice([True, False]):
                        return self.play_truthfully(input_player, first_turn = False, uncertainty = False, maximize = False)
                return self.bluff(input_player, first_turn = False, uncertainty = False, maximize = False)
        else:
            return {'doubt': True, 'number': None, 'cards': None}
    
    def bluff(self, input_player: Dict, first_turn: bool, uncertainty : bool, maximize: bool) -> Dict:
        '''
        Bluff Decision for AI Player

        Determines whether the player should bluff by playing cards.

        Parameters:
            input_player (Dict): Information provided to the AI about the game state.
            first_turn (bool): Flag indicating if it's the player's first turn.
            uncertainty (bool): Flag indicating uncertainty about the previous player's move.
            maximize (bool): Flag indicating whether to maximize the bluff.

        Returns:
            Dict: Decision dictionary containing:
                - doubt: Boolean indicating whether to doubt.
                - number: Number declared by the player (if first turn).
                - cards: Cards played by the player.
        '''
        if uncertainty:
            if not random.random() > self.uncertainty_value:
                if first_turn:
                    return self.play_truthfully(input_player, first_turn = True, uncertainty = False, maximize = maximize)
                else:
                    return self.doubt(input_player, uncertainty = False)
        
        if first_turn:
            how_many_cards = 3 if maximize else random.choice([1, 2, 3])
            random_cards = self.cards.pick_random(how_many_cards)
            random_number = random.choice(input_player['playing_cards'])
        else:
            random_cards = self.cards.pick_random(3) if maximize else self.cards.pick_random(random.choice([1, 2, 3]))

        return {'doubt': False, 'number': random_number if first_turn else None, 'cards': random_cards}
    
    def play_truthfully(self, input_player: Dict, first_turn : bool, uncertainty : bool, maximize : bool) -> Dict:
        '''
        Truthful Play Decision for AI Player

        Determines whether the player should play truthfully by selecting cards.

        Parameters:
            input_player (Dict): Information provided to the AI about the game state.
            first_turn (bool): Flag indicating if it's the player's first turn.
            uncertainty (bool): Flag indicating uncertainty about the previous player's move.
            maximize (bool): Flag indicating whether to maximize the truthfulness.

        Returns:
            Dict: Decision dictionary containing:
                - doubt: Boolean indicating whether to doubt.
                - number: Number declared by the player (if first turn).
                - cards: Cards played by the player.
        '''
        if uncertainty:
            if not random.random() > self.uncertainty_value:
                if first_turn:
                    return self.bluff(input_player, first_turn = True, uncertainty = False, maximize = maximize)
                else:
                    if random.choice([True, False]):
                        return self.doubt(input_player, uncertainty = False)
                    else:
                        return self.bluff(input_player, first_turn = False, uncertainty = False, maximize = maximize)
        
        if first_turn:
            if maximize: picked_cards = self.cards.pick_most()
            else:
                picked_cards = self.cards.pick_random()
            return {'doubt': False, 'number': picked_cards[0], 'cards': picked_cards}
        else:
            if maximize: picked_cards = self.cards.pick_all(input_player['current_number'])
            else:
                card_count = self.cards.count(input_player['current_number'])
                amount_to_choice = list(range(1, card_count + 1))
                cards_number = random.choice(amount_to_choice)
                picked_cards = self.cards.pick(input_player['current_number'], cards_number)
            return {'doubt': False, 'number': None, 'cards': picked_cards}
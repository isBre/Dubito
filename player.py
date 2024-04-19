from abc import ABC, abstractmethod
from typing import List, Dict
import random
from collections import Counter

class Hand:
    def __init__(self, hand: List[int]) -> None:
        """
        Initialize a Hand object with a list of cards.

        Args:
            hand (List[int]): List of card values.
        """
        self.hand = hand
        self.hand.sort()

    def pick(self, card_number: int, card_amount: int) -> List[int]:
        """
        Pick a specific number of cards with the given card_number from the hand.

        Args:
            card_number (int): The card value to pick.
            card_amount (int): The number of cards to pick.

        Returns:
            List[int]: List of picked cards with the specified card number.
        """
        if card_amount > len(self.hand):
            raise ValueError("Card amount exceeds the number of cards in the hand")

        picked_cards = []
        remaining_cards = self.hand[:]
        for card in self.hand:
            if card == card_number and card_amount > 0:
                picked_cards.append(card)
                remaining_cards.remove(card)
                card_amount -= 1
        self.hand = remaining_cards
        return picked_cards
    
    def pick_idx(self, indexes: List[int]) -> List[int]:
        """
        Pick cards from the hand at specified indexes and remove them.

        Args:
            indexes (List[int]): List of indexes to pick cards from.

        Returns:
            List[int]: List of picked cards.
        """
        picked_cards = [self.hand[i] for i in indexes]
        self.hand = [self.hand[i] for i in range(len(self.hand)) if i not in indexes]
        return picked_cards
    
    def pick_all(self, number: int) -> List[int]:
        """
        Remove all occurrences of the specified number from the player's hand.

        Args:
            number (int): The number to be removed from the hand.

        Returns:
            List[int]: List of removed numbers (equal to the specified number) from the hand.
        """
        card_amount = self.hand.count(number)
        self.hand = [num for num in self.hand if num != number]
        return [number] * card_amount
    
    def pick_random(self, amount: int = 1) -> List[int]:
        """
        Randomly picks a specified number of elements from the player's hand,
        removes one occurrence of each picked element, and returns the picked elements.

        Args:
            amount (int, optional): The number of elements to pick randomly from the hand.
                Defaults to 1.

        Returns:
            List[int]: A list of randomly picked elements from the hand.

        Raises:
            ValueError: If the specified amount is greater than the number of unique elements in the hand.
        """
        random_numbers = random.sample(self.hand, min(amount, len(self.hand)))
        for n in random_numbers:
            if n in self.hand:
                self.hand.remove(n)
        return random_numbers
    
    def pick_most(self) -> List[int]:
        """
        Pick the most common card(s) from the player's hand and return them.

        Returns:
            List[int]: List of picked cards with the most common card number(s).
        """
        counter = self.count_all()
        most_common_element, card_amount = counter.most_common(1)[0]
        picked_cards = self.pick(most_common_element, card_amount)
        return picked_cards

    def add(self, cards: List[int]) -> None:
        """
        Add a list of cards to the hand.

        Args:
            cards (List[int]): List of cards to add to the hand.
        """
        self.hand += cards
        self.hand.sort()

    def count_all(self) -> Counter:
        """
        Count the occurrences of each card value in the hand.

        Returns:
            Counter: A Counter object with card counts.
        """
        return Counter(self.hand)
    
    def count(self, number: int) -> int:
        """
        Count the occurrences of a specific card value in the hand.

        Args:
            number (int): The card value to count.

        Returns:
            int: The number of occurrences of the specified card value in the hand.
        """
        return self.hand.count(number)

    def discard(self, amount = 4) -> List[int]:
        """
        Discard cards that appear a specific number of times in the hand.

        Args:
            amount (int): The number of times a card must appear to be discarded.

        Returns:
            List[int]: List of discarded card values.
        """
        occurrences = Counter(self.hand)
        elements_to_remove = [num for num, count in occurrences.items() if count >= amount]
        self.hand = [num for num in self.hand if num not in elements_to_remove]
        return elements_to_remove
    
    def has(self, number: int) -> bool:
        """
        Checks if the specified number is present in the player's hand.

        Args:
            number (int): The number to check for in the player's hand.

        Returns:
            bool: True if the number is present in the hand, False otherwise.
        """
        return number in self.hand

    def __len__(self) -> int:
        """
        Get the number of cards in the hand.

        Returns:
            int: Number of cards in the hand.
        """
        return len(self.hand)

    def __str__(self) -> str:
        """
        Get a string representation of the hand.

        Returns:
            str: String representation of the hand.
        """
        return str(self.hand)


class Player(ABC):
    """
    Abstract base class representing a player in a card game.

    Attributes:
        cards (Hand): The player's hand of cards.
        id (int): The unique identifier for the player.
        game_position (int): The position of the player in the game.

    Methods:
        play(turn_infos: Dict) -> Dict:
            Abstract method representing the player's move during their turn.
            Must be implemented by subclasses.
        add_cards(new_cards: List):
            Adds new cards to the player's hand.
        discard_cards() -> List[int]:
            Discards cards from the player's hand.
        has_no_cards() -> bool:
            Checks if the player has no cards left in their hand.
        n_cards() -> int:
            Returns the number of cards in the player's hand.
        reset():
            Resets the player's hand.
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
        Check if the player contain the same cards
        """
        if not self.cards:
            return True
        first_card = self.cards.hand[0]
        return all(card == first_card for card in self.cards.hand)



class PlayerAI(Player):
    """
    Base class for AI player behavior.
    """
    def __init__(self, id: int) -> None:
        self.uncertainty_value = 0.05
        super().__init__(id)
        
    def can_play_truthfully(self, input_player: Dict) -> Dict:
        return self.cards.has(input_player['current_number'])
    
    def is_first_turn(self, input_player : Dict) -> bool:
        return input_player['board_cards'] == 0
    
    def prev_player_started_turn(self, input_player : Dict) -> bool:
        return input_player['n_cards_played'] == input_player['board_cards']

    def play(self, input_player: Dict) -> Dict:
        if self.is_first_turn(input_player):
            return self.play_first_turn(input_player)
        else:
            return self.play_regular_turn(input_player)

    def play_first_turn(self, input_player: Dict) -> Dict:
        raise NotImplementedError("Subclasses must implement play_first_turn method.")

    def play_regular_turn(self, input_player: Dict) -> Dict:
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
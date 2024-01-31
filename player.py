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

    def pick(self, card_number: int, card_amount: int) -> List[int]:
        """
        Pick a specific number of cards with the given card_number from the hand.

        Args:
            card_number (int): The card value to pick.
            card_amount (int): The number of cards to pick.

        Returns:
            List[int]: List of picked cards with the specified card number.
        """
        picked_cards = [card_number] * card_amount
        self.hand = [card for card in self.hand if card != card_number]
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
        update(player_name: str, was_honest: bool):
            Updates the player's information based on the game's outcome.
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
        initial_infos(game_position: int):
            Sets the initial game position for the player.
    """

    def __init__(self, id: int) -> None:
        """
        Initializes a player with an empty hand, an ID, and default game position.

        Args:
            id (int): The unique identifier for the player.
        """
        self.cards: Hand = Hand(hand=[])
        self.id = id
        self.game_position = -1
    
    @abstractmethod
    def play(self, turn_infos: Dict) -> Dict:
        """
        Abstract method representing the player's move during their turn.
        Must be implemented by subclasses.

        Args:
            turn_infos (Dict): Information about the current game state.

        Returns:
            Dict: Information about the player's move.
        """
        pass

    def update(self, player_name: str, was_honest: bool) -> None:
        """
        Updates the player's information based on the game's outcome.

        Args:
            player_name (str): The name of the player being updated.
            was_honest (bool): Whether the player was honest in the game.
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
        return self.cards.discard(amount=4)

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
        self.cards = Hand(hand=[])

    def initial_infos(self, game_position: int) -> None:
        """
        Sets the initial game position for the player.

        Args:
            game_position (int): The position of the player in the game.
        """
        self.game_position = game_position

def is_first_turn(turn_infos: Dict) -> bool:
    """
    Check if it is the first turn of the game based on the provided turn information.

    Args:
        turn_infos (Dict): Dictionary containing information about the current turn.

    Returns:
        bool: True if it is the first turn, False otherwise.
    """
    return not(turn_infos['board']['n_cards'] and 
               turn_infos['prev']['n_cards_placed'] and 
               turn_infos['current_number'])

def is_not_first_turn(turn_infos: Dict) -> bool:
    """
    Check if it is not the first turn of the game based on the provided turn information.

    Args:
        turn_infos (Dict): Dictionary containing information about the current turn.

    Returns:
        bool: True if it is not the first turn, False otherwise.
    """
    return (turn_infos['board']['n_cards'] and 
            turn_infos['prev']['n_cards_placed'] and 
            turn_infos['current_number'])

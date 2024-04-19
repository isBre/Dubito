from typing import List
from collections import Counter
import random


class Hand:
    """
    Represents a hand of cards.

    Attributes:
        hand (List[int]): List of card values in the hand.
    """

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
    
    def all_equal(self) -> bool:
        """
        Check if all cards in the player's hand are the same.

        Returns:
            bool: True if all cards in the hand are the same, False otherwise.
        """
        if not self.hand:
            return True
        first_card = self.hand[0]
        return all(card == first_card for card in self.hand)

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

"""
Player representation for the card game.
"""

from .card import Card

class Player:
    def __init__(self, username, websocket):
        self.username = username
        self.websocket = websocket
        self.hand = []  # List of cards
        self.is_connected = True
    
    def add_card(self, card: Card):
        """Add a card object to the player's hand."""
        self.hand.append(card)
    
    def remove_card(self, card_str: str) -> Card | None:
        """Remove a card from the player's hand based on its string representation.
           Returns the removed Card object or None if not found.
        """
        for i, card in enumerate(self.hand):
            if str(card) == card_str:
                return self.hand.pop(i)
        return None
    
    def has_card(self, card_str: str) -> bool:
        """Check if player has the specified card (by string)."""
        return any(str(card) == card_str for card in self.hand)
    
    def get_card_from_str(self, card_str: str) -> Card | None:
        """Find and return the Card object corresponding to the string representation.
           Returns None if the card is not in the hand.
        """
        for card in self.hand:
            if str(card) == card_str:
                return card
        return None
    
    def get_hand_as_strings(self) -> list[str]:
        """Return the player's hand as a list of strings."""
        return [str(card) for card in self.hand]
    
    def calculate_hand_value(self) -> int:
        """Calculate the total point value of the cards in the hand (Crazy Eights scoring)."""
        total_value = 0
        for card in self.hand:
            total_value += card.get_points()
        return total_value
    
    def can_play(self, top_card_value: str, required_suit: object) -> bool:
        """Check if the player has any playable card.

        Args:
            top_card_value: The value string of the top discard card (e.g., 'K', '7').
            required_suit: The Suit enum member that must be matched (could be the
                           top card's suit or a declared suit after an 8).

        Returns:
            True if the player has at least one playable card, False otherwise.
        """
        for card in self.hand:
            # An 8 is always playable
            if card.value == '8':
                return True
            # Check if card matches the required suit or the top card's value
            if card.suit == required_suit or card.value == top_card_value:
                return True
        return False

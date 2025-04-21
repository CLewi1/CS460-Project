"""
Player representation for the card game.
"""

class Player:
    def __init__(self, username, websocket):
        self.username = username
        self.websocket = websocket
        self.hand = []  # List of cardsa
        self.is_connected = True
    
    def add_card(self, card):
        """Add a card to the player's hand."""
        self.hand.append(card)
    
    def remove_card(self, card_str):
        """Remove a card from the player's hand."""
        for i, card in enumerate(self.hand):
            if str(card) == card_str:
                return self.hand.pop(i)
        return None
    
    def has_card(self, card_str):
        """Check if player has the specified card."""
        return any(str(card) == card_str for card in self.hand)
    
    def get_hand_as_strings(self):
        """Return the player's hand as a list of strings."""
        return [str(card) for card in self.hand]

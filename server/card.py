"""
Card and deck implementation for the card game.
"""
import random
from enum import Enum

class Suit(Enum):
    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"
    SPADES = "spades"

class Card:
    def __init__(self, value, suit):
        self.value = value # Keep value as string ('2', 'K', 'A', etc.)
        self.suit = suit # Suit enum

    def __str__(self):
        # Use more standard representation like 'KH' (King of Hearts) or '8S' (8 of Spades)
        value_map = {'10': 'T', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}
        display_value = value_map.get(self.value, self.value) # Use 'T' for 10, others as is
        suit_map = {Suit.HEARTS: 'H', Suit.DIAMONDS: 'D', Suit.CLUBS: 'C', Suit.SPADES: 'S'}
        return f"{display_value}{suit_map[self.suit]}"

    def to_dict(self):
        # Send the string representation over the network
        return str(self)

    def get_points(self):
        """Get the point value of the card for Crazy Eights scoring."""
        if self.value == '8':
            return 50
        elif self.value in ['K', 'Q', 'J', 'T']: # T represents 10
            return 10
        elif self.value == 'A':
            return 1
        else:
            try:
                return int(self.value) # 2 through 9
            except ValueError:
                return 0 # Should not happen with standard deck

class Deck:
    def __init__(self):
        self.cards = []
        self.reset()
    
    def reset(self):
        """Reset the deck with all 52 cards."""
        self.cards = []
        # Use 'T' for 10 internally for consistency with display? Or keep '10'? Let's keep '10' for now.
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        for suit in Suit:
            for value in values:
                # Ensure suit is the Enum member, not the string
                self.cards.append(Card(value, suit))
    
    def shuffle(self):
        """Shuffle the deck."""
        random.shuffle(self.cards)
    
    def deal(self, num_cards=1):
        """Deal a specified number of cards from the deck. Returns a list of Card objects."""
        if num_cards > len(self.cards):
            # If not enough cards, deal remaining ones
            num_cards = len(self.cards)

        dealt_cards = []
        for _ in range(num_cards):
            if self.cards: # Check if deck is not empty
                 dealt_cards.append(self.cards.pop())
            else:
                break # Stop if deck runs out

        return dealt_cards

    def is_empty(self):
        """Check if the deck (draw pile) is empty."""
        return len(self.cards) == 0

# Add a function to parse card string back to Card object if needed (maybe in Game class)
def card_from_str(card_str):
    """Convert a card string like 'KH' or '8S' back to a Card object."""
    if not card_str or len(card_str) < 2:
        return None

    value_str = card_str[:-1]
    suit_char = card_str[-1]

    value_map_rev = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}
    value = value_map_rev.get(value_str, value_str)

    suit_map_rev = {'H': Suit.HEARTS, 'D': Suit.DIAMONDS, 'C': Suit.CLUBS, 'S': Suit.SPADES}
    suit = suit_map_rev.get(suit_char)

    if suit is None or value not in ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']:
        return None # Invalid card string

    return Card(value, suit)

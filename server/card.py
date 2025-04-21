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
        self.value = value
        self.suit = suit
    
    def __str__(self):
        return f"{self.value} of {self.suit.value}"
    
    def to_dict(self):
        return str(self)

class Deck:
    def __init__(self):
        self.cards = []
        self.reset()
    
    def reset(self):
        """Reset the deck with all 52 cards."""
        self.cards = []
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        for suit in Suit:
            for value in values:
                self.cards.append(Card(value, suit))
    
    def shuffle(self):
        """Shuffle the deck."""
        random.shuffle(self.cards)
    
    def deal(self, num_cards=1):
        """Deal a specified number of cards from the deck."""
        if num_cards > len(self.cards):
            raise ValueError("Not enough cards in the deck")
        
        dealt_cards = []
        for _ in range(num_cards):
            dealt_cards.append(self.cards.pop())
        
        return dealt_cards

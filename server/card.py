import random
from enum import Enum

class Suit(Enum):
    HEARTS = "Hearts"
    DIAMONDS = "Diamonds"
    CLUBS = "Clubs"
    SPADES = "Spades"

class Rank(Enum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 'Jack'
    QUEEN = 'Queen'
    KING = 'King'
    ACE = 'Ace'

class Card:
    def __init__(self, suit: Suit, rank: Rank):
        self.suit = suit
        self.rank = rank

    def __str__(self):
        return f"{self.rank.value} of {self.suit.value}"
    
    def to_dict(self):
        return str(self)

class Deck:
    def __init__(self):
        self.cards = []
        self.reset()

    def reset(self):
        self.cards = []
        for suit in Suit:
            for rank in Rank:
                self.cards.append(Card(suit, rank))

    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self, num_cards=1):
        if num_cards > len(self.cards):
            raise ValueError("Not enough cards in the deck to deal.")
        
        dealt_cards = []
        for _ in range(num_cards):
            dealt_cards.append(self.cards.pop())

        return dealt_cards
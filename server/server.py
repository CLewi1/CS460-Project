from card import Card, Suit, Rank, Deck
from player import Player

def main():
    # Example of importing and testing a class
    # from your_module import YourClass
    # instance = YourClass()
    # result = instance.some_method()
    # print(f"Test result: {result}")
    
    print("Running tests...\n")
    
    # Card class tests

    print("==== Card Class Tests ====\n")

    # Test creating a card
    card = Card(Suit.HEARTS, Rank.ACE)
    print(f"Created card: {card}")

    # Test card to_dict method
    card_dict = card.to_dict()
    print(f"Card to_dict: {card_dict}")

    # Test deck creation
    deck = Deck()
    print(f"Deck created with {len(deck.cards)} cards.")

    # Test deck shuffle
    deck.shuffle()
    print("Deck shuffled.")

    # Test dealing cards
    dealt_cards = deck.deal(5)
    print(f"Dealt cards: {[str(card) for card in dealt_cards]}")

    # Test dealing more cards than available
    try:
        deck.deal(55)
    except ValueError as e:
        print(f"Expected error: {e}")

    # Test deck reset
    deck.reset()
    print(f"Deck reset, now has {len(deck.cards)} cards.")

    # Player class tests
    print("\n==== Player Class Tests ====\n")
    

    
    print("Tests completed")

if __name__ == "__main__":
    main()
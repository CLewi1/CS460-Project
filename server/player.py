class Player:
    def __init__(self, username, websocket, score):
        self.username = username
        self.websocket = websocket
        self.score = score
        self.hand = []
        self.is_connected = True

    def add_card(self, card):
        self.hand.append(card)

    def remove_card(self, card_str):
        for i, card in enumerate(self.hand):
            if str(card) == card_str:
                return self.hand.pop(i)
        return None
    
    def has_card(self, card_str):
        return any(str(card) == card_str for card in self.hand)
    
    def get_hand_as_strings(self):
        return [str(card) for card in self.hand]
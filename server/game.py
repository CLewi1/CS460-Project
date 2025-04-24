"""
Game logic for the card game.
"""
import asyncio
import json
import random
from .card import Deck, Card, Suit, card_from_str
from .player import Player

class Game:
    def __init__(self):
        self.players = {}  # username -> Player object
        self.deck = Deck()
        self.started = False
        self.current_turn_index = 0
        self.player_order = []  # List of usernames in turn order
        self.discard_pile = []  # Stores Card objects
        self.current_suit = None  # For when an 8 is played
        self.game_over_data = None  # Stores winner and scores

    def add_player(self, username, websocket):
        """Add a player to the game."""
        if username in self.players:
            return False
        self.players[username] = Player(username, websocket)
        return True

    def remove_player(self, username):
        """Remove a player from the game."""
        if username in self.players:
            player_was_current = (username == self.get_current_player())
            original_player_count = len(self.player_order)

            del self.players[username]
            if username in self.player_order:
                try:
                    removed_index = self.player_order.index(username)
                    self.player_order.remove(username)
                    if self.started and len(self.player_order) > 0:
                        if removed_index < self.current_turn_index:
                            self.current_turn_index = (self.current_turn_index - 1) % len(self.player_order)
                        elif removed_index == self.current_turn_index:
                            self.current_turn_index %= len(self.player_order)
                except ValueError:
                    pass

            if self.started and len(self.player_order) < 2 and original_player_count >= 2:
                self.end_game(blocked=True)

            return True, player_was_current
        return False, False

    def start_game(self):
        """Start the game, shuffle and deal cards according to Crazy Eights rules."""
        if len(self.players) < 2:
            return False, "Need at least 2 players to start"
        if self.started:
            return False, "Game already in progress"

        self.started = True
        self.deck.reset()
        self.deck.shuffle()
        self.discard_pile = []
        self.current_suit = None
        self.game_over_data = None

        for player in self.players.values():
            player.hand = []

        self.player_order = list(self.players.keys())
        random.shuffle(self.player_order)
        self.current_turn_index = 0

        num_cards_to_deal = 7 if len(self.players) == 2 else 5
        for username in self.player_order:
            cards = self.deck.deal(num_cards_to_deal)
            for card in cards:
                self.players[username].add_card(card)

        while True:
            if self.deck.is_empty():
                return False, "Deck exhausted during initial deal setup (rare)."
            top_card = self.deck.deal(1)[0]
            if top_card.value == '8':
                insert_pos = random.randint(0, len(self.deck.cards)) if not self.deck.is_empty() else 0
                self.deck.cards.insert(insert_pos, top_card)
            else:
                self.discard_pile.append(top_card)
                self.current_suit = top_card.suit
                break

        return True, None

    def get_top_discard_card(self):
        """Get the top card of the discard pile."""
        return self.discard_pile[-1] if self.discard_pile else None

    def get_current_player(self):
        """Get the username of the current player."""
        if not self.started or not self.player_order:
            return None
        if self.current_turn_index >= len(self.player_order):
            self.current_turn_index = 0
            if not self.player_order:
                return None
        return self.player_order[self.current_turn_index]

    def advance_turn(self):
        """Move to the next player's turn."""
        if self.player_order:
            self.current_turn_index = (self.current_turn_index + 1) % len(self.player_order)
        return self.get_current_player()

    def is_valid_move(self, username, card_str):
        """Check if playing a card is valid according to Crazy Eights rules."""
        if not self.started:
            return False, "Game has not started"

        if username != self.get_current_player():
            return False, "Not your turn"

        player = self.players.get(username)
        if not player:
            return False, "Player not found"

        card = player.get_card_from_str(card_str)
        if not card:
            return False, f"You don't have the card: {card_str}"

        top_card = self.get_top_discard_card()
        if not top_card:
            return False, "Discard pile is empty (error)"

        # Card is always playable if it's an 8
        if card.value == '8':
            return True, None

        # Check if the card matches the rank of the top card
        if card.value == top_card.value:
            return True, None

        # Check if the card matches the current suit (either declared after an 8 or the suit of the top card)
        effective_suit = self.current_suit if self.current_suit else top_card.suit
        if card.suit == effective_suit:
            return True, None

        # If none of the above conditions are met, the move is invalid
        return False, f"Card {card_str} doesn't match rank ({top_card.value}) or suit ({effective_suit.value})"

    def make_move(self, username, card_str, declared_suit_str=None):
        """Process a player's move (playing a card)."""
        is_valid, error = self.is_valid_move(username, card_str)
        if not is_valid:
            return False, error, None

        player = self.players[username]
        card = player.remove_card(card_str)
        if not card:
            return False, "Card inconsistency error", None

        self.discard_pile.append(card)
        # Reset current_suit initially. It will be set below if an 8 is played.
        self.current_suit = None
        declared_suit_enum = None # Keep track if a suit was declared this move

        if card.value == '8':
            if declared_suit_str:
                suit_map = {'hearts': Suit.HEARTS, 'diamonds': Suit.DIAMONDS, 'clubs': Suit.CLUBS, 'spades': Suit.SPADES}
                declared_suit_enum = suit_map.get(declared_suit_str.lower())
                if declared_suit_enum:
                    # Set self.current_suit ONLY for the declared suit after an 8
                    self.current_suit = declared_suit_enum
                else:
                    # Invalid suit string provided
                    # Put card back in hand? Or just reject move?
                    # Let's reject the move for now. Add card back to hand for safety.
                    player.add_card(card) # Add back the card that was removed
                    self.discard_pile.pop() # Remove the 8 from discard pile
                    return False, f"Invalid declared suit: {declared_suit_str}", None
            else:
                # Missing suit declaration for an 8
                player.add_card(card) # Add back the card
                self.discard_pile.pop() # Remove the 8
                return False, "Missing declared suit for playing an 8", None
        # If it wasn't an 8, self.current_suit remains None (correct for next turn's check)

        if not player.hand:
            self.end_game(winner=username)
            return True, None, {"game_over": self.game_over_data}

        next_player = self.advance_turn()
        # The current_suit to report is the one set above (declared suit or None)
        current_suit_val = self.current_suit.value if self.current_suit else None
        move_result = {
            "next_player": next_player,
            "top_card": str(self.get_top_discard_card()),
            "current_suit": current_suit_val, # Use the potentially updated current_suit
            "played_card": str(card),
            "player_who_played": username,
            # Send the declared suit value string if an 8 was played
            "declared_suit": declared_suit_enum.value if declared_suit_enum else None
        }
        return True, None, move_result

    def draw_card(self, username):
        """Allows the current player to draw a card."""
        if not self.started:
            return False, "Game has not started", None
        if username != self.get_current_player():
            return False, "Not your turn", None

        player = self.players.get(username)
        if not player:
            return False, "Player not found", None

        if self.deck.is_empty():
            if not self.reshuffle_discard_pile():
                can_anyone_play = False
                top_card = self.get_top_discard_card()
                if top_card:
                    required_suit = self.current_suit if self.current_suit else top_card.suit
                    required_value = top_card.value
                    for p_name, p_obj in self.players.items():
                        if p_obj.can_play(required_value, required_suit):
                            can_anyone_play = True
                            break

                if not can_anyone_play:
                    self.end_game(blocked=True)
                    return True, None, {"game_over": self.game_over_data, "draw_result": {"card": None, "deck_empty": True, "game_blocked": True}}
                else:
                    next_player = self.advance_turn()
                    return True, "Deck empty, cannot draw. Turn passed.", {"next_player": next_player, "top_card": str(self.get_top_discard_card()), "current_suit": self.current_suit.value if self.current_suit else None, "draw_result": {"card": None, "deck_empty": True}}

        drawn_card = self.deck.deal(1)[0]
        player.add_card(drawn_card)

        top_card = self.get_top_discard_card()
        can_play_drawn = False
        if top_card:
            effective_suit = self.current_suit if self.current_suit else top_card.suit
            if drawn_card.value == '8' or drawn_card.value == top_card.value or drawn_card.suit == effective_suit:
                can_play_drawn = True

        draw_result = {
            "card": str(drawn_card),
            "can_play": can_play_drawn,
            "deck_empty": self.deck.is_empty()
        }
        return True, None, {"draw_result": draw_result}

    def reshuffle_discard_pile(self):
        """Reshuffles the discard pile (except the top card) back into the draw deck."""
        if len(self.discard_pile) <= 1:
            return False

        top_card = self.discard_pile.pop()
        cards_to_reshuffle = self.discard_pile
        self.discard_pile = [top_card]

        self.deck.cards.extend(cards_to_reshuffle)
        self.deck.shuffle()
        return True

    def calculate_scores(self):
        """Calculate scores at the end of the game based on remaining hands."""
        scores = {}
        for username, player in self.players.items():
            scores[username] = player.calculate_hand_value()
        return scores

    def end_game(self, winner=None, blocked=False, reason=None):
        """Ends the game and determines the winner and scores."""
        if not self.started:
            return # Game wasn't even running

        self.started = False
        scores = self.calculate_scores()
        final_winner = winner # The player who went out
        game_reason = reason # Use the provided reason first

        if blocked:
            # Find player with the lowest score
            min_score = float('inf')
            potential_winners = []
            for username, score in scores.items():
                if score < min_score:
                    min_score = score
                    potential_winners = [username]
                elif score == min_score:
                    potential_winners.append(username)
            # If there's a tie for lowest score in a blocked game, it's a draw among them
            final_winner = ", ".join(potential_winners) if potential_winners else "No one (Blocked Draw)"
            if not game_reason: # Set default reason if blocked and none provided
                 game_reason = "Game blocked"

        elif final_winner and not game_reason: # Set default reason if winner and none provided
             game_reason = f"{final_winner} won"


        self.game_over_data = {
            "winner": final_winner,
            "scores": scores,
            "blocked": blocked,
            "reason": game_reason or "Game ended" # Ensure there's always a reason
        }
        # Reset turn index?
        self.current_turn_index = 0

    async def broadcast(self, message, exclude_username=None):
        """Send a message to all connected players, optionally excluding one."""
        json_message = json.dumps(message)
        tasks = []
        for username, player in self.players.items():
            if username != exclude_username and player.is_connected:
                tasks.append(
                    asyncio.create_task(
                        player.websocket.send(json_message)
                    )
                )
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    target_username = list(self.players.keys())[i]
                    print(f"Error broadcasting to {target_username}: {result}")

    async def send_to_player(self, username, message):
        """Send a message to a specific player."""
        player = self.players.get(username)
        if player and player.is_connected:
            try:
                await player.websocket.send(json.dumps(message))
            except Exception as e:
                print(f"Error sending message to {username}: {e}")

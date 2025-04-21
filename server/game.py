"""
Game logic for the card game.
"""
import asyncio
import json
import random
from .card import Deck
from .player import Player
from common import protocol

class Game:
    def __init__(self):
        self.players = {}  # username -> Player object
        self.deck = Deck()
        self.started = False
        self.current_turn_index = 0
        self.played_cards = []  # Cards that have been played
        self.player_order = []  # List of usernames in turn order
    
    def add_player(self, username, websocket):
        """Add a player to the game."""
        if username in self.players:
            return False
        self.players[username] = Player(username, websocket)
        return True
    
    def remove_player(self, username):
        """Remove a player from the game."""
        if username in self.players:
            del self.players[username]
            if username in self.player_order:
                self.player_order.remove(username)
            # Adjust current turn if necessary
            if self.started and len(self.player_order) > 0:
                self.current_turn_index %= len(self.player_order)
            return True
        return False
    
    def start_game(self):
        """Start the game, shuffle and deal cards."""
        if len(self.players) < 2:
            return False, "Need at least 2 players to start"
        
        self.started = True
        self.deck.reset()
        self.deck.shuffle()
        self.played_cards = []
        
        # Set player order
        self.player_order = list(self.players.keys())
        random.shuffle(self.player_order)
        self.current_turn_index = 0
        
        # Deal 5 cards to each player (simple game)
        for username in self.player_order:
            cards = self.deck.deal(5)
            for card in cards:
                self.players[username].add_card(card)
        
        return True, None
    
    def get_current_player(self):
        """Get the username of the current player."""
        if not self.started or not self.player_order:
            return None
        return self.player_order[self.current_turn_index]
    
    def advance_turn(self):
        """Move to the next player's turn."""
        if self.player_order:
            self.current_turn_index = (self.current_turn_index + 1) % len(self.player_order)
        return self.get_current_player()
    
    def is_valid_move(self, username, card_str):
        """Check if the move is valid."""
        if not self.started:
            return False, "Game has not started"
        
        if username != self.get_current_player():
            return False, "Not your turn"
        
        player = self.players.get(username)
        if not player:
            return False, "Player not found"
        
        if not player.has_card(card_str):
            return False, "You don't have that card"
        
        # In a simple game, any card is valid
        # For a more complex game, add rule validation here
        
        return True, None
    
    def make_move(self, username, card_str):
        """Process a player's move."""
        is_valid, error = self.is_valid_move(username, card_str)
        if not is_valid:
            return False, error
        
        # Remove the card from the player's hand
        card = self.players[username].remove_card(card_str)
        if card:
            self.played_cards.append(card)
        
        # Check win condition (player has no cards left)
        if not self.players[username].hand:
            return True, {"winner": username}
        
        # Continue to next player's turn
        next_player = self.advance_turn()
        return True, {"next_player": next_player}
    
    async def broadcast(self, message):
        """Send a message to all connected players."""
        json_message = json.dumps(message)
        tasks = []
        for player in self.players.values():
            if player.is_connected:
                tasks.append(
                    asyncio.create_task(
                        player.websocket.send(json_message)
                    )
                )
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def send_to_player(self, username, message):
        """Send a message to a specific player."""
        if username in self.players and self.players[username].is_connected:
            await self.players[username].websocket.send(json.dumps(message))

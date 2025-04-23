"""
WebSocket client for the card game.
"""
import asyncio
import json
import logging
import os
import websockets
from common import protocol
from datetime import datetime

logger = logging.getLogger(__name__)

class GameClient:
    def __init__(self, server_uri='ws://localhost:8765'):
        self.server_uri = server_uri
        self.websocket = None
        self.username = None
        self.hand = []
        self.current_turn = None
        self.game_started = False
        self.players = set()
        self.ui_callback = None
        self.top_card = None # Add state for top card
        self.current_suit = None # Add state for current suit (especially after 8)
        self.can_play_drawn_card = False # Flag if drawn card is playable
    
    def set_ui_callback(self, callback):
        """Set the callback function for UI updates."""
        self.ui_callback = callback
    
    def update_ui(self, event_type, data=None):
        """Update the UI with new information."""
        if self.ui_callback:
            self.ui_callback(event_type, data)
    
    async def connect(self, username):
        """Connect to the server."""
        try:
            # Define logs directory path
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'client_logs') # Go up one level from client dir
            
            # Create logs directory if it doesn't exist
            os.makedirs(log_dir, exist_ok=True)
            
            # Generate log filename based on current time, placing it in the logs directory
            log_filename = datetime.now().strftime("client_log_%Y%m%d_%H%M%S.log")
            log_filepath = os.path.join(log_dir, log_filename)
            
            # Configure logging to file
            # Remove existing handlers if any to avoid duplicate logs
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                filename=log_filepath, # Use the full path
                filemode='w' # Overwrite log file each time
            )
            
            self.websocket = await websockets.connect(self.server_uri)
            self.username = username
            logger.info(f"Connecting as {username} to {self.server_uri}")
            logger.info(f"Logging to file: {log_filepath}")
            
            # Send join message
            await self.send_message(protocol.create_join_message(username))
            
            # Start the message receiver
            asyncio.create_task(self.receive_messages())
            
            return True
        except Exception as e:
            # Log error before returning False, ensure logging is configured
            if not logging.root.handlers:
                 # Basic console config if file setup failed
                 logging.basicConfig(level=logging.ERROR)
            logger.error(f"Connection error: {e}")
            self.websocket = None # Ensure websocket is None on failure
            return False
    
    async def send_message(self, message):
        """Send a message to the server."""
        if self.websocket and self.websocket.open:
            try:
                await self.websocket.send(json.dumps(message))
                logger.debug(f"Sent: {message}")
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Attempted to send message, but connection is closed.")
                await self.handle_disconnection()
        else:
            logger.warning("Attempted to send message, but websocket is not connected or open.")
    
    async def start_game(self):
        """Send a request to start the game."""
        await self.send_message(protocol.create_start_game_message())
    
    async def play_card(self, card, declared_suit=None):
        """Play a card, optionally declaring a suit (for 8s)."""
        await self.send_message(protocol.create_move_message(card, declared_suit))
        self.can_play_drawn_card = False # Reset flag after attempting to play
    
    async def draw_card(self):
        """Send a request to draw a card."""
        await self.send_message(protocol.create_draw_card_message())
        self.can_play_drawn_card = False # Reset flag when drawing
    
    async def request_player_list(self):
        """Send a request to the server for the current player list."""
        await self.send_message(protocol.create_list_players_message())
    
    async def disconnect(self):
        """Disconnect from the server."""
        if self.websocket and self.websocket.open:
            logger.info("Disconnecting...")
            await self.websocket.close()
            # The receive_messages loop will handle the cleanup via ConnectionClosed
        self.websocket = None # Ensure websocket is None
        self.username = None
        # Reset game state on explicit disconnect
        self.game_started = False
        self.hand = []
        self.current_turn = None
        self.top_card = None
        self.current_suit = None
    
    async def handle_disconnection(self):
        """Handles cleanup and UI notification upon disconnection."""
        if self.websocket: # Check if already handled
            logger.info("Connection to server closed")
            self.websocket = None
            self.game_started = False # Reset game state
            self.update_ui("disconnected")
    
    async def receive_messages(self):
        """Receive and process messages from the server."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                logger.info(f"Received: {data}")
                
                action = data.get("action")
                
                if action == protocol.PLAYER_JOINED:
                    self.players.add(data["player"])
                    self.update_ui("player_joined", data)
                
                elif action == protocol.GAME_STARTED:
                    self.game_started = True
                    self.current_turn = data["currentTurn"]
                    self.top_card = data.get("topCard")
                    self.current_suit = data.get("currentSuit")
                    self.update_ui("game_started", data)
                
                elif action == protocol.DEAL:
                    self.hand = data["hand"]
                    self.update_ui("deal", data)
                
                elif action == protocol.MOVE_MADE:
                    player = data["player"]
                    move_details = data.get("move", {})
                    card = move_details.get("card")
                    self.top_card = move_details.get("topCard")
                    self.current_suit = move_details.get("currentSuit")
                    declared_suit = move_details.get("declaredSuit")
                    
                    # If it was our move, remove the card from our hand
                    if player == self.username:
                        if card in self.hand:
                            self.hand.remove(card)
                        else:
                            logger.warning(f"Server reported move ({card}) but card not found in local hand: {self.hand}")
                    
                    # Pass declared suit info to UI
                    ui_data = data.copy()
                    ui_data['declared_suit'] = declared_suit
                    self.update_ui("move_made", ui_data)
                
                elif action == protocol.TURN_CHANGE:
                    self.current_turn = data["currentTurn"]
                    self.top_card = data.get("topCard")
                    self.current_suit = data.get("currentSuit")
                    self.can_play_drawn_card = False # Reset flag on turn change
                    self.update_ui("turn_change", data)
                
                elif action == protocol.DRAW_RESULT:
                    draw_result = data.get("drawResult", {})
                    drawn_card = draw_result.get("card")
                    if drawn_card:
                        self.hand.append(drawn_card)
                    self.can_play_drawn_card = draw_result.get("canPlay", False)
                    self.update_ui("draw_result", draw_result)
                
                elif action == protocol.PLAYER_LIST:
                    self.players = set(data["players"])
                    self.update_ui("player_list", data)
                
                elif action == protocol.GAME_OVER:
                    self.game_started = False
                    self.current_turn = None
                    self.top_card = None
                    self.current_suit = None
                    # Pass the full data (including reason) to the UI
                    self.update_ui("game_over", data)
                
                elif action == protocol.ERROR:
                    self.update_ui("error", data)
                
                elif action == protocol.PLAYER_LEFT:
                    player_left = data.get("player")
                    if player_left in self.players:
                        self.players.remove(player_left)
                    self.update_ui("player_left", data)
                
                elif action == protocol.UPDATE_GAME_STATE:
                    game_state = data.get("gameState", {})
                    self.current_turn = game_state.get("currentTurn", self.current_turn)
                    self.top_card = game_state.get("topCard", self.top_card)
                    self.current_suit = game_state.get("currentSuit", self.current_suit)
                    if "hand" in game_state:
                        self.hand = game_state["hand"]
                    self.game_started = True # Assume if we get this, game is on
                    self.update_ui("update_game_state", game_state)
        
        except websockets.exceptions.ConnectionClosed:
            await self.handle_disconnection()
        except Exception as e:
            logger.error(f"Error receiving messages: {e}", exc_info=True)
            self.update_ui("error", {"message": f"Receive loop error: {e}"})
            await self.handle_disconnection()
        finally:
            await self.handle_disconnection()

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
            return False
    
    async def send_message(self, message):
        """Send a message to the server."""
        if self.websocket:
            await self.websocket.send(json.dumps(message))
    
    async def start_game(self):
        """Send a request to start the game."""
        await self.send_message(protocol.create_start_game_message())
    
    async def play_card(self, card):
        """Play a card."""
        await self.send_message(protocol.create_move_message(card))
    
    async def request_player_list(self):
        """Send a request to the server for the current player list."""
        await self.send_message(protocol.create_list_players_message())
    
    async def disconnect(self):
        """Disconnect from the server."""
        if self.websocket:
            await self.websocket.close()
    
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
                    self.update_ui("game_started", data)
                
                elif action == protocol.DEAL:
                    self.hand = data["hand"]
                    self.update_ui("deal", data)
                
                elif action == protocol.MOVE_MADE:
                    player = data["player"]
                    card = data["move"]["card"]
                    
                    # If it was our move, remove the card from our hand
                    if player == self.username and card in self.hand:
                        self.hand.remove(card)
                    
                    self.update_ui("move_made", data)
                
                elif action == protocol.TURN_CHANGE:
                    self.current_turn = data["currentTurn"]
                    self.update_ui("turn_change", data)
                
                elif action == protocol.PLAYER_LIST:
                    self.players = set(data["players"])
                    self.update_ui("player_list", data)
                
                elif action == protocol.GAME_OVER:
                    self.game_started = False
                    self.update_ui("game_over", data)
                
                elif action == protocol.ERROR:
                    self.update_ui("error", data)
        
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection to server closed")
            self.update_ui("disconnected")
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            self.update_ui("error", {"message": str(e)})

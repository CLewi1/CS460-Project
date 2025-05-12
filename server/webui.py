"""
Flask web interface for the card game server.
"""
import os
from flask import Flask, render_template, redirect, url_for, request, jsonify, session
from datetime import datetime
import json
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebUI:
    def __init__(self, game_server=None):
        """Initialize the Flask application for the web UI"""
        self.app = Flask(
            __name__,
            template_folder='../templates',
            static_folder='../static'
        )
        self.app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
        self.game_server = game_server
        self.setup_routes()
        
    def setup_routes(self):
        """Set up the Flask routes"""
        
        @self.app.route('/')
        def index():
            """Home page - shows game status and connected players"""
            if not self.game_server:
                return render_template('error.html', message="Game server not initialized")
            
            players = list(self.game_server.game.players.keys())
            is_started = self.game_server.game.started
            current_player = self.game_server.game.get_current_player()
            top_card = self.game_server.game.get_top_discard_card()
            current_suit = self.game_server.game.current_suit
            
            game_info = {
                'started': is_started,
                'players': players,
                'current_player': current_player,
                'top_card': str(top_card) if top_card else None,
                'current_suit': current_suit.value if current_suit and is_started else None,
                'player_count': len(players)
            }
            
            return render_template('index.html', game=game_info)
        
        @self.app.route('/admin')
        def admin():
            """Admin page for monitoring and controlling the game"""
            if not self.game_server:
                return render_template('error.html', message="Game server not initialized")
            
            players = {}
            for username, player in self.game_server.game.players.items():
                players[username] = {
                    'hand_size': len(player.hand),
                    'is_connected': player.is_connected
                }
            
            game_info = {
                'started': self.game_server.game.started,
                'players': players,
                'current_player': self.game_server.game.get_current_player(),
                'player_order': self.game_server.game.player_order,
                'deck_size': len(self.game_server.game.deck.cards),
                'discard_size': len(self.game_server.game.discard_pile),
                'top_card': str(self.game_server.game.get_top_discard_card()) if self.game_server.game.discard_pile else None,
                'current_suit': self.game_server.game.current_suit.value if self.game_server.game.current_suit else None
            }
            
            return render_template('admin.html', game=game_info)
        
        @self.app.route('/api/game-state')
        def game_state_api():
            """API endpoint to get the current game state as JSON"""
            if not self.game_server:
                return jsonify({'error': 'Game server not initialized'})
            
            players = {}
            for username, player in self.game_server.game.players.items():
                players[username] = {
                    'hand_size': len(player.hand),
                    'is_connected': player.is_connected
                }
            
            game_info = {
                'started': self.game_server.game.started,
                'players': players,
                'current_player': self.game_server.game.get_current_player(),
                'player_order': self.game_server.game.player_order,
                'deck_size': len(self.game_server.game.deck.cards),
                'discard_size': len(self.game_server.game.discard_pile),
                'top_card': str(self.game_server.game.get_top_discard_card()) if self.game_server.game.discard_pile else None,
                'current_suit': self.game_server.game.current_suit.value if self.game_server.game.current_suit else None,
                'timestamp': datetime.now().isoformat()
            }
            
            return jsonify(game_info)
        
    def start(self, host='0.0.0.0', port=5000, debug=False):
        """Start the Flask web server"""
        # Use a separate thread for Flask to avoid blocking the WebSocket server
        threading.Thread(
            target=self.app.run,
            kwargs={'host': host, 'port': port, 'debug': debug},
            daemon=True
        ).start()
        logger.info(f"Web UI started at http://{host}:{port}")
        
    def set_game_server(self, game_server):
        """Set the game server instance after initialization"""
        self.game_server = game_server
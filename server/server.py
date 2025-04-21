"""
WebSocket server for the card game.
"""
import asyncio
import json
import logging
import websockets
import threading
from .game import Game
from common import protocol

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GameServer:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.game = Game()
    
    async def handle_client(self, websocket, path):
        """Handle a client connection."""
        client_id = id(websocket)
        username = None
        logger.info(f"New connection from {client_id}")
        
        try:
            async for message in websocket:
                data = json.loads(message)
                logger.info(f"Received: {data}")
                
                # Process different message types
                if data["action"] == protocol.JOIN:
                    username = data["username"]
                    success = self.game.add_player(username, websocket)
                    if success:
                        logger.info(f"Player {username} joined")
                        player_count = len(self.game.players)
                        
                        # Send player joined notification to all players
                        await self.game.broadcast(
                            protocol.create_player_joined_message(username, player_count)
                        )
                        
                        # Send the full player list to the new player
                        if len(self.game.players) > 1:
                            all_players = list(self.game.players.keys())
                            await self.game.send_to_player(
                                username,
                                protocol.create_player_list_message(all_players)
                            )
                    else:
                        await websocket.send(json.dumps(
                            protocol.create_error_message(f"Username {username} already taken")
                        ))
                
                elif data["action"] == protocol.START_GAME:
                    if username:
                        success, error = self.game.start_game()
                        if success:
                            logger.info("Game started")
                            current_turn = self.game.get_current_player()
                            
                            # Send game started to all players
                            await self.game.broadcast(
                                protocol.create_game_started_message(current_turn)
                            )
                            
                            # Send private hand to each player
                            for player_name, player in self.game.players.items():
                                hand = player.get_hand_as_strings()
                                await self.game.send_to_player(
                                    player_name,
                                    protocol.create_deal_message(hand)
                                )
                        else:
                            await websocket.send(json.dumps(
                                protocol.create_error_message(error)
                            ))
                
                elif data["action"] == protocol.MOVE:
                    if username:
                        card = data["move"]["card"]
                        success, result = self.game.make_move(username, card)
                        if success:
                            # Broadcast the move
                            await self.game.broadcast(
                                protocol.create_move_made_message(username, card)
                            )
                            
                            if "winner" in result:
                                # Game over, we have a winner
                                await self.game.broadcast(
                                    protocol.create_game_over_message(result["winner"])
                                )
                                self.game.started = False
                            else:
                                # Notify about turn change
                                await self.game.broadcast(
                                    protocol.create_turn_change_message(result["next_player"])
                                )
                        else:
                            await websocket.send(json.dumps(
                                protocol.create_error_message(result)
                             ))
                
                elif data["action"] == protocol.LIST_PLAYERS:  # Handle the new action
                    if username:
                        player_names = list(self.game.players.keys())
                        await self.game.send_to_player(
                            username,
                            protocol.create_player_list_message(player_names)
                        )
                        logger.info(f"Sent player list to {username}: {player_names}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed for {username or client_id}")
        except Exception as e:
            logger.error(f"Error handling client: {e}", exc_info=True)
        finally:
            if username and username in self.game.players:
                self.game.remove_player(username)
                logger.info(f"Removed player {username}")
                
                # Notify remaining players that someone left
                if self.game.players:
                    player_count = len(self.game.players)
                    asyncio.create_task(self.game.broadcast(
                        protocol.create_player_left_message(username, player_count)
                    ))
    
    async def start_server(self):
        """Start the WebSocket server."""
        server = await websockets.serve(
            self.handle_client, self.host, self.port
        )
        logger.info(f"Server started at ws://{self.host}:{self.port}")
        return server

async def main():
    """Main entry point for the server."""
    # Start WebSocket server
    server = GameServer()
    server_task = await server.start_server()
    
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        server_task.close()
        await server_task.wait_closed()
        logger.info("Servers shutdown")

if __name__ == "__main__":
    asyncio.run(main())

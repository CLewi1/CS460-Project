"""
WebSocket server for the card game.
"""
import asyncio
import json
import logging
import websockets
import threading
from .game import Game
import common.protocol as protocol
from .webui import WebUI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GameServer:
    def __init__(self, host='localhost', port=8765, web_port=5000):
        self.host = host
        self.port = port
        self.web_port = web_port
        self.game = Game()
        self.clients = {}
        self.webui = WebUI(self)
    
    async def handle_client(self, websocket):
        """Handle a client connection."""
        client_id = id(websocket)
        self.clients[client_id] = websocket
        logger.info(f"New connection from {client_id}")
        username = None
        
        try:
            async for message in websocket:
                data = json.loads(message)
                logger.info(f"Received from {username or 'new client'}: {data}")

                action = data.get("action")

                if action == protocol.JOIN:
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
                        all_players = list(self.game.players.keys())
                        await self.game.send_to_player(
                            username,
                            protocol.create_player_list_message(all_players)
                        )

                        # If game is already in progress, send current state (without hand)
                        if self.game.started:
                            top_card = self.game.get_top_discard_card()
                            await self.game.send_to_player(
                                username,
                                protocol.create_update_game_state_message(
                                    current_turn=self.game.get_current_player(),
                                    top_card=str(top_card) if top_card else None,
                                    current_suit=self.game.current_suit.value if self.game.current_suit else None
                                )
                            )
                            await self.game.send_to_player(username, protocol.create_error_message("Game already in progress. You are observing."))

                    else:
                        await websocket.send(json.dumps(
                            protocol.create_error_message(f"Username {username} already taken or invalid")
                        ))
                        username = None

                elif not username:
                    await websocket.send(json.dumps(
                        protocol.create_error_message("You must join first.")
                    ))
                    continue

                elif action == protocol.START_GAME:
                    success, error = self.game.start_game()
                    if success:
                        logger.info(f"Game started by {username}")
                        current_turn = self.game.get_current_player()
                        top_card = self.game.get_top_discard_card()
                        current_suit = self.game.current_suit

                        # Send game started to all players
                        await self.game.broadcast(
                            protocol.create_game_started_message(
                                current_turn,
                                str(top_card),
                                current_suit.value if current_suit else None
                            )
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
                            protocol.create_error_message(error or "Failed to start game")
                        ))

                elif action == protocol.MOVE:
                    move_data = data.get("move", {})
                    card_str = move_data.get("card")
                    declared_suit_str = move_data.get("declaredSuit")

                    if not card_str:
                        await websocket.send(json.dumps(protocol.create_error_message("Invalid move format.")))
                        continue

                    success, error, result_data = self.game.make_move(username, card_str, declared_suit_str)

                    if success:
                        logger.info(f"Move made by {username}: {card_str} {f'(declared {declared_suit_str})' if declared_suit_str else ''}")
                        if "game_over" in result_data:
                            game_over_info = result_data["game_over"]
                            await self.game.broadcast(
                                protocol.create_game_over_message(
                                    winner=game_over_info["winner"],
                                    scores=game_over_info["scores"],
                                    blocked=game_over_info["blocked"]
                                )
                            )
                            logger.info(f"Game over! Winner: {game_over_info['winner']}")
                        else:
                            await self.game.broadcast(
                                protocol.create_move_made_message(
                                    player=result_data["player_who_played"],
                                    card=result_data["played_card"],
                                    top_card=result_data["top_card"],
                                    current_suit=result_data["current_suit"],
                                    declared_suit=result_data.get("declared_suit")
                                )
                            )
                            await self.game.broadcast(
                                protocol.create_turn_change_message(
                                    current_turn=result_data["next_player"],
                                    top_card=result_data["top_card"],
                                    current_suit=result_data["current_suit"]
                                )
                            )
                    else:
                        await websocket.send(json.dumps(
                            protocol.create_error_message(error or "Invalid move")
                        ))

                elif action == protocol.DRAW_CARD:
                    success, error, result_data = self.game.draw_card(username)

                    if success:
                        draw_info = result_data.get("draw_result")
                        if draw_info:
                            logger.info(f"{username} drew: {draw_info.get('card')}")
                            await self.game.send_to_player(
                                username,
                                protocol.create_draw_result_message(
                                    drawn_card=draw_info.get("card"),
                                    can_play=draw_info.get("can_play", False),
                                    deck_empty=draw_info.get("deck_empty", False),
                                    game_blocked=draw_info.get("game_blocked", False)
                                )
                            )

                            if draw_info.get("game_blocked", False):
                                game_over_info = result_data.get("game_over")
                                if game_over_info:
                                    await self.game.broadcast(
                                        protocol.create_game_over_message(
                                            winner=game_over_info["winner"],
                                            scores=game_over_info["scores"],
                                            blocked=game_over_info["blocked"]
                                        )
                                    )
                                    logger.info(f"Game blocked! Winner/Lowest: {game_over_info['winner']}")

                        elif "next_player" in result_data:
                            logger.info(f"{username} tried to draw, but deck empty. Turn passed.")
                            await self.game.send_to_player(username, protocol.create_error_message(error))
                            await self.game.broadcast(
                                protocol.create_turn_change_message(
                                    current_turn=result_data["next_player"],
                                    top_card=result_data["top_card"],
                                    current_suit=result_data["current_suit"]
                                )
                            )

                    else:
                        await websocket.send(json.dumps(
                            protocol.create_error_message(error or "Cannot draw card")
                        ))

                elif action == protocol.LIST_PLAYERS:
                    player_names = list(self.game.players.keys())
                    await self.game.send_to_player(
                        username,
                        protocol.create_player_list_message(player_names)
                    )
                    logger.info(f"Sent player list to {username}: {player_names}")
        
        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"Client {client_id} disconnected normally.")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning(f"Client {client_id} connection closed with error: {e}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}", exc_info=True)
        finally:
            if username:
                logger.info(f"Player {username} disconnecting...")
                was_started = self.game.started  # Check if game was running *before* removing player
                removed, was_current_player = self.game.remove_player(username)

                if removed:
                    logger.info(f"Removed player {username} from game state")
                    player_count = len(self.game.players)

                    # Notify remaining players about the departure
                    if self.game.players:
                        await self.game.broadcast(
                            protocol.create_player_left_message(username, player_count),
                            exclude_username=username
                        )

                    # Check if the game should end because the player quit mid-game
                    # Use was_started to see if game was running before removal
                    if was_started and not self.game.game_over_data:  # Check if game hasn't already ended (e.g., by player count < 2 in remove_player)
                        logger.info(f"Game was in progress. Ending game because player {username} quit.")
                        # End the game with a specific reason
                        self.game.end_game(reason=f"Player {username} quit")
                        # The game_over_data is now set by end_game

                    # Broadcast game over if it ended (either by player count < 2 in remove_player OR explicit quit above)
                    if self.game.game_over_data:
                        # Ensure the reason is included in the message
                        reason = self.game.game_over_data.get("reason", "Game ended")
                        logger.info(f"Broadcasting game over. Reason: {reason}")
                        await self.game.broadcast(
                            protocol.create_game_over_message(
                                winner=self.game.game_over_data["winner"],
                                scores=self.game.game_over_data["scores"],
                                blocked=self.game.game_over_data["blocked"],
                                reason=reason  # Pass reason to protocol function
                            ),
                            exclude_username=username  # Exclude the player who just left
                        )
                        # Reset game_over_data after broadcasting? Or let start_game handle reset?
                        # Let start_game handle reset.

                    # If game didn't end, but was started and the current player left, advance turn
                    # This condition should now only be met if the game didn't end due to the quit
                    elif was_started and was_current_player:
                        next_player = self.game.get_current_player()
                        top_card = self.game.get_top_discard_card()
                        current_suit = self.game.current_suit
                        logger.info(f"Player {username} left on their turn. New turn: {next_player}")
                        await self.game.broadcast(
                            protocol.create_turn_change_message(
                                current_turn=next_player,
                                top_card=str(top_card) if top_card else None,
                                current_suit=current_suit.value if current_suit else None
                            ),
                            exclude_username=username
                        )

            if client_id in self.clients:
                del self.clients[client_id]
                logger.info(f"Client websocket {client_id} removed.")
    
    async def start_server(self):
        """Start the WebSocket server."""
        server = await websockets.serve(
            self.handle_client, self.host, self.port
        )
        logger.info(f"Server started at ws://{self.host}:{self.port}")
        
        # Start the web UI in a separate thread
        self.webui.start(host=self.host, port=self.web_port, debug=False)
        logger.info(f"Web UI started at http://{self.host}:{self.web_port}")
        
        return server

async def main():
    """Main entry point for the server."""
    server = GameServer()
    ws_server = await server.start_server()
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        ws_server.close()
        await ws_server.wait_closed()
        logger.info("Server stopped.")

if __name__ == "__main__":
    asyncio.run(main())

"""
Protocol definitions for card game communication.
Defines message types and structures for client-server communication.
"""

# Action types
JOIN = "join"
PLAYER_JOINED = "player_joined"
PLAYER_LIST = "player_list" # Server response with the list
PLAYER_LEFT = "player_left"
START_GAME = "start_game"
GAME_STARTED = "game_started"
DEAL = "deal"
MOVE = "move"
MOVE_MADE = "move_made"
TURN_CHANGE = "turn_change"
ERROR = "error"
GAME_OVER = "game_over"
LIST_PLAYERS = "list_players" # Client request for the list

# Helper functions to create messages
def create_join_message(username):
    return {"action": JOIN, "username": username}

def create_player_joined_message(player, player_count):
    return {"action": PLAYER_JOINED, "player": player, "playerCount": player_count}

def create_start_game_message():
    return {"action": START_GAME}

def create_game_started_message(current_turn):
    return {"action": GAME_STARTED, "currentTurn": current_turn}

def create_deal_message(hand):
    return {"action": DEAL, "hand": hand}

def create_move_message(card):
    return {"action": MOVE, "move": {"card": card}}

def create_move_made_message(player, card):
    return {"action": MOVE_MADE, "player": player, "move": {"card": card}}

def create_turn_change_message(current_turn):
    return {"action": TURN_CHANGE, "currentTurn": current_turn}

def create_error_message(message):
    return {"action": ERROR, "message": message}

def create_game_over_message(winner):
    return {"action": GAME_OVER, "winner": winner}

def create_player_list_message(players):
    """Create a message containing the list of players."""
    return {"action": PLAYER_LIST, "players": players}

def create_player_left_message(player, player_count):
    return {"action": PLAYER_LEFT, "player": player, "playerCount": player_count}

def create_list_players_message():
    """Create a message to request the list of players."""
    return {"action": LIST_PLAYERS}

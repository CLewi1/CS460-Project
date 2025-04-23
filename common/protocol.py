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
DEAL = "deal" # Server sends initial hand to player
MOVE = "move" # Client plays a card
MOVE_MADE = "move_made" # Server broadcasts a move
DRAW_CARD = "draw_card" # Client requests to draw a card
DRAW_RESULT = "draw_result" # Server sends result of draw attempt
TURN_CHANGE = "turn_change"
ERROR = "error"
GAME_OVER = "game_over"
LIST_PLAYERS = "list_players" # Client request for the list
UPDATE_GAME_STATE = "update_game_state" # Server sends general game state update

# Helper functions to create messages
def create_join_message(username):
    return {"action": JOIN, "username": username}

def create_player_joined_message(player, player_count):
    return {"action": PLAYER_JOINED, "player": player, "playerCount": player_count}

def create_start_game_message():
    return {"action": START_GAME}

def create_game_started_message(current_turn, top_card, current_suit):
    """Server informs clients game has started."""
    return {
        "action": GAME_STARTED,
        "currentTurn": current_turn,
        "topCard": top_card, # e.g., '7H'
        "currentSuit": current_suit # e.g., 'hearts'
    }

def create_deal_message(hand):
    """Server sends the initial hand to a player."""
    return {"action": DEAL, "hand": hand} # hand is list of card strings e.g., ['KH', '8S']

def create_move_message(card, declared_suit=None):
    """Client sends a move (playing a card)."""
    move_data = {"card": card} # card is string e.g., '8S'
    if declared_suit:
        move_data["declaredSuit"] = declared_suit # e.g., 'spades'
    return {"action": MOVE, "move": move_data}

def create_move_made_message(player, card, top_card, current_suit, declared_suit=None):
    """Server broadcasts that a move was made."""
    move_details = {
        "card": card, # Card played (string)
        "topCard": top_card, # New top card (string)
        "currentSuit": current_suit # New current suit (string, e.g., 'hearts')
    }
    if declared_suit:
        move_details["declaredSuit"] = declared_suit # Suit declared if an 8 was played (string)

    return {
        "action": MOVE_MADE,
        "player": player,
        "move": move_details
    }

def create_draw_card_message():
    """Client requests to draw a card."""
    return {"action": DRAW_CARD}

def create_draw_result_message(drawn_card, can_play, deck_empty, game_blocked=False):
    """Server informs player about the result of their draw attempt."""
    result = {
        "card": drawn_card, # String of drawn card, or None if failed/blocked
        "canPlay": can_play, # Boolean: can the drawn card be played immediately?
        "deckEmpty": deck_empty, # Boolean: is the draw pile now empty?
        "gameBlocked": game_blocked # Boolean: did the draw attempt lead to a blocked game?
    }
    return {"action": DRAW_RESULT, "drawResult": result}

def create_turn_change_message(current_turn, top_card, current_suit):
    """Server announces the next turn, including current game state."""
    return {
        "action": TURN_CHANGE,
        "currentTurn": current_turn,
        "topCard": top_card,
        "currentSuit": current_suit
    }

def create_error_message(message):
    return {"action": ERROR, "message": message}

def create_game_over_message(winner, scores, blocked, reason=None):
    """Server announces the game is over."""
    return {
        "action": GAME_OVER,
        "winner": winner,
        "scores": scores, # Dict: {username: score}
        "blocked": blocked, # Boolean
        # Add reason, provide defaults based on winner/blocked status if reason is None
        "reason": reason or ("Game blocked" if blocked else f"{winner} won" if winner else "Game ended")
    }

def create_player_list_message(players):
    """Create a message containing the list of players."""
    return {"action": PLAYER_LIST, "players": players}

def create_player_left_message(player, player_count):
    return {"action": PLAYER_LEFT, "player": player, "playerCount": player_count}

def create_list_players_message():
    """Create a message to request the list of players."""
    return {"action": LIST_PLAYERS}

def create_update_game_state_message(current_turn, top_card, current_suit, hand=None):
    """Server sends a general game state update (e.g., after player leaves)."""
    state = {
        "currentTurn": current_turn,
        "topCard": top_card,
        "currentSuit": current_suit
    }
    if hand is not None: # Optionally include hand if sending to a specific player
        state["hand"] = hand
    return {"action": UPDATE_GAME_STATE, "gameState": state}

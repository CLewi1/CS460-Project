"""
Simple console UI for the card game client.
"""
import asyncio
import logging
from .client import GameClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConsoleUI:
    def __init__(self):
        self.client = GameClient()
        self.client.set_ui_callback(self.update_ui)
        self.running = True
        self.waiting_for_suit_declaration = False # Flag for 8s
        self.card_to_play_if_8 = None # Store the 8 being played

    def update_ui(self, event_type, data=None):
        """Update the UI based on events from the client."""
        message = ""
        prompt_needed = True

        if event_type == "player_joined":
            message = f"👤 {data['player']} joined the game. Total players: {data['playerCount']}"
        elif event_type == "player_left":
            message = f"👤 {data['player']} left the game. Total players: {data['playerCount']}"
        elif event_type == "game_started":
            message = f"🎮 Game started!\nTop Card: {data.get('topCard', 'N/A')}\nCurrent Suit: {data.get('currentSuit', 'N/A')}\nCurrent turn: {data['currentTurn']}"
        elif event_type == "deal":
            hand_str = "\n".join([f"  {i+1}. {card}" for i, card in enumerate(data['hand'])])
            message = f"🃏 Your hand:\n{hand_str}"
            # Don't set prompt_needed = False here, let the logic below handle it
        elif event_type == "move_made":
            card_played = data['move']['card']
            declared_suit = data.get('declared_suit')
            suit_info = f" (declared {declared_suit})" if declared_suit else ""
            message = f"👉 {data['player']} played {card_played}{suit_info}\nTop Card: {data['move'].get('topCard', 'N/A')}\nCurrent Suit: {data['move'].get('currentSuit', 'N/A')}"
        elif event_type == "turn_change":
            is_my_turn = data['currentTurn'] == self.client.username
            message = f"🔄 Current turn: {data['currentTurn']}\nTop Card: {data.get('topCard', 'N/A')}\nCurrent Suit: {data.get('currentSuit', 'N/A')}"
        elif event_type == "draw_result":
            drawn_card = data.get('card')
            if data.get('gameBlocked'):
                message = "❌ Deck empty and cannot reshuffle. Game is blocked!"
                # Game over message will follow from server
                prompt_needed = False
            elif drawn_card:
                message = f"✏️ You drew: {drawn_card}"
                if data.get('canPlay'):
                    message += " (You can play this card)"
                if data.get('deckEmpty'):
                    message += "\n⚠️ Draw pile is now empty."
            else:
                message = "Cannot draw. Deck may be empty."
            prompt_needed = True
        elif event_type == "game_over":
            reason = data.get('reason', 'Game ended') # Get the reason
            winner_info = f"Winner: {data['winner']}"
            if data.get('blocked'):
                # If blocked, the 'winner' field might contain the lowest scorer(s)
                winner_info = f"Game Blocked! Lowest Score: {data['winner']}"

            scores_str = "\n".join([f"  {p}: {s} points" for p, s in data.get('scores', {}).items()])
            # Include the reason in the message
            message = f"🏆 Game over! ({reason})\n{winner_info}\nFinal Scores:\n{scores_str}\nEnter 'start' to play again or 'quit' to exit."
            prompt_needed = False
        elif event_type == "error":
            message = f"❌ Error: {data['message']}"
        elif event_type == "disconnected":
            message = "🔌 Disconnected from server."
            self.running = False
            prompt_needed = False
        elif event_type == "player_list":
            players_str = "\n".join([f"  - {p}" for p in data['players']])
            message = f"👥 Players in game:\n{players_str}"
        elif event_type == "update_game_state": # Handle general state update
             message = f"🔄 Game state update.\nTop Card: {data.get('topCard', 'N/A')}\nCurrent Suit: {data.get('currentSuit', 'N/A')}\nCurrent turn: {data['currentTurn']}"
             if "hand" in data:
                 hand_str = "\n".join([f"  {i+1}. {card}" for i, card in enumerate(self.client.hand)])
                 message += f"\n🃏 Your hand:\n{hand_str}"

        if message:
            print(f"\n{message}", flush=True)

        if prompt_needed and self.running and not self.waiting_for_suit_declaration:
            self._print_prompt()

    def _print_prompt(self):
        """Prints the appropriate command prompt."""
        if not self.running:
             return

        if self.waiting_for_suit_declaration:
            print("\nDeclare suit for the 8 (hearts, diamonds, clubs, spades):")
            print("> ", end='', flush=True)
            return

        if self.client.websocket:
            if self.client.game_started:
                print(f"\n--- Top Card: {self.client.top_card or 'N/A'} | Current Suit: {self.client.current_suit or 'N/A'} ---")

                if self.client.current_turn == self.client.username:
                    if self.client.hand:
                        hand_str = "\n".join([f"  {i+1}. {card}" for i, card in enumerate(self.client.hand)])
                        print(f"\n🃏 Your hand:\n{hand_str}")
                    else:
                        print("\nYour hand is empty.")

                    actions = ["play <number>"]
                    actions.append("draw")
                    if self.client.can_play_drawn_card:
                         print("\nYour turn! You drew a playable card.")
                    else:
                         print("\nYour turn! Choose an action:")

                    print(f"Actions: { ', '.join(actions) }")
                    print("> ", end='', flush=True)
                else:
                    print(f"\nIt is {self.client.current_turn}'s turn. Please wait.")
            else:
                print("\nEnter command (start, list, quit):")
                print("> ", end='', flush=True)
        else:
            print("\nEnter command (join <username>, quit):")
            print("> ", end='', flush=True)

    async def get_input(self):
        """Get input from the user in a non-blocking way."""
        self._print_prompt()
        while self.running:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(None, input)
                await self.process_input(user_input)
            except EOFError:
                print("\nExiting...")
                self.running = False
                if self.client.websocket:
                    await self.client.disconnect()
            except KeyboardInterrupt:
                print("\nExiting...")
                self.running = False
                if self.client.websocket:
                    await self.client.disconnect()
            except Exception as e:
                logger.error(f"Error in input loop: {e}")
                if self.running:
                    self._print_prompt()

    async def process_input(self, user_input):
        """Process user input."""
        needs_reprompt = False
        user_input_lower = user_input.lower().strip()

        if user_input_lower == 'quit':
            print("Exiting...")
            self.running = False
            await self.client.disconnect()
            return

        if self.waiting_for_suit_declaration:
            valid_suits = ["hearts", "diamonds", "clubs", "spades"]
            if user_input_lower in valid_suits:
                declared_suit = user_input_lower
                print(f"Playing {self.card_to_play_if_8} and declaring {declared_suit}...")
                await self.client.play_card(self.card_to_play_if_8, declared_suit)
                self.waiting_for_suit_declaration = False
                self.card_to_play_if_8 = None
            else:
                print("Invalid suit. Please enter hearts, diamonds, clubs, or spades.")
                needs_reprompt = True
            if needs_reprompt and self.running:
                self._print_prompt()
            return

        if not self.client.websocket:
            if user_input_lower.startswith('join '):
                username = user_input[5:].strip()
                if username:
                    print(f"Connecting as {username}...")
                    if self.client.websocket:
                        await self.client.disconnect()
                    success = await self.client.connect(username)
                    if not success:
                        print("Failed to connect.")
                        needs_reprompt = True
                else:
                    print("Please provide a username.")
                    needs_reprompt = True
            else:
                print("Please join first with 'join <username>' or quit")
                needs_reprompt = True

        elif not self.client.game_started:
            if user_input_lower == 'start':
                await self.client.start_game()
            elif user_input_lower == 'list':
                await self.client.request_player_list()
            else:
                print(f"Unknown command or game not started: {user_input}")
                needs_reprompt = True

        elif self.client.game_started:
            if self.client.current_turn == self.client.username:
                if user_input_lower == 'draw':
                    print("Drawing card...")
                    await self.client.draw_card()
                elif user_input_lower.startswith('play '):
                    card_num_str = user_input[5:].strip()
                    try:
                        card_index = int(card_num_str) - 1
                        if 0 <= card_index < len(self.client.hand):
                            card_to_play = self.client.hand[card_index]
                            if card_to_play.startswith('8'):
                                self.waiting_for_suit_declaration = True
                                self.card_to_play_if_8 = card_to_play
                                needs_reprompt = True
                            else:
                                print(f"Playing {card_to_play}...")
                                await self.client.play_card(card_to_play)
                        else:
                            print("Invalid card number.")
                            needs_reprompt = True
                    except ValueError:
                        print("Invalid command. Use 'play <number>' or 'draw'.")
                        needs_reprompt = True
                else:
                    print("Invalid command. Use 'play <number>' or 'draw'.")
                    needs_reprompt = True
            else:
                if user_input_lower == 'list':
                     await self.client.request_player_list()
                else:
                     print("It's not your turn.")
                     needs_reprompt = True
        else:
             print(f"Unknown state or command: {user_input}")
             needs_reprompt = True

        if needs_reprompt and self.running:
            self._print_prompt()

    async def run(self):
        """Run the UI."""
        print("🃏 Welcome to Crazy Eights! 🃏")
        try:
            await self.get_input()
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            if self.client.websocket:
                await self.client.disconnect()

async def main():
    """Main entry point for the client."""
    ui = ConsoleUI()
    await ui.run()

if __name__ == "__main__":
    asyncio.run(main())

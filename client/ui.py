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
    
    def update_ui(self, event_type, data=None):
        """Update the UI based on events from the client."""
        # Determine the message based on event_type
        message = ""
        prompt_needed = True # Assume we need to reprint the prompt unless disconnected

        if event_type == "player_joined":
            message = f"👤 {data['player']} joined the game. Total players: {data['playerCount']}"
        elif event_type == "game_started":
            message = f"🎮 Game started! Current turn: {data['currentTurn']}"
        elif event_type == "deal":
            hand_str = "\n".join([f"  {i+1}. {card}" for i, card in enumerate(data['hand'])])
            message = f"🃏 Your hand:\n{hand_str}"
        elif event_type == "move_made":
            message = f"👉 {data['player']} played {data['move']['card']}"
        elif event_type == "turn_change":
            is_my_turn = data['currentTurn'] == self.client.username
            turn_message = f"🔄 Current turn: {data['currentTurn']}"
            if is_my_turn:
                turn_message += "\nIt's your turn! Enter the number of the card to play."
            message = turn_message
        elif event_type == "game_over":
            message = f"🏆 Game over! Winner: {data['winner']}\nEnter 'start' to start a new game or 'quit' to exit."
        elif event_type == "error":
            message = f"❌ Error: {data['message']}"
        elif event_type == "disconnected":
            message = "🔌 Disconnected from server."
            self.running = False # Stop the input loop
            prompt_needed = False # Don't reprint prompt if disconnected
        elif event_type == "player_list": # New event type
            players_str = "\n".join([f"  - {p}" for p in data['players']])
            message = f"👥 Players in game:\n{players_str}"

        # Print the message with a preceding newline for separation
        if message:
            print(f"\n{message}", flush=True) # Added flush=True

        # If the client is still running, reprint the prompt
        if prompt_needed and self.running:
            self._print_prompt()

    def _print_prompt(self):
        """Prints the appropriate command prompt."""
        # Determine the correct prompt to show
        if self.client.websocket:
            if self.client.game_started and self.client.current_turn == self.client.username:
                print("\nYour turn! Choose a card to play (enter the number):")
                print("> ", end='', flush=True)
            else:
                # General command prompt when connected
                print("\nEnter command (start, list, quit):") # Added 'list'
                print("> ", end='', flush=True)
        else:
            # Prompt when not connected
            print("\nEnter command (join <username>, quit):")
            print("> ", end='', flush=True)

    async def get_input(self):
        """Get input from the user in a non-blocking way."""
        # Print the initial prompt once
        self._print_prompt()

        while self.running:
            try:
                # Wait for user input. The prompt is already displayed.
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input
                )

                # Process the input
                await self.process_input(user_input)

            except EOFError: # Handle Ctrl+D or similar
                print("\nExiting...")
                self.running = False
                if self.client.websocket:
                    await self.client.disconnect()
            except KeyboardInterrupt: # Handle Ctrl+C
                print("\nExiting...")
                self.running = False
                if self.client.websocket:
                    await self.client.disconnect()
            except Exception as e:
                logger.error(f"Error in input loop: {e}")
                # Reprint prompt after other errors if still running
                if self.running:
                    self._print_prompt()
    
    async def process_input(self, user_input):
        """Process user input."""
        needs_reprompt = False # Flag to indicate if we need to reprint the prompt

        if user_input.lower() == 'quit':
            print("Exiting...")
            self.running = False
            await self.client.disconnect()
            return # No reprompt needed after quit

        if not self.client.websocket:
            if user_input.lower().startswith('join '):
                username = user_input[5:].strip()
                if username:
                    print(f"Connecting as {username}...")
                    success = await self.client.connect(username)
                    if success:
                        print("Connected to server!")
                        # update_ui will handle the prompt after connection
                    else:
                        print("Failed to connect.")
                        needs_reprompt = True # Reprompt if connection failed
                else:
                    print("Please provide a username.")
                    needs_reprompt = True # Reprompt if username missing
            else:
                print("Please join first with 'join <username>'")
                needs_reprompt = True # Reprompt if not joined

        # Commands available only when connected
        elif user_input.lower() == 'start':
            await self.client.start_game()
        elif user_input.lower() == 'list': # New command
            await self.client.request_player_list()
            # Server response will trigger update_ui and reprompt
        elif self.client.game_started and self.client.current_turn == self.client.username:
            try:
                # Check if input is a valid card number
                if user_input.isdigit() and 1 <= int(user_input) <= len(self.client.hand):
                    card_index = int(user_input) - 1
                    card = self.client.hand[card_index]
                    # Server response will trigger update_ui and reprompt
                    await self.client.play_card(card)
                else:
                    print("Invalid card number.")
                    needs_reprompt = True # Reprompt on invalid card number
            except ValueError:
                print("Please enter a valid card number.")
                needs_reprompt = True # Reprompt on non-numeric input
        else:
            # Handle cases where input is given but it's not the user's turn or game not started
            print(f"Unknown command or invalid state for command: {user_input}")
            needs_reprompt = True # Reprompt on unknown command

        # Reprint the prompt if necessary
        if needs_reprompt and self.running:
            self._print_prompt()
    
    async def run(self):
        """Run the UI."""
        print("🃏 Welcome to the Card Game! 🃏")
        print("Commands: join <username>, start, list, quit")
        
        try:
            await self.get_input()
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            await self.client.disconnect()

async def main():
    """Main entry point for the client."""
    ui = ConsoleUI()
    await ui.run()

if __name__ == "__main__":
    asyncio.run(main())

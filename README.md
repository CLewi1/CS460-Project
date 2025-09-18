
# Deck Link: Multiplayer Crazy Eights

Deck Link is a real-time, multiplayer Crazy Eights card game. Play with friends in your browser or via a Python console client! The game features a modern web UI, chat, and full Crazy Eights rules.

## Features

- Multiplayer Crazy Eights gameplay
- Real-time updates using WebSockets
- Play via web browser or Python console
- In-game chat and player list
- Automatic scoring and game-over detection
- Modern, responsive web interface

## Installation

1. Clone this repository:
   ```
   git clone <repo-url>
   cd CS460-Project-1
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Game

### 1. Start the Server

This will launch both the game server and the web UI:
```
python -m server.server
```
The server listens for game clients on `ws://localhost:8765` and the web UI on `http://localhost:5001`.

### 2. Play via Web Browser

Open your browser and go to:
```
http://localhost:5001
```
Enter a username, join the lobby, and wait for others. When ready, click **Start Game**.

### 3. Play via Python Console Client

In a separate terminal:
```
python -m client.ui
```
Commands:
- Join: `join YourName`
- Start game: `start`
- Play card: `play <number>` (see your hand)
- Draw card: `draw`
- Chat: `chat <message>`

## Gameplay Overview

- Each player is dealt 5 cards (7 if only 2 players).
- On your turn, play a card matching the top card's suit or value, or play an 8 (wild) and declare a suit.
- If you can't play, draw a card until you are able to play a card. If the deck is empty, skip your turn.
- First player to empty their hand wins. If no moves are possible, lowest hand value wins.

## Crazy Eights Rules

- **8s are wild:** Play an 8 to change the current suit.
- **Valid moves:** Match the top card's suit or value, or play an 8.
- **Scoring:**
  - 8 = 50 points
  - K/Q/J/10 = 10 points
  - Ace = 1 point
  - 2-9 = face value
- **Game end:** When a player empties their hand, or if the game is blocked (no valid moves and deck is empty).

## Project Structure

- `server/` — Game logic, server, and web UI
- `client/` — Console client
- `common/` — Protocol definitions
- `static/` & `templates/` — Web UI assets

## License

MIT License. See `LICENSE` file for details.
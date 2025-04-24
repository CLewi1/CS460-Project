# Multiplayer Card Game

A simple multiplayer turn-based card game using WebSockets.

## Features

- Real-time communication between clients and server
- Turn-based gameplay
- Centralized server for game logic
- Python console-based client

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Game

### Server

Start the WebSocket game server:
```
python -m server.server
```

### Client Options

#### Option 1: Python Console Client
```
python -m client.ui
```

In the console client:
- Join with a username: `join YourName`
- Start a game (once multiple players have joined): `start`
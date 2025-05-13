document.addEventListener('DOMContentLoaded', function() {
    // Get references to DOM elements
    const loginPanel = document.getElementById('login-panel');
    const gamePanel = document.getElementById('game-panel');
    const joinBtn = document.getElementById('join-btn');
    const usernameInput = document.getElementById('username');
    const playersList = document.getElementById('players');
    const container = document.querySelector('.container');
    const startBtn = document.getElementById('start-btn'); // Get reference to start button
    const waitingOverlay = document.getElementById('waiting-overlay'); // Get reference to waiting overlay
    const opponentRow = document.getElementById('opponent-row'); // Get reference to opponent row
    const communityCardsDiv = document.getElementById('community-cards'); // Get reference to community cards area
    const playerHandDiv = document.getElementById('player-hand'); // Get reference to player hand area

    const MIN_PLAYERS_TO_START = 2; // Minimum players to start the game
    
    let socket; // Declare socket variable
    let currentUsername = ''; // Store the current user's username
    let isMyTurn = false; // Variable to track if it's the current player's turn

    const predefinedColors = ['red', 'orange', 'green', 'blue', 'purple', 'grey', 'teal'];
    let availableColors = [...predefinedColors];
    let playerColors = new Map(); // Stores playerName -> color
    let currentTopCard = null; // Stores the current top card on the discard pile { value, suit }

    function attachCardClickHandler(cardElement) {
        cardElement.addEventListener('click', function() {
            if (!isMyTurn) {
                console.log("Not your turn!");
                return;
            }
            if (this.classList.contains('playable')) {
                const playedCardString = this.dataset.cardString;
                console.log('Attempting to play card:', playedCardString);
                // Optionally, provide immediate visual feedback or disable the card
                // this.classList.remove('playable');
                // this.style.opacity = 0.5;

                const playMessage = {
                    action: 'play_card',
                    card: playedCardString,
                    username: currentUsername
                };
                socket.send(JSON.stringify(playMessage));
            } else {
                // It is my turn, but the card is not playable
                const topCardValue = currentTopCard ? currentTopCard.value : 'unknown_value';
                const topCardSuit = currentTopCard ? currentTopCard.suit : 'unknown_suit';
                console.log(`Card ${this.dataset.cardString} is not playable. Top card: ${topCardValue}${topCardSuit}. Your turn: ${isMyTurn}.`);
            }
        });
    }

    function updateStartButtonState() {
        const playerCount = playersList.querySelectorAll('.player-entry').length; // Changed selector
        if (playerCount < MIN_PLAYERS_TO_START) {
            startBtn.disabled = true;
        } else {
            startBtn.disabled = false;
        }
    }

    function displayOpponents() {
        if (!opponentRow) {
            console.error('Opponent row element not found');
            return;
        }
        opponentRow.innerHTML = ''; // Clear previous opponents

        const allPlayerElements = playersList.querySelectorAll('.player-entry'); // Changed selector
        let opponentsDisplayed = false;

        for (let i = 0; i < allPlayerElements.length; i++) {
            const playerElement = allPlayerElements[i];
            if (playerElement.dataset.playerName !== currentUsername) { // Changed to use dataset
                const opponentDiv = playerElement.cloneNode(true); // Clone the player-entry div
                opponentDiv.classList.remove('current-user'); 
                opponentRow.appendChild(opponentDiv);
                opponentsDisplayed = true;
            }
        }

        if (opponentsDisplayed) {
            opponentRow.style.display = 'flex'; // Show the opponent row with flex layout
        } else {
            opponentRow.style.display = 'none'; // Keep it hidden if no opponents
        }
    }

    function getSuitSymbol(suitName) {
        if (!suitName) return '';
        switch (suitName.toLowerCase()) {
            case 'hearts': return '♥';
            case 'diamonds': return '♦';
            case 'clubs': return '♣';
            case 'spades': return '♠';
            default: return suitName; // Return name if no symbol found
        }
    }

    function mapSuitCharToName(suitChar) {
        switch (suitChar) {
            case 'H': return 'Hearts';
            case 'D': return 'Diamonds';
            case 'C': return 'Clubs';
            case 'S': return 'Spades';
            default: return ''; // Should not happen with valid card strings
        }
    }

    function parseCardString(cardStr) {
        if (!cardStr || cardStr.length < 2) return null; // Basic validation
        const suitChar = cardStr.slice(-1);
        const value = cardStr.slice(0, -1);
        const suit = mapSuitCharToName(suitChar);
        return { value, suit };
    }

    function createCardElement(cardData, cardStr) { // cardData = { value: '7', suit: 'Hearts' }, cardStr = '7H'
        const cardDiv = document.createElement('div');
        cardDiv.classList.add('card');
        if (cardData.suit) {
            cardDiv.classList.add(cardData.suit.toLowerCase());
        }
        cardDiv.dataset.value = cardData.value; 
        cardDiv.dataset.cardString = cardStr; // Store the original card string

        const valueDiv = document.createElement('div');
        valueDiv.classList.add('card-value');
        valueDiv.textContent = cardData.value;

        const suitDiv = document.createElement('div');
        suitDiv.classList.add('card-suit');
        suitDiv.textContent = getSuitSymbol(cardData.suit);

        cardDiv.appendChild(valueDiv);
        cardDiv.appendChild(suitDiv);
        attachCardClickHandler(cardDiv); // Attach click handler
        return cardDiv;
    }

    function updateHandInteractivity() {
        const handCards = playerHandDiv.querySelectorAll('.card');
        handCards.forEach(cardElement => {
            cardElement.classList.remove('playable'); // Reset first

            if (isMyTurn && currentTopCard) {
                const handCardData = parseCardString(cardElement.dataset.cardString);
                if (handCardData) {
                    // Basic playability rule: match value or suit.
                    // This can be extended for special cards (e.g., Eights, Wilds).
                    if (handCardData.value === currentTopCard.value || handCardData.suit === currentTopCard.suit) {
                        cardElement.classList.add('playable');
                    }
                    // Example for a wild card (e.g., if '8' is wild and can be played on anything,
                    // and allows choosing next suit - choosing suit logic is server-side or needs UI)
                    // if (handCardData.value === '8') {
                    //     cardElement.classList.add('playable');
                    // }
                }
            }
        });
    }

    // Add event listener for the join button
    joinBtn.addEventListener('click', function() {
        const usernameValue = usernameInput.value.trim();
        
        // Basic validation for the username
        if (usernameValue === '') {
            alert('Please enter a username');
            return;
        }
        currentUsername = usernameValue; // Store the username

        // Initialize WebSocket connection
        // Assuming your server is running on ws://localhost:8765
        socket = new WebSocket('ws://localhost:8765');

        socket.onopen = function(event) {
            console.log('WebSocket connection established.');
            // Send join message to the server
            const joinMessage = {
                action: 'join', // As defined in protocol.py
                username: currentUsername // Use stored username
            };
            socket.send(JSON.stringify(joinMessage));
            console.log('Join message sent:', joinMessage);

            // Hide login panel and show game panel
            loginPanel.style.display = 'none';
            gamePanel.style.display = 'block';
            container.classList.add('full-width');
            
            updateStartButtonState(); // Initial check when panel is shown
        };

        socket.onmessage = function(event) {
            const message = JSON.parse(event.data);
            console.log('Message from server:', message);

            switch (message.action) {
                case 'player_list': // Full list of players, usually sent upon joining
                    playersList.innerHTML = ''; // Clear existing list
                    playerColors.clear();
                    availableColors = [...predefinedColors]; // Reset available colors

                    if (message.players && Array.isArray(message.players)) {
                        message.players.forEach(playerName => {
                            const playerEntryDiv = document.createElement('div');
                            playerEntryDiv.classList.add('player-entry');
                            playerEntryDiv.dataset.playerName = playerName;

                            const playerCircleDiv = document.createElement('div');
                            playerCircleDiv.classList.add('player-circle');
                            playerCircleDiv.style.border = 'none'; // Remove border

                            const playerNameLabelDiv = document.createElement('div');
                            playerNameLabelDiv.classList.add('player-name-label');
                            playerNameLabelDiv.textContent = playerName;

                            // All players get color from the list
                            const color = availableColors.length > 0 ? availableColors.shift() : 'lightgray'; // Fallback
                            playerColors.set(playerName, color);
                            playerCircleDiv.style.backgroundColor = color;

                            if (playerName === currentUsername) {
                                playerEntryDiv.classList.add('current-user'); // For other styling, not background
                            }
                            playerEntryDiv.appendChild(playerCircleDiv);
                            playerEntryDiv.appendChild(playerNameLabelDiv);
                            playersList.appendChild(playerEntryDiv);
                        });
                    }
                    updateStartButtonState(); // Update after list change
                    break;
                case 'player_joined': // A new player has joined
                    if (message.player) {
                        let playerExists = false;
                        const existingPlayers = playersList.querySelectorAll('.player-entry');
                        for (const item of existingPlayers) {
                            if (item.dataset.playerName === message.player) { // Changed to use dataset
                                playerExists = true;
                                break;
                            }
                        }
                        if (!playerExists) {
                            const playerEntryDiv = document.createElement('div');
                            playerEntryDiv.classList.add('player-entry');
                            playerEntryDiv.dataset.playerName = message.player;

                            const playerCircleDiv = document.createElement('div');
                            playerCircleDiv.classList.add('player-circle');
                            playerCircleDiv.style.border = 'none'; // Remove border

                            const playerNameLabelDiv = document.createElement('div');
                            playerNameLabelDiv.classList.add('player-name-label');
                            playerNameLabelDiv.textContent = message.player;

                            // All players get color from the list
                            const color = availableColors.length > 0 ? availableColors.shift() : 'lightgray'; // Fallback
                            playerColors.set(message.player, color);
                            playerCircleDiv.style.backgroundColor = color;

                            if (message.player === currentUsername) {
                                playerEntryDiv.classList.add('current-user'); // For other styling, not background
                            }
                            playerEntryDiv.appendChild(playerCircleDiv);
                            playerEntryDiv.appendChild(playerNameLabelDiv);
                            playersList.appendChild(playerEntryDiv);
                        }
                    }
                    updateStartButtonState(); // Update after list change
                    break;
                case 'player_left': // A player has left
                    if (message.player) {
                        const items = playersList.querySelectorAll('.player-entry'); // Changed selector
                        for (let i = 0; i < items.length; i++) {
                            if (items[i].dataset.playerName === message.player) { // Changed to use dataset
                                playersList.removeChild(items[i]);
                                break;
                            }
                        }
                        if (playerColors.has(message.player)) {
                            const colorToRestore = playerColors.get(message.player);
                            if (predefinedColors.includes(colorToRestore)) { // Ensure it was from the predefined list
                                availableColors.unshift(colorToRestore); // Add back to the front or sort if needed
                            }
                            playerColors.delete(message.player);
                        }
                    }
                    updateStartButtonState(); // Update after list change
                    break;
                case 'game_started': // Game has started
                    if (waitingOverlay) {
                        waitingOverlay.style.display = 'none';
                    }
                    displayOpponents(); // Display opponents
                    console.log('Game started. Current turn:', message.currentTurn, 'Top card:', message.topCard, 'Current suit:', message.currentSuit);
                    
                    isMyTurn = (message.currentTurn === currentUsername);
                    console.log(isMyTurn ? "It's your turn!" : "Waiting for your turn.");

                    if (message.topCard && communityCardsDiv) { // communityCardsDiv check, currentSuit is in parsed cardData
                        communityCardsDiv.innerHTML = ''; // Clear previous cards
                        communityCardsDiv.classList.add('card-container'); // Apply layout styling

                        const cardData = parseCardString(message.topCard); // Use parseCardString for topCard too
                        if (cardData) {
                            currentTopCard = cardData; // Store the current top card
                            const topCardElement = createCardElement(cardData, message.topCard);
                            communityCardsDiv.appendChild(topCardElement);
                        }
                    }
                    updateHandInteractivity(); // Update hand based on whose turn it is
                    break;
                case 'deal': // Player receives their hand
                    console.log('Received hand:', message.hand);
                    if (message.hand && Array.isArray(message.hand) && playerHandDiv) {
                        playerHandDiv.innerHTML = ''; // Clear previous hand
                        if (!playerHandDiv.classList.contains('card-container')) {
                            playerHandDiv.classList.add('card-container');
                        }

                        message.hand.forEach(cardStr => { 
                            const cardData = parseCardString(cardStr);
                            if (cardData) {
                                const cardElement = createCardElement(cardData, cardStr); // Pass cardStr
                                attachCardClickHandler(cardElement); // Use refactored click handler
                                playerHandDiv.appendChild(cardElement);
                            }
                        });
                        updateHandInteractivity(); // Apply .playable class based on current turn status
                    }
                    break;
                case 'game_update': // Generic message to update game state
                    console.log('Game update received:', message);
                    if (message.topCard && communityCardsDiv) {
                        communityCardsDiv.innerHTML = ''; // Clear previous cards
                        const cardData = parseCardString(message.topCard);
                        if (cardData) {
                            currentTopCard = cardData; // Store the current top card
                             // Ensure card-container class is present
                            if (!communityCardsDiv.classList.contains('card-container')) {
                                communityCardsDiv.classList.add('card-container');
                            }
                            const topCardElement = createCardElement(cardData, message.topCard);
                            communityCardsDiv.appendChild(topCardElement);
                        }
                    }
                    if (message.currentTurn) {
                        isMyTurn = (message.currentTurn === currentUsername);
                        console.log(isMyTurn ? "It's now your turn!" : "Waiting for your turn.");
                    }

                    // If the game_update includes the current player's updated hand
                    // This assumes the server might send 'hand' and 'player_for_hand' in a game_update.
                    // A common alternative is for the server to send a separate 'deal' message for hand updates.
                    if (message.hand && Array.isArray(message.hand) && playerHandDiv && message.player_for_hand === currentUsername) {
                        console.log(`Game update includes new hand for ${currentUsername}:`, message.hand);
                        playerHandDiv.innerHTML = ''; // Clear previous hand
                        if (!playerHandDiv.classList.contains('card-container')) {
                            playerHandDiv.classList.add('card-container');
                        }
                        message.hand.forEach(cardStr => {
                            const cardData = parseCardString(cardStr);
                            if (cardData) {
                                const cardElement = createCardElement(cardData, cardStr);
                                attachCardClickHandler(cardElement); // Use refactored click handler
                                playerHandDiv.appendChild(cardElement);
                            }
                        });
                    }
                    updateHandInteractivity();
                    break;
                default:
                    console.log('Received unhandled action or message format:', message);
            }
        };

        socket.onerror = function(error) {
            console.error('WebSocket Error:', error);
            alert('Failed to connect to the server. Please try again later.');
            loginPanel.style.display = 'block';
            gamePanel.style.display = 'none';
            container.classList.remove('full-width');
            updateStartButtonState(); // Ensure button state is correct if UI reverts
        };

        socket.onclose = function(event) {
            console.log('WebSocket connection closed:', event);
            if (gamePanel.style.display === 'block') { // Only if game panel was shown
                loginPanel.style.display = 'block';
                gamePanel.style.display = 'none';
                container.classList.remove('full-width');
            }
            updateStartButtonState(); // Ensure button state is correct if UI reverts
        };
    });

    // Add event listener for the start game button
    startBtn.addEventListener('click', function() {
        if (socket && socket.readyState === WebSocket.OPEN) {
            const startGameMessage = {
                action: 'start_game' // As defined in protocol.py
            };
            socket.send(JSON.stringify(startGameMessage));
            console.log('Start game message sent:', startGameMessage);
        } else {
            console.error('WebSocket is not connected or not open.');
            alert('Error: Not connected to the server. Please try rejoining.');
        }
    });
});
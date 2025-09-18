document.addEventListener('DOMContentLoaded', function() {
    // Security: HTML sanitization function
    function sanitizeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // Security: Input validation function
    function validateUsername(username) {
        // Check length (1-30 characters)
        if (username.length < 1 || username.length > 30) {
            return false;
        }
        // Check for only alphanumeric characters, spaces, hyphens, and underscores
        const validPattern = /^[a-zA-Z0-9\s\-_]+$/;
        return validPattern.test(username);
    }

    // Security: Validate and sanitize incoming messages
    function validateMessage(message) {
        if (!message || typeof message !== 'object') {
            return false;
        }
        if (!message.action || typeof message.action !== 'string') {
            return false;
        }
        return true;
    }

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
    const drawBtn = document.getElementById('draw-btn'); // Get reference to the draw button
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input'); // Get reference to chat input
    const sendChatBtn = document.getElementById('send-chat-btn'); // Get reference to send chat button

    // Chat message sending function
    function sendChatMessage() {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            console.error('WebSocket is not connected');
            return;
        }

        const message = chatInput.value.trim();
        if (message === '') return;

        // Create a chat message object
        const chatMessage = {
            action: 'chat_message',
            message: message
        };

        // Send the message to the server
        socket.send(JSON.stringify(chatMessage));

        // Add message to the chat display (local echo)
        const messageElement = document.createElement('div');
        messageElement.className = 'chat-message';
        messageElement.innerHTML = `<span class="username">${sanitizeHTML(currentUsername)}: </span><span class="message">${sanitizeHTML(message)}</span>`;
        chatMessages.appendChild(messageElement);
        
        // Scroll to the bottom of the chat
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Clear the input field
        chatInput.value = '';
    }

    // Add event listener for the send button
    if (sendChatBtn) {
        sendChatBtn.addEventListener('click', sendChatMessage);
    }

    // Add event listener for Enter key in chat input
    if (chatInput) {
        chatInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                sendChatMessage();
                event.preventDefault(); // Prevent default Enter behavior
            }
        });
    }

    const MIN_PLAYERS_TO_START = 2; // Minimum players to start the game
    
    let socket; // Declare socket variable
    let currentUsername = ''; // Store the current user's username
    let isMyTurn = false; // Variable to track if it's the current player's turn
    let currentTurnPlayer = ''; // Variable to track the current turn player
    let currentSuit = null; // Variable to track the current suit, especially after an 8 is played

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
                
                // Check if it's an 8 (which requires suit declaration)
                if (playedCardString.startsWith('8')) {
                    // Ask the user to declare a suit
                    const suits = ['hearts', 'diamonds', 'clubs', 'spades'];
                    const declaredSuit = prompt("Declare a suit for your 8 (hearts, diamonds, clubs, spades):");
                    
                    if (!declaredSuit || !suits.includes(declaredSuit.toLowerCase())) {
                        alert("You must declare a valid suit: hearts, diamonds, clubs, or spades");
                        return;
                    }
                    
                    // Create message with declared suit
                    const playMessage = {
                        action: 'move',
                        move: {
                            card: playedCardString,
                            declaredSuit: declaredSuit.toLowerCase()
                        }
                    };
                    socket.send(JSON.stringify(playMessage));
                    
                    // Immediately disable turn to prevent double-clicks or further plays
                    isMyTurn = false;
                } else {
                    // Normal card play
                    const playMessage = {
                        action: 'move',
                        move: {
                            card: playedCardString
                        }
                    };
                    socket.send(JSON.stringify(playMessage));
                    
                    // Immediately disable turn to prevent double-clicks
                    isMyTurn = false;
                }
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

    function displayPlayers() {
        if (!opponentRow) {
            console.error('Player row element not found');
            return;
        }
        
        console.log('Displaying players. Current turn player:', currentTurnPlayer);
        
        opponentRow.innerHTML = ''; // Clear previous players

        const allPlayerElements = playersList.querySelectorAll('.player-entry');
        let playersDisplayed = false;

        for (let i = 0; i < allPlayerElements.length; i++) {
            const playerElement = allPlayerElements[i];
            const playerName = playerElement.dataset.playerName;
            const isCurrentPlayer = playerName === currentUsername;
            const isCurrentTurn = playerName === currentTurnPlayer;
            
            // Clone the player entry
            const playerDiv = playerElement.cloneNode(true);
            
            // Find the player name label in the cloned element
            const nameLabel = playerDiv.querySelector('.player-name-label');
            
            // Only add "(You)" if it's not already there
            if (nameLabel && isCurrentPlayer && !nameLabel.textContent.includes("(You)")) {
                nameLabel.textContent += " (You)";
            }
            
            // Apply visual distinction if it's the player whose turn it is
            if (isCurrentTurn) {
                playerDiv.classList.add('active-player');
                console.log(`Adding active-player class to ${playerName}`);
            } else {
                playerDiv.classList.remove('active-player');
            }
            
            opponentRow.appendChild(playerDiv);
            playersDisplayed = true;
        }

        if (playersDisplayed) {
            opponentRow.style.display = 'flex'; // Show the player row with flex layout
        } else {
            opponentRow.style.display = 'none'; // Keep it hidden if no players
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
        
        // Debug logging to help diagnose the issue
        console.log(`Updating hand interactivity. Is my turn: ${isMyTurn}, Current suit: ${currentSuit}, Top card:`, currentTopCard);
        
        // Update responsive card classes based on cards per row (8 cards per row)
        const cardCount = handCards.length;
        const cardsPerRow = 8;
        const numberOfRows = Math.ceil(cardCount / cardsPerRow);
        
        console.log(`Card count: ${cardCount}, Cards per row: ${cardsPerRow}, Number of rows: ${numberOfRows}`);
        console.log(`Current classes before removal:`, playerHandDiv.className);
        
        playerHandDiv.classList.remove('many-cards', 'lots-of-cards', 'overflow-cards');
        
        if (numberOfRows === 2) {
            playerHandDiv.classList.add('many-cards');
            console.log('Added many-cards class');
        } else if (numberOfRows === 3) {
            playerHandDiv.classList.add('lots-of-cards');
            console.log('Added lots-of-cards class');
        } else if (numberOfRows > 3) {
            playerHandDiv.classList.add('overflow-cards');
            console.log('Added overflow-cards class');
        }
        
        console.log(`Final classes:`, playerHandDiv.className);
        
        handCards.forEach(cardElement => {
            cardElement.classList.remove('playable'); // Reset first

            if (isMyTurn && currentTopCard) {
                const handCardData = parseCardString(cardElement.dataset.cardString);
                if (handCardData) {
                    // 8s are wild cards and always playable
                    if (handCardData.value === '8') {
                        cardElement.classList.add('playable');
                        console.log(`Card ${cardElement.dataset.cardString} is playable (it's an 8)`);
                    }
                    // Match by value
                    else if (handCardData.value === currentTopCard.value) {
                        cardElement.classList.add('playable');
                        console.log(`Card ${cardElement.dataset.cardString} is playable (matches top card value ${currentTopCard.value})`);
                    }
                    // Match by suit - use the declared suit (currentSuit) if set, otherwise use top card's suit
                    else if (currentSuit && handCardData.suit.toLowerCase() === currentSuit.toLowerCase()) {
                        cardElement.classList.add('playable');
                        console.log(`Card ${cardElement.dataset.cardString} is playable (matches declared suit ${currentSuit})`);
                    }
                    // If no declared suit, match by top card's suit
                    else if (!currentSuit && handCardData.suit === currentTopCard.suit) {
                        cardElement.classList.add('playable');
                        console.log(`Card ${cardElement.dataset.cardString} is playable (matches top card suit ${currentTopCard.suit})`);
                    }
                    else {
                        console.log(`Card ${cardElement.dataset.cardString} is NOT playable. Card suit: ${handCardData.suit}, Current suit: ${currentSuit || currentTopCard.suit}`);
                    }
                }
            }
        });
    }
    
    // Function to update the draw button state based on turn
    function updateDrawButtonState() {
        if (drawBtn) {
            drawBtn.disabled = !isMyTurn;
            drawBtn.title = isMyTurn ? "Draw a card from the deck" : "Wait for your turn to draw";
        }
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
                case 'chat_message': // Handle incoming chat messages from other players
                    if (message.sender && message.message && chatMessages) {
                        // Create and display the chat message from another player
                        const messageElement = document.createElement('div');
                        messageElement.className = 'chat-message';
                        messageElement.innerHTML = `<span class="username">${sanitizeHTML(message.sender)}:</span><span class="message">${sanitizeHTML(message.message)}</span>`;
                        chatMessages.appendChild(messageElement);
                        
                        // Scroll to the bottom to show the new message
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                    break;
                
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
                            
                            // Add "(You)" to your own name in the waiting screen
                            playerNameLabelDiv.textContent = playerName === currentUsername ? 
                                `${sanitizeHTML(playerName)} (You)` : sanitizeHTML(playerName);

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
                            playerNameLabelDiv.textContent = sanitizeHTML(message.player);

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
                            
                            // Add a notification in the chat that a player joined
                            if (chatMessages) {
                                const joinMsg = document.createElement('div');
                                joinMsg.className = 'chat-message';
                                joinMsg.innerHTML = `<span class="username">Game: </span><span class="message">${sanitizeHTML(message.player)} joined the game</span>`;
                                chatMessages.appendChild(joinMsg);
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                            }
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
                        
                        // Add a notification in the chat that a player left
                        if (chatMessages) {
                            const leaveMsg = document.createElement('div');
                            leaveMsg.className = 'chat-message';
                            leaveMsg.innerHTML = `<span class="username">Game: </span><span class="message">${sanitizeHTML(message.player)} left the game</span>`;
                            chatMessages.appendChild(leaveMsg);
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        }
                    }
                    updateStartButtonState(); // Update after list change
                    break;
                case 'game_started': // Game has started
                    if (waitingOverlay) {
                        waitingOverlay.style.display = 'none';
                    }
                    displayPlayers(); // Display players
                    console.log('Game started. Current turn:', message.currentTurn, 'Top card:', message.topCard, 'Current suit:', message.currentSuit);
                    
                    isMyTurn = (message.currentTurn === currentUsername);
                    currentTurnPlayer = message.currentTurn;
                    console.log(isMyTurn ? "It's your turn!" : "Waiting for your turn.");

                    
                    if (message.topCard && communityCardsDiv) { // communityCardsDiv check, currentSuit is in parsed cardData
                        communityCardsDiv.innerHTML = ''; // Clear previous cards
                        communityCardsDiv.classList.add('card-container'); // Apply layout styling

                        const cardData = parseCardString(message.topCard); // Use parseCardString for topCard too
                        if (cardData) {
                            currentTopCard = cardData; // Store the current top card
                            const topCardElement = createCardElement(cardData, message.topCard);
                            topCardElement.classList.add('community-card'); // Add the new community-card class
                            communityCardsDiv.appendChild(topCardElement);
                        }
                    }
                    updateHandInteractivity(); // Update hand based on whose turn it is
                    updateDrawButtonState(); // Update draw button state
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
                        currentTurnPlayer = message.currentTurn;
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
                                attachCardClickHandler(cardElement);
                                playerHandDiv.appendChild(cardElement);
                            }
                        });
                    }
                    updateHandInteractivity();
                    updateDrawButtonState(); // Update draw button state
                    displayPlayers(); // Update player display for turn change
                    break;
                case 'move_made': // Handle when a player plays a card
                    const moveDetails = message.move || {};
                    const topCard = moveDetails.topCard;
                    const moveSuit = moveDetails.currentSuit;  // Renamed from currentSuit to avoid shadowing
                    const player = message.player;
                    const playedCard = moveDetails.card;
                    const declaredSuit = moveDetails.declaredSuit;
                    
                    // Update global currentSuit if available in the move
                    if (moveSuit) {
                        currentSuit = moveSuit;
                    } else if (!playedCard.startsWith('8')) {
                        // If a non-8 card is played and no specific suit is declared in the move,
                        // reset the currentSuit to null to ensure we use the card's natural suit
                        currentSuit = null;
                    }
                    
                    console.log(`Player ${player} played ${playedCard}${declaredSuit ? ' (declared '+declaredSuit+')' : ''}`);
                    console.log(`Current suit after move: ${currentSuit || 'None (using card suit)'}`);
                    
                    // If I played the card, ensure my turn is over
                    if (player === currentUsername) {
                        isMyTurn = false;
                    }
                    
                    // Update UI state
                    if (topCard && communityCardsDiv) {
                        communityCardsDiv.innerHTML = ''; // Clear previous cards
                        const cardData = parseCardString(topCard);
                        if (cardData) {
                            currentTopCard = cardData; // Store the current top card
                            
                            // For 8 cards, show the declared suit visually on the card
                            if (declaredSuit && cardData.value === '8') {
                                // Create a modified card element that shows the declared suit
                                const topCardElement = document.createElement('div');
                                topCardElement.classList.add('card', 'community-card');
                                topCardElement.classList.add(declaredSuit.toLowerCase()); // Add the declared suit as class
                                topCardElement.dataset.cardString = topCard;
                                topCardElement.dataset.value = cardData.value;
                                
                                // Create value display
                                const valueDiv = document.createElement('div');
                                valueDiv.classList.add('card-value');
                                valueDiv.textContent = cardData.value;
                                
                                // Create suit display with the declared suit
                                const suitDiv = document.createElement('div');
                                suitDiv.classList.add('card-suit');
                                suitDiv.textContent = getSuitSymbol(declaredSuit);
                                
                                topCardElement.appendChild(valueDiv);
                                topCardElement.appendChild(suitDiv);
                                
                                communityCardsDiv.appendChild(topCardElement);
                            } else {
                                // Normal card display
                                const topCardElement = createCardElement(cardData, topCard);
                                topCardElement.classList.add('community-card');
                                communityCardsDiv.appendChild(topCardElement);
                            }
                        }
                    }
                    
                    // If the current player made this move, remove the card from their hand
                    if (player === currentUsername) {
                        const handCards = playerHandDiv.querySelectorAll('.card');
                        for (let i = 0; i < handCards.length; i++) {
                            if (handCards[i].dataset.cardString === playedCard) {
                                handCards[i].remove();
                                break;
                            }
                        }
                    }
                    
                    // Add a notification in the chat or game log if you have one
                    
                    if (chatMessages) {
                        const moveMsg = document.createElement('div');
                        moveMsg.className = 'chat-message';
                        moveMsg.innerHTML = `<span class="username">Game: </span><span class="message">${sanitizeHTML(player)} played ${sanitizeHTML(playedCard)}${declaredSuit ? ' (declared '+sanitizeHTML(declaredSuit)+')' : ''}</span>`;
                        chatMessages.appendChild(moveMsg);
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                    break;
                
                case 'turn_change': // Add proper handling for turn changes
                    isMyTurn = (message.currentTurn === currentUsername);
                    currentTurnPlayer = message.currentTurn;
                    
                    // Update top card if provided
                    if (message.topCard && communityCardsDiv) {
                        const cardData = parseCardString(message.topCard);
                        if (cardData && (!currentTopCard || 
                            currentTopCard.value !== cardData.value || 
                            currentTopCard.suit !== cardData.suit)) {
                            
                            communityCardsDiv.innerHTML = '';
                            currentTopCard = cardData;
                            const topCardElement = createCardElement(cardData, message.topCard);
                            topCardElement.classList.add('community-card'); // Add community-card class
                            communityCardsDiv.appendChild(topCardElement);
                            
                            // If we have a declared suit (especially after an 8 is played)
                            if (message.currentSuit && cardData.value === '8') {
                                // Add visual indicator of the declared suit
                                const declaredSuitIndicator = document.createElement('div');
                                declaredSuitIndicator.className = 'declared-suit-indicator';
                                declaredSuitIndicator.innerHTML = `Declared suit: <span class="declared-suit-value">${sanitizeHTML(message.currentSuit)}</span>`;
                                communityCardsDiv.appendChild(declaredSuitIndicator);
                                
                                // Update the card visually to show the declared suit
                                topCardElement.className = 'card community-card'; // Reset classes
                                topCardElement.classList.add(message.currentSuit.toLowerCase());
                                
                                // Update the suit display
                                const suitDiv = topCardElement.querySelector('.card-suit');
                                if (suitDiv) {
                                    suitDiv.textContent = getSuitSymbol(message.currentSuit);
                                }
                            }
                        }
                    }
                    
                    // Always update current suit if provided, especially important after an 8 is played
                    if (message.currentSuit) {
                        currentSuit = message.currentSuit;
                    }
                    
                    // Clear any previous turn highlights
                    const allPlayerEntries = document.querySelectorAll('.player-entry');
                    allPlayerEntries.forEach(entry => {
                        entry.classList.remove('active-player');
                        entry.style.cssText = ''; // Remove any inline styles
                    });
                    
                    // Update the interactivity of cards
                    updateHandInteractivity();
                    updateDrawButtonState(); // Update draw button state
                    
                    // Always call displayPlayers to update the visual turn indicator
                    displayPlayers();
                    
                    // Add turn indication in chat
                    const chatMsgs = document.getElementById('chat-messages');
                    if (chatMsgs) {
                        const turnMsg = document.createElement('div');
                        turnMsg.className = 'chat-message';
                        turnMsg.innerHTML = `<span class="username">Game: </span><span class="message">It's ${sanitizeHTML(message.currentTurn)}'s turn</span>`;
                        chatMsgs.appendChild(turnMsg);
                        chatMsgs.scrollTop = chatMsgs.scrollHeight;
                    }
                    
                    console.log(`Turn changed to: ${message.currentTurn}. Is my turn: ${isMyTurn}`);
                    break;
                
                case 'card_drawn': { // Handle when a player draws a card
                    const drawingPlayer = message.player;
                    const drawnCard = message.card; // Will be null for other players

                    // If I drew the card, add it to my hand
                    if (drawingPlayer === currentUsername && drawnCard) {
                        const cardData = parseCardString(drawnCard);
                        if (cardData && playerHandDiv) {
                            const cardElement = createCardElement(cardData, drawnCard);
                            attachCardClickHandler(cardElement);
                            playerHandDiv.appendChild(cardElement);
                            
                            // Add a notification in chat
                            const chatMessages = document.getElementById('chat-messages');
                            if (chatMessages) {
                                const drawMsg = document.createElement('div');
                                drawMsg.className = 'chat-message';
                                drawMsg.innerHTML = `<span class="username">Game: </span><span class="message">You drew a card: ${sanitizeHTML(drawnCard)}</span>`;
                                chatMessages.appendChild(drawMsg);
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                            }
                        }
                    } else if (drawingPlayer !== currentUsername) {
                        // Someone else drew a card
                        const chatMessages = document.getElementById('chat-messages');
                        if (chatMessages) {
                            const drawMsg = document.createElement('div');
                            drawMsg.className = 'chat-message';
                            drawMsg.innerHTML = `<span class="username">Game: </span><span class="message">${sanitizeHTML(drawingPlayer)} drew a card</span>`;
                            chatMessages.appendChild(drawMsg);
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        }
                    }
                    
                    // Update card interactivity in case drawing changed playable cards
                    updateHandInteractivity();
                    break;
                }
                
                case 'draw_result': { // Handle the DRAW_RESULT action from server
                    const drawResult = message.drawResult || {};
                    const drawnCard = drawResult.card;
                    
                    // If a card was drawn successfully, add it to the player's hand
                    if (drawnCard) {
                        const cardData = parseCardString(drawnCard);
                        if (cardData && playerHandDiv) {
                            const cardElement = createCardElement(cardData, drawnCard);
                            attachCardClickHandler(cardElement);
                            playerHandDiv.appendChild(cardElement);
                            
                            // Add a notification in chat
                            const chatMessages = document.getElementById('chat-messages');
                            if (chatMessages) {
                                const drawMsg = document.createElement('div');
                                drawMsg.className = 'chat-message';
                                drawMsg.innerHTML = `<span class="username">Game: </span><span class="message">You drew a card: ${sanitizeHTML(drawnCard)}</span>`;
                                chatMessages.appendChild(drawMsg);
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                            }
                            
                            // Update hand interactivity if the card can be played immediately
                            if (drawResult.canPlay) {
                                updateHandInteractivity();
                            }
                        }
                    }
                    
                    // Show message if the game is blocked
                    if (drawResult.gameBlocked) {
                        const chatMessages = document.getElementById('chat-messages');
                        if (chatMessages) {
                            const blockMsg = document.createElement('div');
                            blockMsg.className = 'chat-message';
                            blockMsg.innerHTML = `<span class="username">Game: </span><span class="message">Game is blocked - no valid moves possible!</span>`;
                            chatMessages.appendChild(blockMsg);
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        }
                    }
                    break;
                }
                
                case 'game_over': // Handle game over message
                    const winner = message.winner;
                    const scores = message.scores || {};
                    const blocked = message.blocked || false;
                    const reason = message.reason || `${winner} won the game`;
                    
                    // Display game over information in chat
                    
                    if (chatMessages) {
                        // Add game over announcement
                        const gameOverMsg = document.createElement('div');
                        gameOverMsg.className = 'chat-message game-over';
                        
                        let gameOverText = `<span class="username">Game: </span><span class="message">Game Over! `;
                        if (blocked) {
                            gameOverText += `Game was blocked. Player with lowest score wins: ${sanitizeHTML(winner)}`;
                        } else {
                            gameOverText += `${sanitizeHTML(winner)} won!`;
                        }
                        
                        if (reason && reason !== `${winner} won`) {
                            gameOverText += ` (${sanitizeHTML(reason)})`;
                        }
                        
                        gameOverText += `</span>`;
                        gameOverMsg.innerHTML = gameOverText;
                        chatMessages.appendChild(gameOverMsg);
                        
                        // Add scores information
                        const scoresMsg = document.createElement('div');
                        scoresMsg.className = 'chat-message scores';
                        
                        let scoresText = `<span class="username">Game: </span><span class="message">Final Scores:<br>`;
                        for (const [player, score] of Object.entries(scores)) {
                            const isWinner = player === winner;
                            scoresText += `${sanitizeHTML(player)}: ${sanitizeHTML(score)} points${isWinner ? ' 🏆' : ''}<br>`;
                        }
                        scoresText += `</span>`;
                        scoresMsg.innerHTML = scoresText;
                        chatMessages.appendChild(scoresMsg);
                        
                        // Add play again message
                        const playAgainMsg = document.createElement('div');
                        playAgainMsg.className = 'chat-message';
                        playAgainMsg.innerHTML = `<span class="username">Game: </span><span class="message">Click 'Start Game' to play again.</span>`;
                        chatMessages.appendChild(playAgainMsg);
                        
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                    
                    // Reset game state
                    isMyTurn = false;
                    currentTopCard = null;
                    currentSuit = null;
                    
                    // Show the waiting overlay again
                    if (waitingOverlay) {
                        waitingOverlay.style.display = 'flex';
                    }
                    
                    // Clear the community cards
                    if (communityCardsDiv) {
                        communityCardsDiv.innerHTML = '';
                    }
                    
                    // Update UI elements
                    updateDrawButtonState();
                    console.log(`Game over! Winner: ${winner}, Reason: ${reason}`);
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

    // Add event listener for the draw button
    if (drawBtn) {
        console.log('Draw button found, adding event listener.');
        drawBtn.addEventListener('click', function() {
            if (!isMyTurn) {
                console.log("Not your turn to draw!");
                return;
            }

            console.log("Draw button clicked.");
            
            // Send draw card message to the server
            if (socket && socket.readyState === WebSocket.OPEN) {
                const drawMessage = {
                    action: 'draw_card'
                };
                socket.send(JSON.stringify(drawMessage));
                console.log('Draw card message sent');
                
            } else {
                console.error('WebSocket is not connected or not open.');
                alert('Error: Not connected to the server. Please try rejoining.');
            }
        });
    }
});
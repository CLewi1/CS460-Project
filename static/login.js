document.addEventListener('DOMContentLoaded', function() {
    // Get references to DOM elements
    const loginPanel = document.getElementById('login-panel');
    const gamePanel = document.getElementById('game-panel');
    const joinBtn = document.getElementById('join-btn');
    const usernameInput = document.getElementById('username');
    const playersList = document.getElementById('players');
    const container = document.querySelector('.container');
    

    // Add event listener for the join button
    joinBtn.addEventListener('click', function() {
        const username = usernameInput.value.trim();
        
        // Basic validation for the username
        if (username === '') {
            alert('Please enter a username');
            return;
        }
        
        // Hide login panel and show game panel
        loginPanel.style.display = 'none';
        gamePanel.style.display = 'block';
        container.classList.add('full-width');
        
        // Add the player to the waiting players list
        const playerItem = document.createElement('li');
        playerItem.textContent = username;
        playersList.appendChild(playerItem);
        
        // Here you would typically send this username to the server
        console.log('User joined:', username);
    });
});
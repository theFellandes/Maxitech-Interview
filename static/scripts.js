document.addEventListener('DOMContentLoaded', function() {
  const chatForm = document.getElementById('chat-form');
  const chatWindow = document.getElementById('chat-window');
  const userInput = document.getElementById('user-input');
  const loadingIndicator = document.getElementById('loading-indicator');
  const sessionIdField = document.getElementById('session_id');

  function appendMessage(message, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender === 'User' ? 'user-message' : 'bot-message');
    msgDiv.innerHTML = `<strong>${sender}:</strong> ${message}`;
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  chatForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    const userMessage = userInput.value.trim();
    if (!userMessage) return;
    appendMessage(userMessage, 'User');
    userInput.value = '';
    document.getElementById('submit-btn').disabled = true;
    loadingIndicator.style.display = 'inline';

    const formData = new FormData();
    formData.append('user_message', userMessage);
    formData.append('session_id', sessionIdField.value);

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        body: formData
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      appendMessage(data.bot_message, 'Bot');
    } catch (error) {
      console.error('Error:', error);
      appendMessage('Error processing message.', 'Bot');
    } finally {
      document.getElementById('submit-btn').disabled = false;
      loadingIndicator.style.display = 'none';
    }
  });
});

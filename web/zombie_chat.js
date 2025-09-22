// zombie_chat.js - Zombie Dialog System für Adventure Game

function zombie_chat(ws, initialMessage = null) {
    console.log('🧟 Zombie Chat wird gestartet...');

    // Chat-Array für die Konversation
    let chatArray = [];

    // Falls der Zombie den Dialog eröffnet
    if (initialMessage && initialMessage.trim() !== '') {
        chatArray.push({ zombiemessage: initialMessage });
    }

    // Erstelle das Chat-Overlay
    const overlay = createChatOverlay();
    document.body.appendChild(overlay);

    // Referenzen zu wichtigen Elementen
    const chatMessages = overlay.querySelector('#zombie-chat-messages');
    const inputField = overlay.querySelector('#zombie-chat-input');
    const sendButton = overlay.querySelector('#zombie-chat-send');
    const closeButton = overlay.querySelector('#zombie-chat-close');

    // Falls es eine initiale Nachricht gibt, zeige sie an
    if (initialMessage && initialMessage.trim() !== '') {
        addMessageToChat('zombie', initialMessage, chatMessages);
    }

    // Fokus auf Eingabefeld setzen
    inputField.focus();

    // Event Listener für Send-Button
    sendButton.addEventListener('click', sendMessage);

    // Event Listener für Close-Button
    closeButton.addEventListener('click', closeChat);

    // WebSocket Message Handler
    function handleWebSocketMessage(event) {
        try {
            const data = JSON.parse(event.data);
            if (data.zombiemessage !== undefined) {
                // Zombie-Antwort erhalten
                chatArray.push({ zombiemessage: data.zombiemessage });
                addMessageToChat('zombie', data.zombiemessage, chatMessages);

                // Prüfe ob Zombie das Gespräch beendet
                if (data.zombiemessage.toLowerCase().trim() === 'quit') {
                    closeChat();
                }
            }
        } catch (error) {
            console.error('❌ Fehler beim Parsen der WebSocket-Nachricht:', error);
        }
    }

    // WebSocket Listener hinzufügen
    ws.addEventListener('message', handleWebSocketMessage);

    // Funktion zum Senden einer Nachricht
    function sendMessage() {
        const message = inputField.value;
        if (message.trim() === '') return;

        // Prüfe ob Spieler "quit" eingibt
        if (message.toLowerCase().trim() === 'quit') {
            closeChat();
            return;
        }

        // Füge Spielernachricht zum Array hinzu
        chatArray.push({ playermessage: message });

        // Zeige Nachricht im Chat an
        addMessageToChat('player', message, chatMessages);

        // Sende gesamten Chat-Array über WebSocket
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ zombiechat: chatArray }));
        }

        // Eingabefeld leeren
        inputField.value = '';
        inputField.focus();
    }

    // Funktion zum Schließen des Chats
    function closeChat() {
        console.log('🧟 Zombie Chat wird beendet');

        // Sende closeChat-Nachricht an Server
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ closeChat: true }));
        }

        // WebSocket Listener entfernen
        ws.removeEventListener('message', handleWebSocketMessage);

        // Overlay entfernen
        if (overlay && overlay.parentNode) {
            overlay.parentNode.removeChild(overlay);
        }
    }

    // Hilfsfunktion zum Hinzufügen einer Nachricht zum Chat
    function addMessageToChat(sender, message, container) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `zombie-chat-message zombie-chat-message-${sender}`;

        const bubble = document.createElement('div');
        bubble.className = `zombie-chat-bubble zombie-chat-bubble-${sender}`;

        // Konvertiere Newlines zu HTML-Zeilenumbrüchen
        bubble.innerHTML = escapeHtml(message).replace(/\n/g, '<br>');

        messageDiv.appendChild(bubble);
        container.appendChild(messageDiv);

        // Scrolle nach unten
        container.scrollTop = container.scrollHeight;
    }

    // Hilfsfunktion zum Escapen von HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Funktion zum Erstellen des Chat-Overlays
    function createChatOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'zombie-chat-overlay';
        overlay.innerHTML = `
            <div id="zombie-chat-container">
                <div id="zombie-chat-header">
                    <span id="zombie-chat-title">Gespräch mit dem Zombie</span>
                    <button id="zombie-chat-close" aria-label="Chat schließen">×</button>
                </div>
                <div id="zombie-chat-messages"></div>
                <div id="zombie-chat-input-container">
                    <textarea id="zombie-chat-input" 
                             placeholder="Nachricht eingeben..." 
                             rows="3"></textarea>
                    <button id="zombie-chat-send">Senden</button>
                </div>
            </div>
        `;

        // Füge Styles hinzu
        const style = document.createElement('style');
        style.textContent = `
            #zombie-chat-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
                animation: fadeIn 0.3s ease-in;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            #zombie-chat-container {
                width: 90%;
                max-width: 500px;
                height: 80%;
                max-height: 600px;
                background: #1a1a1a;
                border-radius: 12px;
                display: flex;
                flex-direction: column;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8);
                border: 1px solid #333;
                animation: slideUp 0.3s ease-out;
            }
            
            @keyframes slideUp {
                from { 
                    transform: translateY(20px);
                    opacity: 0;
                }
                to { 
                    transform: translateY(0);
                    opacity: 1;
                }
            }
            
            #zombie-chat-header {
                background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%);
                color: #4caf50;
                padding: 15px 20px;
                border-radius: 12px 12px 0 0;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #333;
                font-weight: bold;
                font-size: 16px;
            }
            
            #zombie-chat-close {
                background: none;
                border: none;
                color: #888;
                font-size: 28px;
                cursor: pointer;
                padding: 0;
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 4px;
                transition: all 0.2s ease;
            }
            
            #zombie-chat-close:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #ff4444;
            }
            
            #zombie-chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                background: #0a0a0a;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            
            #zombie-chat-messages::-webkit-scrollbar {
                width: 8px;
            }
            
            #zombie-chat-messages::-webkit-scrollbar-track {
                background: #1a1a1a;
            }
            
            #zombie-chat-messages::-webkit-scrollbar-thumb {
                background: #333;
                border-radius: 4px;
            }
            
            #zombie-chat-messages::-webkit-scrollbar-thumb:hover {
                background: #444;
            }
            
            .zombie-chat-message {
                display: flex;
                animation: messageIn 0.3s ease-out;
            }
            
            @keyframes messageIn {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .zombie-chat-message-zombie {
                justify-content: flex-start;
            }
            
            .zombie-chat-message-player {
                justify-content: flex-end;
            }
            
            .zombie-chat-bubble {
                max-width: 75%;
                padding: 12px 16px;
                border-radius: 18px;
                word-wrap: break-word;
                position: relative;
                font-size: 14px;
                line-height: 1.4;
            }
            
            .zombie-chat-bubble-zombie {
                background: linear-gradient(135deg, #2d4a2d 0%, #1a3a1a 100%);
                color: #4caf50;
                border: 1px solid #2a5a2a;
                margin-left: 8px;
            }
            
            .zombie-chat-bubble-zombie::before {
                content: '';
                position: absolute;
                left: -8px;
                top: 12px;
                width: 0;
                height: 0;
                border-top: 8px solid transparent;
                border-bottom: 8px solid transparent;
                border-right: 8px solid #2d4a2d;
            }
            
            .zombie-chat-bubble-player {
                background: linear-gradient(135deg, #0066cc 0%, #004499 100%);
                color: #ffffff;
                border: 1px solid #0055aa;
                margin-right: 8px;
            }
            
            .zombie-chat-bubble-player::after {
                content: '';
                position: absolute;
                right: -8px;
                top: 12px;
                width: 0;
                height: 0;
                border-top: 8px solid transparent;
                border-bottom: 8px solid transparent;
                border-left: 8px solid #0066cc;
            }
            
            #zombie-chat-input-container {
                padding: 15px;
                background: #1a1a1a;
                border-top: 1px solid #333;
                border-radius: 0 0 12px 12px;
                display: flex;
                gap: 10px;
                align-items: flex-end;
            }
            
            #zombie-chat-input {
                flex: 1;
                background: #0a0a0a;
                border: 1px solid #333;
                color: #ffffff;
                padding: 10px 12px;
                border-radius: 8px;
                resize: none;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 14px;
                line-height: 1.4;
                transition: border-color 0.2s ease;
            }
            
            #zombie-chat-input:focus {
                outline: none;
                border-color: #4caf50;
                background: #111;
            }
            
            #zombie-chat-input::placeholder {
                color: #666;
            }
            
            #zombie-chat-send {
                background: linear-gradient(135deg, #4caf50 0%, #388e3c 100%);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: bold;
                font-size: 14px;
                transition: all 0.2s ease;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
            }
            
            #zombie-chat-send:hover {
                background: linear-gradient(135deg, #5cbf60 0%, #4caf50 100%);
                transform: translateY(-1px);
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4);
            }
            
            #zombie-chat-send:active {
                transform: translateY(0);
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
            }
        `;
        document.head.appendChild(style);

        return overlay;
    }
}

console.log('🧟 zombie_chat.js geladen');

console.log('🚀 Adventure mit Mini-Games startet...');
const welc = ` <h1>Willkommen in der Wüste</h1>

<p> <strong>Eine komische Situation</strong>: Du radelst mit Deinem Fahrrad als Bote
unter sengender Sonne entlang einer schnurgraden Strasse durch eine
endlose Wüste. Bei Dir hast Du einen Umschlag, den Du an ein Ziel 
bringen musst. Erreicht der Umschlag das Ziel nicht, so geht die Welt 
unter, aber das ist eine andere Geschichte.

<p> Plötzlich reisst Dir die Fahrradkette - das Fahrrad funktioniert ohne
sie nicht mehr. Glücklicherweise bist Du an einem Ort gestrandet, an
dem es Rettung geben könnte. 
<p> <strong>Und nun?</strong>
<p> (Weiter mit einem Mausklick) `;

window.onload =function() {
    showWelcome(welc);
};
let gameState = {
    round: 1,
    player: { name: "WebPlayer", location: "Start", thirst: 40, inventory: [] },
    environment: { objects: [], ways: [], blockedWays: [] },
    dog: {location: "Geldautomat", state:"Hund tut nichts..."},
    lastAction: { command: "Noch keine", result: "Warte auf Verbindung..." }
};

let backend = null;

class AdventureBackend {
    constructor() {
        this.ws = null;
        this.connect();
    }

    connect() {
        const status = document.getElementById('connection-status');
        if (status) status.textContent = 'Verbinde...';

        try {
            this.ws = new WebSocket('ws://localhost:8765');

            this.ws.onopen = () => {
                console.log('✅ Verbunden');
                if (status) status.textContent = '🟢 Verbunden';
                document.getElementById('user-input').disabled = false;
                document.getElementById('send-button').disabled = false;
            };

            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            };

            this.ws.onclose = () => {
                console.log('🔌 Verbindung getrennt');
                if (status) status.textContent = '🔴 Getrennt';
                document.getElementById('user-input').disabled = true;
                document.getElementById('send-button').disabled = true;
            };

        } catch (error) {
            console.error('❌ Verbindungsfehler:', error);
            if (status) status.textContent = '❌ Fehler';
        }
    }

    sendCommand(command) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'command', command: command }));
        }
    }

    sendMinigameResult(gameType, result) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'minigame_result',
                game_type: gameType,
                result: result
            }));
            console.log(`🎮 Mini-Game Ergebnis gesendet: ${gameType} -> ${result}`);
        }
    }

    handleMessage(data) {
        console.log("++++handleMessage:")
        console.log("data = ", data);
        console.log("data.type = ", data.type);
        switch(data.type) {
            case 'game_state':
                this.updateGameState(data.data);
                break;
            case 'command_result':
                if (data.results && data.results.length > 0) {
                    gameState.lastAction = {
                        command: data.command,
                        result: data.results[data.results.length - 1].result
                    };
                }
                if (data.game_state) this.updateGameState(data.game_state);
                else updateUI();
                this.updateDebugInfo(data);
                break;
            case 'npc_actions':
                if (data.actions && data.actions.length > 0) {
                    this.handleNPCActions(data.actions);
                }
                if (data.game_state) this.updateGameState(data.game_state);
                else updateUI();
                break;
            case 'start_minigame':  // NEUE
                this.startMinigame(data.game_type, data.game_data);
                break;
            case 'minigame_complete': // NEUE
                this.handleMinigameComplete(data);
                break;
            case 'pinpad':
                const hash = data.hash;
                showPinPad(hash).then(result => {
                    if (backend && backend.ws && backend.ws.readyState === WebSocket.OPEN) {
                        backend.ws.send(JSON.stringify({
                            type: "pinpad_result",
                            result: result
                        }));
                    }
                });
                break;
            case 'zombie_chat':
                const firstmsg = data.firstmsg;
                const who = data.who;
                const whom = data.whom;
                zombie_chat(this.ws,who, whom,firstmsg);
                break;
            case 'playername':
                askPlayerName().then(playerName => {
                    console.log(`Spielername: ${playerName}`);
                    // Hier können Sie mit dem Namen weiterarbeiten
                    if (backend && backend.ws && backend.ws.readyState === WebSocket.OPEN) {
                        backend.ws.send(JSON.stringify({
                            type: "playername_result",
                            result: playerName
                        }));
                    }
                });
                break;
            case 'game_over':
                const text = data.text
                const won = data.won
                gameOver(won,text)
                break;
            case 'info':
                gameState.lastAction = {
                    command: 'Info',
                    result: '💡 ' + data.message
                };
                updateUI();
                break;
            case 'error':
                gameState.lastAction = {
                    command: data.command || 'Fehler',
                    result: '❌ ' + data.message
                };
                updateUI();
                break;
        }
    }

    startMinigame(gameType, gameData) {
        console.log(`🎮 Starte Mini-Game: ${gameType}`);

        // Update UI
        gameState.lastAction = {
            command: 'Mini-Game',
            result: `🎮 ${gameType} wird gestartet...`
        };
        updateUI();

        // Deaktiviere normale Eingabe während Mini-Game
        document.getElementById('user-input').disabled = true;
        document.getElementById('send-button').disabled = true;

        // Starte Mini-Game
        if (miniGames) {
            miniGames.showGame(gameType, gameData, (result) => {
                // Re-aktiviere Eingabe
                document.getElementById('user-input').disabled = false;
                document.getElementById('send-button').disabled = false;

                // Sende Ergebnis an Server
                this.sendMinigameResult(gameType, result);
            });
        } else {
            console.error('❌ MiniGames nicht geladen!');
            // Re-aktiviere Eingabe bei Fehler
            document.getElementById('user-input').disabled = false;
            document.getElementById('send-button').disabled = false;
        }
    }


    handleMinigameComplete(data) {
        console.log(`✅ Mini-Game beendet:  ${data.result}`);

        // Zeige Ergebnismeldung
        gameState.lastAction = {
            command: `🎮 Minigame`,
            result: data.message
        };

        // Update Game State
        if (data.game_state) {
            this.updateGameState(data.game_state);
        } else {
            updateUI();
        }
    }

    handleNPCActions_old(actions) {
        // Sortiere NPC-Actions nach Typ
        let dogActions = [];
        let explosionTimers = [];
        let realExplosions = [];

        for (let action of actions) {
            if (action.includes('💥 EXPLOSION:') && action.includes('KABUMM')) {
                // Echte Explosion - ins Overlay
                let explosionText = action.replace('**💥 EXPLOSION:**', '').trim();
                realExplosions.push(explosionText);
            } else if (action.includes('💣 Timer:') || action.includes('explodiert in')) {
                // Timer-Nachricht - in letzte Aktion
                explosionTimers.push(action.replace('**💣 Timer:**', '').trim());
            } else if (action.includes('**Hund:**')) {
                // Hund-Aktion - update Hund-Status
                let dogAction = action.replace('**Hund:**', '').trim();
                dogActions.push(dogAction);
            } else if (action.includes('🎮') && action.includes('Mini-Game')) {
                // Mini-Game Ankündigung - zeige in letzter Aktion
                gameState.lastAction = {
                    command: 'Kampf-Vorbereitung',
                    result: action
                };
            }
        }

        // Verarbeite Timer-Nachrichten (in lastAction)
        if (explosionTimers.length > 0) {
            gameState.lastAction = {
                command: 'Explosion Timer',
                result: explosionTimers.join('\n')
            };
        }

        // Verarbeite Hund-Aktionen (update Hund-Status)
        if (dogActions.length > 0) {
            if (gameState.dog) {
                gameState.dog.state = dogActions[dogActions.length - 1]; // Letzte Aktion
            }
        }

        // Verarbeite echte Explosionen (Overlay)
        if (realExplosions.length > 0) {
            showExplosion(realExplosions.join('\n'));
        }

        updateUI();
    }

    handleNPCActions(actions) {
        // Sortiere NPC-Actions nach Typ
        let dogActions = [];
        let explosionTimers = [];
        let realExplosions = [];
        console.log("+++++ handleNPCActions:")
        console.log("Actions = ", actions)
        for (let action of actions) {
            console.log("Single Action = ", action)
            switch (action.command) {
                case 'do_explosion':
                    realExplosions.push(action.message);
                    break;
                case "explosion_message":
                    explosionTimers.push(action.message);
                    showExplosionMessage(action.message)
                    break;
                case "dog_message":
                    dogActions.push(action.message);
                    break;
                case "minigame":
                    gameState.lastAction = {
                        command: 'Kampf-Vorbereitung',
                        result: action.message
                    };
                    break;
            }
        }

        // Verarbeite Timer-Nachrichten (in lastAction)
        if (explosionTimers.length > 0) {
            gameState.lastAction = {
                command: 'Explosion Timer',
                result: explosionTimers.join('\n')
            };
        }

        // Verarbeite Hund-Aktionen (update Hund-Status)
        if (dogActions.length > 0) {
            if (gameState.dog) {
                gameState.dog.state = dogActions[dogActions.length - 1]; // Letzte Aktion
            }
        }

        // Verarbeite echte Explosionen (Overlay)
        if (realExplosions.length > 0) {
            hideExplosionMessage()
            showExplosion(realExplosions.join('\n'));
        }

        updateUI();
    }

    updateGameState(newState) {
        Object.assign(gameState, newState);
        updateUI();

        if (newState.scene_description) {
            const content = document.getElementById('scene-content');
            if (content) content.innerHTML = newState.scene_description.replace(/\n/g, '<br>');

                // ✨ Flash-Effekt auf Panel "scene"
            console.log("Attempting to flash scene-content panel")
            const panel = document.getElementById('scene');
            if (panel) {
                console.log("Found panel")
                panel.classList.remove('flash-scene'); // falls schon vorhanden
                void panel.offsetWidth; // Reflow erzwingen
                panel.classList.add('flash-scene');
            }
            else
                console.log("panel not found")
        }
    }

    updateDebugInfo(data) {
        const debugInfo = document.getElementById('debug-info');
        if (debugInfo) {
            const pendingCommands = data.pending_commands || 0;
            const hasPendingInput = data.has_pending_input || false;
            const executedCommand = data.executed_command || 'unknown';
            const pendingPreview = data.pending_input_preview || '';

            debugInfo.innerHTML = `Debug: Executed: <strong>${executedCommand}</strong>, Queue: ${pendingCommands}, Pending: ${hasPendingInput}` +
                                 (pendingPreview ? `<br>Next: "${pendingPreview}"` : '');
        }
    }
}

function isNearby(loc1, loc2) {
    const ways = gameState.environment?.ways || [];
    return ways.includes(loc2);
}

function updateDogDanger() {
    const playerLoc = gameState.player?.location || '';
    const dogLoc = gameState.dog?.location || '';
    const dogDiv = document.getElementById('dogstate');

    // Entferne alle Status-Klassen
    dogDiv.classList.remove('dog-danger', 'dog-nearby', 'dog-safe');

    if (playerLoc === dogLoc && playerLoc !== '') {
        // Gleicher Ort - GEFAHR!
        dogDiv.classList.add('dog-danger');
    } else if (isNearby(playerLoc, dogLoc)) {
        // Nachbar-Ort - Warnung
        dogDiv.classList.add('dog-nearby');
    } else {
        // Weit weg - sicher
        dogDiv.classList.add('dog-safe');
    }
}

function updateStatus() {

    const plDiv = document.getElementById('status');
    const thirst = (gameState.player?.thirst || 40)

    // Entferne alle Status-Klassen
    plDiv.classList.remove('player-danger', 'player-thirsty', 'player-safe');

    if (thirst>=20) {
        plDiv.classList.add('player-safe')
    } else if (thirst>=10) {
        plDiv.classList.add('player-thirsty')
    } else {
        plDiv.classList.add('player-danger')
    }
}

function updateUI() {
    try {
        const playerName = document.getElementById('player-name');
        const location = document.getElementById('location');
        const thirstValue = document.getElementById('thirst-value');

        if (playerName) playerName.textContent = 'Spieler: ' + (gameState.player?.name || 'Unbekannt');
        if (location) location.textContent = 'Ort: ' + (gameState.player?.location || 'Unbekannt');
        if (thirstValue) thirstValue.textContent = 'In ' + (gameState.player?.thirst || 40) + ' Spielzügen verdurstest du.'

        const inventory = document.getElementById('inventory');
        if (inventory) {
            const items = gameState.player?.inventory || [];
            if (items.length === 0) {
                inventory.innerHTML = '<em>Leer</em>';
            } else {
                inventory.innerHTML = items.map(item => '<div>• ' + item + '</div>').join('');
            }
        }

        const objectsList = document.getElementById('objects-list');
        if (objectsList) {
            const objects = gameState.environment?.objects || [];
            if (objects.length === 0) {
                objectsList.innerHTML = '<li><em>Keine Objekte</em></li>';
            } else {
                objectsList.innerHTML = objects.map(obj => '<li>' + obj + '</li>').join('');
            }
        }

        const waysList = document.getElementById('ways-list');
        if (waysList) {
            const ways = gameState.environment?.ways || [];
            if (ways.length === 0) {
                waysList.innerHTML = '<li><em>Keine Wege</em></li>';
            } else {
                waysList.innerHTML = ways.map(way => '<li>' + way + '</li>').join('');
            }
        }

        const commandText = document.getElementById('command-text');
        const resultText = document.getElementById('result-text');

        if (commandText) commandText.textContent = gameState.lastAction?.command || 'Noch keine';
        if (resultText) resultText.innerHTML = (gameState.lastAction?.result || 'Warte...').replace(/\n/g, '<br>');

        const dog_loc = document.getElementById('dog-location')
        const dog_state = document.getElementById('dog-state')

        if (dog_loc) dog_loc.textContent = "Der Hund ist momentan hier: "+ (gameState.dog?.location || 'Unbekannt');
        if (dog_state) dog_state.textContent =  (gameState.dog?.state || 'Der Hund döst vor sich hin');
        updateDogDanger()
        updateStatus()
        showPowerMain(gameState.power_main)

    } catch (error) {
        console.error('❌ UI-Fehler:', error);
    }
}

function sendCommand() {
    const input = document.getElementById('user-input');
    if (!input) return;

    const command = input.value.trim();
    if (!command) return;

    input.value = '';

    if (backend) {
        backend.sendCommand(command);
    } else {
        console.error('❌ Kein Backend');
    }
}

function showExplosion_old(text) {
    const overlay = document.getElementById("explosion-overlay");
    const messageBox = document.getElementById("explosion-message");
    const particlesContainer = document.getElementById("explosion-particles");
    const shockwave = document.getElementById("shockwave");

    overlay.style.display = "flex";
    messageBox.style.display = "none";
    particlesContainer.innerHTML = "";
    shockwave.style.display = "block";

    //
    // In case game over directly follows the explosion
    //

    window.explosion_running = true;

    const centerX = window.innerWidth / 2;
    const centerY = window.innerHeight / 2;
    shockwave.style.left = `${centerX - 25}px`;
    shockwave.style.top = `${centerY - 25}px`;

    // --- Trümmerteilchen ---
    for (let i = 0; i < 80; i++) {
        const angle = Math.random() * 2 * Math.PI;
        const distance = 100 + Math.random() * 200;
        const dx = Math.cos(angle) * distance;
        const dy = Math.sin(angle) * distance;
        const size = 4 + Math.random() * 8;

        const p = document.createElement("div");
        p.className = "particle";
        p.style.width = `${size}px`;
        p.style.height = `${size}px`;
        p.style.left = `${centerX - size / 2}px`;
        p.style.top = `${centerY - size / 2}px`;
        p.style.animationDuration = `${1.5 + Math.random()}s`;
        p.style.animationDelay = `${Math.random() * 0.4}s`;
        p.style.setProperty("--translate", `translate(${dx}px, ${dy}px)`);

        particlesContainer.appendChild(p);
    }

    // --- Glitzer-Sparkles ---
    for (let i = 0; i < 30; i++) {
        const angle = Math.random() * 2 * Math.PI;
        const distance = 80 + Math.random() * 150;
        const size = 2 + Math.random() * 4;

        const sparkle = document.createElement("div");
        sparkle.className = "sparkle";
        sparkle.style.width = `${size}px`;
        sparkle.style.height = `${size}px`;
        sparkle.style.left = `${centerX - size / 2}px`;
        sparkle.style.top = `${centerY - size / 2}px`;

        // Vier zitternde Phasen
        const jitter = () => {
            const dx = (Math.random() - 0.5) * distance;
            const dy = (Math.random() - 0.5) * distance;
            return `translate(${dx}px, ${dy}px)`;
        };

        sparkle.style.setProperty("--sparkle-1", jitter());
        sparkle.style.setProperty("--sparkle-2", jitter());
        sparkle.style.setProperty("--sparkle-3", jitter());
        sparkle.style.setProperty("--sparkle-4", jitter());

        sparkle.style.animationDuration = `${1 + Math.random()}s`;
        sparkle.style.animationDelay = `${Math.random() * 0.3}s`;

        particlesContainer.appendChild(sparkle);
    }

    setTimeout(() => {
        messageBox.innerHTML = text.replace(/\n/g, "<br>");
        messageBox.style.display = "block";
    }, 4000);
}

function hideExplosion_old() {
    document.getElementById("explosion-overlay").style.display = "none";
    window.explosion_running = false;
}

// document.addEventListener('DOMContentLoaded', function() {
//     backend = new AdventureBackend();
//     updateUI();
//     setTimeout(() => {
//         const input = document.getElementById('user-input');
//         if (input) input.focus();
//     }, 1000);
// });


function showExplosion(text) {
    const overlay = document.getElementById("explosion-overlay");
    const messageBox = document.getElementById("explosion-message");
    const particlesContainer = document.getElementById("explosion-particles");
    const shockwave = document.getElementById("shockwave");

    overlay.style.display = "flex";
    messageBox.style.display = "none";
    particlesContainer.innerHTML = "";
    shockwave.style.display = "none"; // Verstecken da wir das Video nutzen

    //
    // In case game over directly follows the explosion
    //

    window.explosion_running = true;

    // Video-Element erstellen und abspielen
    const video = document.createElement("video");
    video.src = "explosion.mp4";
    video.autoplay = true;
    video.muted = true; // Nötig für autoplay in den meisten Browsern
    video.loop = false; // Video spielt nur einmal ab
    video.style.position = "absolute";
    video.style.top = "50%";
    video.style.left = "50%";
    video.style.transform = "translate(-50%, -50%)";
    video.style.width = "100vw"; // Skaliert auf Bildschirmbreite
    video.style.height = "auto"; // Behält Seitenverhältnis bei
    video.style.maxWidth = "none";
    video.style.maxHeight = "none";
    video.style.zIndex = "1";

    // Video in den particles-Container einfügen
    particlesContainer.appendChild(video);

    // Text-Overlay nach 4 Sekunden anzeigen (wie im Original)
    setTimeout(() => {
        messageBox.innerHTML = text.replace(/\n/g, "<br>");
        messageBox.style.display = "block";
    }, 4000);
}

function hideExplosion() {
    document.getElementById("explosion-overlay").style.display = "none";
    window.explosion_running = false;
}

document.addEventListener('DOMContentLoaded', function() {
    backend = new AdventureBackend();
    updateUI();
    setTimeout(() => {
        const input = document.getElementById('user-input');
        if (input) input.focus();
    }, 1000);
});

console.log('✅ Script mit Mini-Game Support geladen');

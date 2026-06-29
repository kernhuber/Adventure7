
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
    dog: { here: false, mood: 'normal' },
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
            case 'command_result': {
                const raw = (data.command || '').trim();
                if (raw) resetLastAction(raw);   // neue Benutzereingabe -> Feld leeren + Header
                const label = data.action_label || data.executed_command || '';
                let result = '';
                if (data.results && data.results.length > 0) {
                    result = data.results[data.results.length - 1].result || '';
                }
                appendCommandResult(label, result);
                if (data.game_state) this.updateGameState(data.game_state);
                else updateUI();
                break;
            }
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
            case 'manual_popup':
                // Lesetext (z.B. das Betriebshandbuch) als modales Popup anzeigen.
                if (typeof showTextPopup === 'function') {
                    showTextPopup(data.title || 'Dokument', data.content || '');
                }
                break;
            case 'info':
                appendLastAction(`<div style="color:#ffd700">💡 ${_fmt(data.message)}</div>`);
                break;
            case 'error':
                appendLastAction(`<div style="color:#ff6666">❌ ${_fmt(data.message)}</div>`);
                break;
        }
    }

    startMinigame(gameType, gameData) {
        console.log(`🎮 Starte Mini-Game: ${gameType}`);

        // Update UI
        appendLastAction(`<div style="color:#ffd700">🎮 ${_fmt(gameType)} wird gestartet...</div>`);
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
        appendLastAction(`<div style="color:#ffd700">🎮 ${_fmt(data.message)}</div>`);

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
                    // Hund-Status nur noch als Debug; Dialoge/Knurren erscheinen im Chat-Modal.
                    debugMessage('Hund', action.message);
                    break;
                case "zombie_message":
                    // Zombie-Äußerungen nur noch als Debug; Gespräche laufen über das Chat-Modal.
                    debugMessage('Zombie', action.message);
                    break;
                case "zombie_bite":
                    // Biss: dramatisches Popup + Status (Lebensenergie/Durst) blinkt auf.
                    debugMessage('Zombie', action.message);
                    if (typeof showBiteOverlay === 'function') showBiteOverlay(action.message);
                    flashStatus();
                    break;
                case "zombie_event":
                    // Story-Ereignisse des Zombies (Erinnerung, Erkenntnis, Erlösung,
                    // Erstarren, geteilte Energie) sichtbar ins Transkript "Letzte Aktion".
                    appendLastAction(`<div style="color:#ff7766">🧟 ${_fmt(action.message)}</div>`);
                    break;
                case "minigame":
                    // Der Hund greift an: Icon rot blinken lassen; die Ankündigung steht im Chat-Modal.
                    debugMessage('Hund', action.message);
                    if (typeof showDogOverlay === 'function') showDogOverlay(true, 'attack');
                    break;
            }
        }

        // Explosions-Timer sind Spielereignisse (keine Dialoge) -> in "Letzte Aktion"
        if (explosionTimers.length > 0) {
            appendLastAction(`<div style="color:#ffaa00">💣 ${_fmt(explosionTimers.join('\n'))}</div>`);
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

}

// Dog/zombie status lines are debug-only now (the panel was removed). Show them in
// the "Debug:" line and the console; dialogs themselves go to the chat modal.
function debugMessage(label, msg) {
    console.log(`[debug] ${label}: ${msg}`);
    const d = document.getElementById('debug-info');
    if (d) d.innerHTML = `Debug ${label}: ` + String(msg).replace(/\n/g, '<br>');
}

// Briefly flash the Status panel red (e.g. when the zombie bite costs life energy/thirst).
function flashStatus() {
    const s = document.getElementById('status');
    if (!s) return;
    s.classList.remove('bite-flash');
    void s.offsetWidth; // reflow to restart the animation
    s.classList.add('bite-flash');
    setTimeout(() => s.classList.remove('bite-flash'), 1600);
}

// --- "Letzte Aktion": accumulated log of the user input and the atomic commands ---
let lastActionLog = "";
function _esc(s) { const d = document.createElement('div'); d.textContent = String(s == null ? '' : s); return d.innerHTML; }
function _fmt(s) { return _esc(s).replace(/\n/g, '<br>'); }
function renderLastAction() {
    const el = document.getElementById('last-action-content');
    if (el) el.innerHTML = lastActionLog || 'Noch keine Eingabe.';
}
// Called when the user submits a new input -> clear and start with the "Eingabe:" header.
function resetLastAction(rawInput) {
    lastActionLog = '<strong>Eingabe:</strong> ' + _fmt(rawInput) +
        '<hr style="border:0;border-top:1px dashed #cd853f;margin:6px 0">';
    renderLastAction();
}
function appendLastAction(html) { lastActionLog += html; renderLastAction(); }
// One atomic command (label) followed by the game-engine response.
function appendCommandResult(label, result) {
    let html = '';
    if (label) html += `<div style="margin-top:6px;color:#ffd700">${_fmt(label)}</div>`;
    if (result != null && result !== '') html += `<div>--&gt; ${_fmt(result)}</div>`;
    appendLastAction(html);
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

        renderLastAction();

        // The dog is shown only as an icon (top-right) when at the player's location.
        // Yellow frame = angry, red frame = attacking (mini-game).
        if (typeof showDogOverlay === 'function') {
            showDogOverlay(gameState.dog?.here || false, gameState.dog?.mood || 'normal');
        }
        updateStatus()
        showPowerMain(gameState.power_main)
        // Zombie overlay - inline definition as fallback if zombie_overlay.js not loaded
        if (typeof showZombieOverlay === 'function') {
            showZombieOverlay(gameState.zombie?.here || false, gameState.zombie?.zstate || '');
        } else {
            _showZombieOverlayInline(gameState.zombie?.here || false, gameState.zombie?.zstate || '');
        }

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

// Inline zombie overlay (always available, no separate JS file needed)
function _showZombieOverlayInline(visible, state) {
    const ZOMBIE_ID = 'zombieOverlay';
    const GLOW = {AWAKENING:null, HUNTING:'#ff2222', COOPERATIVE:'#3399ff', DOUBTING:'#ff9900',
                  CONVINCED:'#33cc44', REDEEMED:'#ffffff', PETRIFIED:'#000000'};
    let overlay = document.getElementById(ZOMBIE_ID);
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = ZOMBIE_ID;
        overlay.style.cssText = 'position:fixed;top:0;right:125px;z-index:-1;width:125px;height:180px;border-radius:14px;pointer-events:none;';
        const img = document.createElement('img');
        img.id = ZOMBIE_ID + '_img';
        img.src = 'zombie.png';
        img.style.cssText = 'position:absolute;width:100%;height:100%;object-fit:contain;transition:opacity 0.5s ease, filter 0.5s ease;opacity:0;' +
            '-webkit-mask-image:radial-gradient(ellipse at center,black 70%,transparent 100%);' +
            'mask-image:radial-gradient(ellipse at center,black 70%,transparent 100%);' +
            '-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;' +
            '-webkit-mask-size:100% 100%;mask-size:100% 100%;';
        overlay.appendChild(img);
        document.body.appendChild(overlay);
    }
    const img = document.getElementById(ZOMBIE_ID + '_img');
    img.style.opacity = visible ? '1' : '0';
    const color = visible ? GLOW[(state || '').toUpperCase()] : null;
    overlay.style.boxShadow = color ? ('0 0 0 3px ' + color + ', 0 0 22px 8px ' + color) : 'none';
    img.style.filter = (visible && (state || '').toUpperCase() === 'PETRIFIED') ? 'grayscale(1) brightness(0.6)' : 'none';
}

console.log('✅ Script mit Mini-Game Support geladen');

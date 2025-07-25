/**
 * Mini-Games für das Adventure Web-Interface
 * Entspricht den Mini-Games aus MiniGames.py
 */

class MiniGames {
    constructor() {
        this.currentGame = null;
        this.gameData = null;
        this.onGameComplete = null;
        this.createOverlays();
    }

    createOverlays() {
        // Haupt-Overlay Container
        const overlay = document.createElement('div');
        overlay.id = 'minigame-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.9);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 10000;
            color: #f5deb3;
            font-family: monospace;
        `;

        const gameContainer = document.createElement('div');
        gameContainer.id = 'minigame-container';
        gameContainer.style.cssText = `
            background: #2c1810;
            border: 3px solid #cd853f;
            border-radius: 15px;
            padding: 30px;
            max-width: 600px;
            width: 90%;
            text-align: center;
            box-shadow: 0 0 20px rgba(205, 133, 63, 0.5);
        `;

        overlay.appendChild(gameContainer);
        document.body.appendChild(overlay);
    }

    showGame(gameType, gameData, onComplete) {
        this.currentGame = gameType;
        this.gameData = gameData;
        this.onGameComplete = onComplete;

        const overlay = document.getElementById('minigame-overlay');
        const container = document.getElementById('minigame-container');

        overlay.style.display = 'flex';

        switch(gameType) {
            case 'circle_fight':
                this.setupCircleFight(container);
                break;
            case 'sum_fight':
                this.setupSumFight(container, gameData);
                break;
            case 'odd_even_fight':
                this.setupOddEvenFight(container);
                break;
            case 'close_fight':
                this.setupCloseFight(container);
                break;
        }
    }

    hideGame() {
        const overlay = document.getElementById('minigame-overlay');
        overlay.style.display = 'none';
        this.currentGame = null;
        this.gameData = null;
        this.onGameComplete = null;
    }

    setupCircleFight(container) {
        container.innerHTML = `
            <h2>🥊 Kreis-Kampf</h2>
            <div style="margin: 20px 0; font-size: 14px; line-height: 1.6;">
                <p><strong>Regeln:</strong></p>
                <p>Beide wählen eine Zahl von 1-4:</p>
                <p><strong>4</strong> schlägt <strong>3</strong> • <strong>3</strong> schlägt <strong>2</strong> • <strong>2</strong> schlägt <strong>1</strong> • <strong>1</strong> schlägt <strong>4</strong></p>
                <p>Alles andere: Unentschieden</p>
            </div>
            <div id="circle-choices" style="margin: 30px 0;">
                <p style="font-size: 18px; margin-bottom: 20px;">Wähle deine Zahl:</p>
                <div style="display: flex; justify-content: center; gap: 15px;">
                    ${[1,2,3,4].map(num => `
                        <button class="choice-btn" data-choice="${num}" style="
                            background: #8b4513;
                            color: #f5deb3;
                            border: 2px solid #cd853f;
                            padding: 15px 25px;
                            font-size: 24px;
                            font-weight: bold;
                            border-radius: 50%;
                            cursor: pointer;
                            width: 60px;
                            height: 60px;
                            transition: all 0.3s;
                        " onmouseover="this.style.background='#cd853f'"
                           onmouseout="this.style.background='#8b4513'">${num}</button>
                    `).join('')}
                </div>
            </div>
            <div id="circle-result" style="font-size: 16px; min-height: 100px;"></div>
        `;

        container.querySelectorAll('.choice-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.playCircleFight(parseInt(e.target.dataset.choice));
            });
        });
    }

    playCircleFight(playerChoice) {
        const dogChoice = Math.floor(Math.random() * 4) + 1;
        const resultDiv = document.getElementById('circle-result');

        resultDiv.innerHTML = `
            <p><strong>Du hast:</strong> ${playerChoice}</p>
            <p><strong>Hund hat:</strong> ${dogChoice}</p>
        `;

        // Berechnung wie in MiniGames.py (umgestellt auf 0-3 für Modulo)
        const p = playerChoice - 1;
        const d = dogChoice - 1;

        let result;
        if ((d + 1) % 4 === p) {
            result = 'LOST'; // Hund verliert
            resultDiv.innerHTML += '<p style="color: #90ee90; font-weight: bold;">***Der Hund verliert den Kampf!***</p>';
        } else if ((p + 1) % 4 === d) {
            result = 'WON'; // Hund gewinnt
            resultDiv.innerHTML += '<p style="color: #ff6b6b; font-weight: bold;">***Du verlierst den Kampf gegen den Hund!***</p>';
        } else {
            result = 'TIE';
            resultDiv.innerHTML += '<p style="color: #ffd700; font-weight: bold;">***Unentschieden!***</p>';
        }

        setTimeout(() => {
            this.completeGame(result);
        }, 3000);
    }

    setupSumFight(container, gameData) {
        const { stones, reach, whoStarts } = gameData;
        let currentStones = [...stones];
        let stackSum = 0;
        let currentPlayer = whoStarts; // 0 = Hund, 1 = Spieler

        const updateDisplay = () => {
            const stackDiv = document.getElementById('sum-stack');
            const stonesDiv = document.getElementById('sum-stones');
            const playerDiv = document.getElementById('sum-current-player');

            stackDiv.innerHTML = `
                <p><strong>Ziel:</strong> ${reach}</p>
                <p><strong>Aktueller Stapel:</strong> ${stackSum}</p>
            `;

            stonesDiv.innerHTML = `
                <p style="margin-bottom: 15px;"><strong>Verfügbare Zahlen:</strong></p>
                <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 10px;">
                    ${currentStones.map(stone => `
                        <button class="stone-btn" data-stone="${stone}" 
                                ${currentPlayer === 0 ? 'disabled' : ''} style="
                            background: ${currentPlayer === 0 ? '#666' : '#8b4513'};
                            color: #f5deb3;
                            border: 2px solid #cd853f;
                            padding: 10px 15px;
                            font-size: 16px;
                            border-radius: 8px;
                            cursor: ${currentPlayer === 0 ? 'not-allowed' : 'pointer'};
                            transition: all 0.3s;
                        ">${stone}</button>
                    `).join('')}
                </div>
            `;

            playerDiv.innerHTML = `
                <p style="font-size: 18px; font-weight: bold; color: ${currentPlayer === 0 ? '#ff6b6b' : '#90ee90'};">
                    ${currentPlayer === 0 ? '🐕 Hund ist dran' : '👤 Du bist dran'}
                </p>
            `;

            // Event Listeners für Spieler-Züge
            if (currentPlayer === 1) {
                container.querySelectorAll('.stone-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const choice = parseInt(e.target.dataset.stone);
                        this.processSumFightMove(choice, currentStones, stackSum, reach, (newStones, newSum, result) => {
                            if (result) {
                                this.completeGame(result);
                                return;
                            }
                            currentStones = newStones;
                            stackSum = newSum;
                            currentPlayer = 0; // Wechsel zum Hund
                            updateDisplay();

                            // Hund-Zug nach kurzer Verzögerung
                            setTimeout(() => {
                                this.processDogSumFightMove(currentStones, stackSum, reach, (newStones, newSum, result) => {
                                    if (result) {
                                        this.completeGame(result);
                                        return;
                                    }
                                    currentStones = newStones;
                                    stackSum = newSum;
                                    currentPlayer = 1; // Zurück zu Spieler
                                    updateDisplay();
                                });
                            }, 1500);
                        });
                    });
                });
            }
        };

        container.innerHTML = `
            <h2>🎲 Zahlen-Summen-Spiel</h2>
            <div style="margin: 20px 0; font-size: 14px; line-height: 1.6;">
                <p><strong>Regeln:</strong></p>
                <p>Wähle abwechselnd Zahlen aus der Liste. Wer die Zielzahl genau erreicht, gewinnt!</p>
                <p>Wer die Zielzahl überschreitet oder nur noch überschreitende Zahlen übrig lässt, verliert!</p>
            </div>
            <div id="sum-stack" style="background: rgba(139, 69, 19, 0.3); padding: 15px; border-radius: 8px; margin: 20px 0;"></div>
            <div id="sum-current-player" style="margin: 20px 0;"></div>
            <div id="sum-stones"></div>
            <div id="sum-messages" style="margin-top: 20px; min-height: 50px; color: #ffd700;"></div>
        `;

        // Erster Zug falls Hund startet
        if (currentPlayer === 0) {
            setTimeout(() => {
                this.processDogSumFightMove(currentStones, stackSum, reach, (newStones, newSum, result) => {
                    if (result) {
                        this.completeGame(result);
                        return;
                    }
                    currentStones = newStones;
                    stackSum = newSum;
                    currentPlayer = 1;
                    updateDisplay();
                });
            }, 1000);
        }

        updateDisplay();
    }

    processSumFightMove(choice, stones, stackSum, reach, callback) {
        const newSum = stackSum + choice;
        const newStones = stones.filter(s => s !== choice);

        const messageDiv = document.getElementById('sum-messages');
        messageDiv.innerHTML = `<p>Du wählst: <strong>${choice}</strong></p>`;

        if (newSum === reach) {
            messageDiv.innerHTML += '<p style="color: #90ee90; font-weight: bold;">***Du hast gewonnen!***</p>';
            setTimeout(() => callback(newStones, newSum, 'LOST'), 2000); // LOST für Hund
            return;
        }

        if (newSum > reach) {
            messageDiv.innerHTML += '<p style="color: #ff6b6b; font-weight: bold;">***Du hast überschritten und verloren!***</p>';
            setTimeout(() => callback(newStones, newSum, 'WON'), 2000); // WON für Hund
            return;
        }

        // Prüfe ob noch spielbare Züge möglich sind
        const possibleMoves = newStones.filter(s => newSum + s <= reach);
        if (possibleMoves.length === 0) {
            messageDiv.innerHTML += '<p style="color: #ff6b6b; font-weight: bold;">***Keine gültigen Züge mehr - Du verlierst!***</p>';
            setTimeout(() => callback(newStones, newSum, 'WON'), 2000); // WON für Hund
            return;
        }

        callback(newStones, newSum, null);
    }

    processDogSumFightMove(stones, stackSum, reach, callback) {
        // Hund-KI wie in MiniGames.py
        let choice = 0;
        for (let stone of stones) {
            if (stone + stackSum === reach) {
                choice = stone;
                break;
            } else if (stone + stackSum < reach && stone > choice) {
                choice = stone;
            }
        }

        const newSum = stackSum + choice;
        const newStones = stones.filter(s => s !== choice);

        const messageDiv = document.getElementById('sum-messages');
        messageDiv.innerHTML = `<p>🐕 <strong>Hund wählt:</strong> ${choice}</p>`;

        if (newSum === reach) {
            messageDiv.innerHTML += '<p style="color: #ff6b6b; font-weight: bold;">***Der Hund hat gewonnen!***</p>';
            setTimeout(() => callback(newStones, newSum, 'WON'), 2000);
            return;
        }

        if (newSum > reach) {
            messageDiv.innerHTML += '<p style="color: #90ee90; font-weight: bold;">***Der Hund hat überschritten - Du gewinnst!***</p>';
            setTimeout(() => callback(newStones, newSum, 'LOST'), 2000);
            return;
        }

        // Prüfe ob noch spielbare Züge möglich sind
        const possibleMoves = newStones.filter(s => newSum + s <= reach);
        if (possibleMoves.length === 0) {
            messageDiv.innerHTML += '<p style="color: #ff6b6b; font-weight: bold;">***Keine gültigen Züge mehr - Hund gewinnt!***</p>';
            setTimeout(() => callback(newStones, newSum, 'WON'), 2000);
            return;
        }

        callback(newStones, newSum, null);
    }

    setupOddEvenFight(container) {
        container.innerHTML = `
            <h2>🎯 Gerade oder Ungerade</h2>
            <div style="margin: 20px 0; font-size: 14px; line-height: 1.6;">
                <p><strong>Regeln:</strong></p>
                <p>Beide wählen eine Zahl von 1-5</p>
                <p><strong>Gerade Summe:</strong> Der Hund gewinnt</p>
                <p><strong>Ungerade Summe:</strong> Du gewinnst</p>
                <p><strong>Gleiche Zahl:</strong> Unentschieden</p>
            </div>
            <div id="oddeven-choices" style="margin: 30px 0;">
                <p style="font-size: 18px; margin-bottom: 20px;">Wähle deine Zahl:</p>
                <div style="display: flex; justify-content: center; gap: 15px;">
                    ${[1,2,3,4,5].map(num => `
                        <button class="choice-btn" data-choice="${num}" style="
                            background: #8b4513;
                            color: #f5deb3;
                            border: 2px solid #cd853f;
                            padding: 15px 25px;
                            font-size: 24px;
                            font-weight: bold;
                            border-radius: 50%;
                            cursor: pointer;
                            width: 60px;
                            height: 60px;
                            transition: all 0.3s;
                        " onmouseover="this.style.background='#cd853f'"
                           onmouseout="this.style.background='#8b4513'">${num}</button>
                    `).join('')}
                </div>
            </div>
            <div id="oddeven-result" style="font-size: 16px; min-height: 100px;"></div>
        `;

        container.querySelectorAll('.choice-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.playOddEvenFight(parseInt(e.target.dataset.choice));
            });
        });
    }

    playOddEvenFight(playerChoice) {
        const dogChoice = Math.floor(Math.random() * 5) + 1;
        const resultDiv = document.getElementById('oddeven-result');

        resultDiv.innerHTML = `
            <p><strong>Du hast:</strong> ${playerChoice}</p>
            <p><strong>Hund hat:</strong> ${dogChoice}</p>
        `;

        if (playerChoice === dogChoice) {
            resultDiv.innerHTML += '<p style="color: #ffd700; font-weight: bold;">***Beide haben dieselbe Zahl! Unentschieden.***</p>';
            setTimeout(() => this.completeGame('TIE'), 3000);
            return;
        }

        const total = playerChoice + dogChoice;
        let result;

        if (total % 2 === 0) {
            result = 'WON'; // Hund gewinnt
            resultDiv.innerHTML += '<p style="color: #ff6b6b; font-weight: bold;">***Die Summe ist gerade – der Hund gewinnt!***</p>';
        } else {
            result = 'LOST'; // Hund verliert
            resultDiv.innerHTML += '<p style="color: #90ee90; font-weight: bold;">***Die Summe ist ungerade – du gewinnst!***</p>';
        }

        setTimeout(() => {
            this.completeGame(result);
        }, 3000);
    }

    setupCloseFight(container) {
        const secretNumber = Math.floor(Math.random() * 100) + 1;
        const dogChoice = Math.floor(Math.random() * 100) + 1;

        container.innerHTML = `
            <h2>🎯 Wer ist am nächsten dran?</h2>
            <div style="margin: 20px 0; font-size: 14px; line-height: 1.6;">
                <p><strong>Regeln:</strong></p>
                <p>Das System hat eine geheime Zahl zwischen 1 und 100 gewürfelt</p>
                <p>Beide wählen eine Zahl zwischen 1 und 100</p>
                <p>Wer näher an der geheimen Zahl liegt, gewinnt!</p>
            </div>
            <div id="close-input" style="margin: 30px 0;">
                <p style="font-size: 18px; margin-bottom: 20px;">Wähle deine Zahl (1-100):</p>
                <input type="number" id="close-number" min="1" max="100" 
                       style="background: #8b4513; color: #f5deb3; border: 2px solid #cd853f; 
                              padding: 10px; font-size: 18px; border-radius: 8px; width: 120px; text-align: center;">
                <br><br>
                <button id="close-submit" style="
                    background: #8b4513;
                    color: #f5deb3;
                    border: 2px solid #cd853f;
                    padding: 15px 30px;
                    font-size: 16px;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: all 0.3s;
                " onmouseover="this.style.background='#cd853f'"
                   onmouseout="this.style.background='#8b4513'">Bestätigen</button>
            </div>
            <div id="close-result" style="font-size: 16px; min-height: 100px;"></div>
        `;

        const submitBtn = document.getElementById('close-submit');
        const numberInput = document.getElementById('close-number');

        const playGame = () => {
            const playerChoice = parseInt(numberInput.value);

            if (isNaN(playerChoice) || playerChoice < 1 || playerChoice > 100) {
                alert('Bitte eine gültige Zahl zwischen 1 und 100 eingeben!');
                return;
            }

            this.playCloseFight(playerChoice, dogChoice, secretNumber);
        };

        submitBtn.addEventListener('click', playGame);
        numberInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                playGame();
            }
        });

        // Fokussiere das Eingabefeld
        setTimeout(() => numberInput.focus(), 100);
    }

    playCloseFight(playerChoice, dogChoice, secretNumber) {
        const resultDiv = document.getElementById('close-result');

        resultDiv.innerHTML = `
            <p><strong>Deine Wahl:</strong> ${playerChoice}</p>
            <p><strong>Hund hat gewählt:</strong> ${dogChoice}</p>
            <p><strong>Geheime Zahl:</strong> ${secretNumber}</p>
        `;

        if (playerChoice === dogChoice) {
            resultDiv.innerHTML += '<p style="color: #ffd700; font-weight: bold;">***Gleiche Zahl - Unentschieden!***</p>';
            setTimeout(() => this.completeGame('TIE'), 3000);
            return;
        }

        const playerDistance = Math.abs(secretNumber - playerChoice);
        const dogDistance = Math.abs(secretNumber - dogChoice);

        if (playerDistance === dogDistance) {
            resultDiv.innerHTML += '<p style="color: #ffd700; font-weight: bold;">***Gleicher Abstand - Unentschieden!***</p>';
            setTimeout(() => this.completeGame('TIE'), 3000);
        } else if (playerDistance > dogDistance) {
            resultDiv.innerHTML += `<p style="color: #ff6b6b; font-weight: bold;">***Der Hund ist näher dran (Abstand ${dogDistance}). Dein Abstand ist ${playerDistance}. Der Hund gewinnt!***</p>`;
            setTimeout(() => this.completeGame('WON'), 3000);
        } else {
            resultDiv.innerHTML += `<p style="color: #90ee90; font-weight: bold;">***Du bist näher dran (Abstand ${playerDistance}). Abstand des Hundes ist ${dogDistance}. Du gewinnst!***</p>`;
            setTimeout(() => this.completeGame('LOST'), 3000);
        }
    }

    completeGame(result) {
        if (this.onGameComplete) {
            this.onGameComplete(result);
        }
        this.hideGame();
    }
}

// Globale Instanz erstellen
let miniGames = null;

// Initialisierung wenn DOM geladen ist
document.addEventListener('DOMContentLoaded', function() {
    miniGames = new MiniGames();
});

// Export für andere Scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MiniGames;
}

/**
 * Erweiterte Mini-Game Features und Optimierungen
 * Diese Ergänzungen können zu minigames.js hinzugefügt werden
 */

// ============== ERWEITERTE MINIGAME-KLASSE ==============

class EnhancedMiniGames extends MiniGames {
    constructor() {
        super();
        this.gameHistory = [];
        this.playerStats = {
            circle_fight: { won: 0, lost: 0, tie: 0 },
            sum_fight: { won: 0, lost: 0, tie: 0 },
            odd_even_fight: { won: 0, lost: 0, tie: 0 },
            close_fight: { won: 0, lost: 0, tie: 0 }
        };
        this.soundEnabled = true;
        this.animationsEnabled = true;
    }

    // Überschreibe showGame für erweiterte Features
    showGame(gameType, gameData, onComplete) {
        // Statistik tracking
        this.gameHistory.push({
            type: gameType,
            startTime: Date.now(),
            data: gameData
        });

        // Sound-Effekt beim Start
        this.playSound('game_start');

        // Basis-Implementation aufrufen
        super.showGame(gameType, gameData, (result) => {
            this.updateStats(gameType, result);
            this.playSound(result === 'WON' ? 'dog_win' : result === 'LOST' ? 'player_win' : 'tie');
            onComplete(result);
        });
    }

    updateStats(gameType, result) {
        if (result === 'WON') {
            this.playerStats[gameType].lost++;
        } else if (result === 'LOST') {
            this.playerStats[gameType].won++;
        } else {
            this.playerStats[gameType].tie++;
        }

        // Speichere Stats in localStorage (falls verfügbar)
        try {
            localStorage.setItem('adventure_minigame_stats', JSON.stringify(this.playerStats));
        } catch(e) {
            console.log('localStorage nicht verfügbar - Stats nicht gespeichert');
        }
    }

    // ============== SOUND-SYSTEM ==============

    playSound(soundType) {
        if (!this.soundEnabled) return;

        const sounds = {
            'game_start': { freq: 440, duration: 200, type: 'sine' },
            'button_click': { freq: 220, duration: 100, type: 'square' },
            'player_win': { freq: [440, 554, 659], duration: 300, type: 'sine' },
            'dog_win': { freq: [220, 185, 147], duration: 400, type: 'sawtooth' },
            'tie': { freq: 330, duration: 250, type: 'triangle' },
            'countdown': { freq: 660, duration: 150, type: 'sine' }
        };

        const sound = sounds[soundType];
        if (!sound) return;

        try {
            // Web Audio API für Sound-Effekte
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();

            if (Array.isArray(sound.freq)) {
                // Mehrere Töne nacheinander (für Gewinn-Melodie)
                sound.freq.forEach((freq, index) => {
                    setTimeout(() => {
                        this.playTone(audioContext, freq, sound.duration / sound.freq.length, sound.type);
                    }, index * (sound.duration / sound.freq.length));
                });
            } else {
                this.playTone(audioContext, sound.freq, sound.duration, sound.type);
            }
        } catch(e) {
            console.log('Web Audio nicht verfügbar');
        }
    }

    playTone(audioContext, frequency, duration, type) {
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.frequency.value = frequency;
        oscillator.type = type;

        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration / 1000);

        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + duration / 1000);
    }

    // ============== ERWEITERTE CIRCLE FIGHT ==============

    setupCircleFight(container) {
        super.setupCircleFight(container);

        // Füge Statistik-Anzeige hinzu
        const statsDiv = document.createElement('div');
        statsDiv.style.cssText = `
            margin-top: 15px;
            font-size: 12px;
            color: #aaa;
            text-align: center;
        `;
        const stats = this.playerStats.circle_fight;
        statsDiv.innerHTML = `
            <strong>Deine Circle Fight Statistik:</strong><br>
            Siege: ${stats.won} | Niederlagen: ${stats.lost} | Unentschieden: ${stats.tie}
        `;
        container.appendChild(statsDiv);

        // Erweiterte Button-Interaktionen
        container.querySelectorAll('.choice-btn').forEach(btn => {
            btn.addEventListener('mousedown', () => {
                this.playSound('button_click');
                btn.style.transform = 'scale(0.95)';
            });

            btn.addEventListener('mouseup', () => {
                btn.style.transform = 'scale(1)';
            });
        });
    }

    playCircleFight(playerChoice) {
        const dogChoice = Math.floor(Math.random() * 4) + 1;
        const resultDiv = document.getElementById('circle-result');

        // Erweiterte Animation
        resultDiv.innerHTML = `
            <div style="animation: fadeIn 0.5s ease-in;">
                <p><strong>Du hast:</strong> <span style="color: #90ee90; font-size: 20px;">${playerChoice}</span></p>
                <p><strong>Hund hat:</strong> <span style="color: #ff6b6b; font-size: 20px;">${dogChoice}</span></p>
            </div>
        `;

        // CSS für Animation hinzufügen falls nicht vorhanden
        if (!document.getElementById('minigame-animations')) {
            const style = document.createElement('style');
            style.id = 'minigame-animations';
            style.textContent = `
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                @keyframes bounce {
                    0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
                    40% { transform: translateY(-10px); }
                    60% { transform: translateY(-5px); }
                }
                .winner-text { animation: bounce 1s ease-in-out; }
            `;
            document.head.appendChild(style);
        }

        const p = playerChoice - 1;
        const d = dogChoice - 1;

        let result;
        setTimeout(() => {
            if ((d + 1) % 4 === p) {
                result = 'LOST';
                resultDiv.innerHTML += '<p class="winner-text" style="color: #90ee90; font-weight: bold;">***Der Hund verliert den Kampf!***</p>';
            } else if ((p + 1) % 4 === d) {
                result = 'WON';
                resultDiv.innerHTML += '<p class="winner-text" style="color: #ff6b6b; font-weight: bold;">***Du verlierst den Kampf gegen den Hund!***</p>';
            } else {
                result = 'TIE';
                resultDiv.innerHTML += '<p class="winner-text" style="color: #ffd700; font-weight: bold;">***Unentschieden!***</p>';
            }

            setTimeout(() => {
                this.completeGame(result);
            }, 2000);
        }, 1000);
    }

    // ============== ERWEITERTE SUM FIGHT ==============

    setupSumFight(container, gameData) {
        super.setupSumFight(container, gameData);

        // Füge Tipp-System hinzu
        const tipDiv = document.createElement('div');
        tipDiv.id = 'sum-tips';
        tipDiv.style.cssText = `
            background: rgba(139, 69, 19, 0.2);
            border: 1px solid #cd853f;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
            font-size: 12px;
            color: #ffd700;
        `;

        container.appendChild(tipDiv);
        this.updateSumFightTips(gameData.stones, gameData.reach, 0);
    }

    updateSumFightTips(stones, reach, currentSum) {
        const tipDiv = document.getElementById('sum-tips');
        if (!tipDiv) return;

        const remaining = reach - currentSum;
        const validMoves = stones.filter(s => s <= remaining);
        const winningMoves = stones.filter(s => s === remaining);

        let tip = '';
        if (winningMoves.length > 0) {
            tip = `💡 <strong>Gewinnzug verfügbar:</strong> Wähle ${winningMoves.join(' oder ')} um zu gewinnen!`;
        } else if (validMoves.length === 0) {
            tip = `⚠️ <strong>Achtung:</strong> Alle Züge würden das Ziel überschreiten!`;
        } else {
            const safeMoves = validMoves.filter(s => {
                const newSum = currentSum + s;
                const newRemaining = reach - newSum;
                return stones.some(stone => stone !== s && stone <= newRemaining);
            });

            if (safeMoves.length > 0) {
                tip = `🎯 <strong>Sichere Züge:</strong> ${safeMoves.join(', ')} lassen dem Hund Optionen`;
            } else {
                tip = `⚡ <strong>Riskante Lage:</strong> Alle Züge könnten dem Hund einen Vorteil geben`;
            }
        }

        tipDiv.innerHTML = tip;
    }

    // ============== ERWEITERTE CLOSE FIGHT ==============

    setupCloseFight(container) {
        const secretNumber = Math.floor(Math.random() * 100) + 1;
        const dogChoice = Math.floor(Math.random() * 100) + 1;

        container.innerHTML = `
            <h2>🎯 Wer ist am nächsten dran?</h2>
            <div style="margin: 20px 0; font-size: 14px; line-height: 1.6;">
                <p><strong>Regeln:</strong></p>
                <p>Das System hat eine geheime Zahl zwischen 1 und 100 gewürfelt</p>
                <p>Beide wählen eine Zahl zwischen 1 und 100</p>
                <p>Wer näher an der geheimen Zahl liegt, gewinnt!</p>
            </div>
            
            <!-- NEUE: Schwierigkeitsgrad-Auswahl -->
            <div style="margin: 15px 0;">
                <p><strong>Schwierigkeitsgrad:</strong></p>
                <div style="display: flex; justify-content: center; gap: 10px; margin: 10px 0;">
                    <button class="difficulty-btn" data-range="10" style="
                        background: #2d5a27; color: #90ee90; padding: 8px 12px; 
                        border: 1px solid #90ee90; border-radius: 5px; cursor: pointer;">
                        Einfach (1-10)
                    </button>
                    <button class="difficulty-btn" data-range="50" style="
                        background: #5a4a27; color: #ffd700; padding: 8px 12px; 
                        border: 1px solid #ffd700; border-radius: 5px; cursor: pointer;">
                        Mittel (1-50)
                    </button>
                    <button class="difficulty-btn selected" data-range="100" style="
                        background: #5a2727; color: #ff6b6b; padding: 8px 12px; 
                        border: 2px solid #ff6b6b; border-radius: 5px; cursor: pointer;">
                        Schwer (1-100)
                    </button>
                </div>
            </div>
            
            <div id="close-input" style="margin: 30px 0;">
                <p style="font-size: 18px; margin-bottom: 20px;">Wähle deine Zahl (<span id="range-display">1-100</span>):</p>
                <input type="number" id="close-number" min="1" max="100" 
                       style="background: #8b4513; color: #f5deb3; border: 2px solid #cd853f; 
                              padding: 10px; font-size: 18px; border-radius: 8px; width: 120px; text-align: center;">
                <br><br>
                
                <!-- NEUE: Hinweis-System -->
                <div id="hint-system" style="margin: 15px 0; display: none;">
                    <p style="color: #ffd700; font-size: 14px;">
                        💡 <strong>Tipp:</strong> <span id="hint-text"></span>
                    </p>
                </div>
                
                <button id="close-submit" style="
                    background: #8b4513; color: #f5deb3; border: 2px solid #cd853f;
                    padding: 15px 30px; font-size: 16px; border-radius: 8px; cursor: pointer;">
                    Bestätigen
                </button>
                
                <button id="hint-button" style="
                    background: #4a4a4a; color: #f5deb3; border: 2px solid #888;
                    padding: 10px 20px; font-size: 14px; border-radius: 8px; cursor: pointer; margin-left: 10px;">
                    Hinweis (1x)
                </button>
            </div>
            <div id="close-result" style="font-size: 16px; min-height: 100px;"></div>
        `;

        let currentRange = 100;
        let secretInRange = secretNumber;
        let dogInRange = dogChoice;
        let hintUsed = false;

        // Schwierigkeitsgrad-Handler
        container.querySelectorAll('.difficulty-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                container.querySelectorAll('.difficulty-btn').forEach(b => {
                    b.classList.remove('selected');
                    b.style.borderWidth = '1px';
                });

                btn.classList.add('selected');
                btn.style.borderWidth = '2px';

                currentRange = parseInt(e.target.dataset.range);

                // Neue Zufallszahlen für gewählten Bereich
                secretInRange = Math.floor(Math.random() * currentRange) + 1;
                dogInRange = Math.floor(Math.random() * currentRange) + 1;

                // UI aktualisieren
                document.getElementById('range-display').textContent = `1-${currentRange}`;
                document.getElementById('close-number').max = currentRange;
                document.getElementById('close-number').value = '';

                this.playSound('button_click');
            });
        });

        // Hinweis-System
        document.getElementById('hint-button').addEventListener('click', () => {
            if (hintUsed) return;

            hintUsed = true;
            const hintDiv = document.getElementById('hint-system');
            const hintText = document.getElementById('hint-text');

            // Bereich-Hinweis basierend auf geheimer Zahl
            let hintMessage;
            const quarter = Math.ceil(currentRange / 4);

            if (secretInRange <= quarter) {
                hintMessage = `Die geheime Zahl ist im unteren Viertel (1-${quarter})`;
            } else if (secretInRange <= quarter * 2) {
                hintMessage = `Die geheime Zahl ist im zweiten Viertel (${quarter + 1}-${quarter * 2})`;
            } else if (secretInRange <= quarter * 3) {
                hintMessage = `Die geheime Zahl ist im dritten Viertel (${quarter * 2 + 1}-${quarter * 3})`;
            } else {
                hintMessage = `Die geheime Zahl ist im oberen Viertel (${quarter * 3 + 1}-${currentRange})`;
            }

            hintText.textContent = hintMessage;
            hintDiv.style.display = 'block';

            // Button deaktivieren
            document.getElementById('hint-button').style.opacity = '0.5';
            document.getElementById('hint-button').style.cursor = 'not-allowed';
            document.getElementById('hint-button').textContent = 'Hinweis verwendet';

            this.playSound('button_click');
        });

        const submitBtn = document.getElementById('close-submit');
        const numberInput = document.getElementById('close-number');

        const playGame = () => {
            const playerChoice = parseInt(numberInput.value);

            if (isNaN(playerChoice) || playerChoice < 1 || playerChoice > currentRange) {
                alert(`Bitte eine gültige Zahl zwischen 1 und ${currentRange} eingeben!`);
                return;
            }

            this.playCloseFightEnhanced(playerChoice, dogInRange, secretInRange, hintUsed);
        };

        submitBtn.addEventListener('click', playGame);
        numberInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                playGame();
            }
        });

        setTimeout(() => numberInput.focus(), 100);
    }

    playCloseFightEnhanced(playerChoice, dogChoice, secretNumber, hintUsed) {
        const resultDiv = document.getElementById('close-result');

        // Erweiterte Anzeige mit Visualisierung
        resultDiv.innerHTML = `
            <div style="animation: fadeIn 0.8s ease-in;">
                <div style="display: flex; justify-content: space-around; margin: 20px 0;">
                    <div style="text-align: center;">
                        <p style="color: #90ee90;"><strong>Deine Wahl</strong></p>
                        <div style="background: #2d5a27; padding: 15px; border-radius: 50%; width: 60px; height: 60px; 
                                    display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold;">
                            ${playerChoice}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <p style="color: #ffd700;"><strong>Geheime Zahl</strong></p>
                        <div style="background: #5a4a27; padding: 15px; border-radius: 50%; width: 60px; height: 60px; 
                                    display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold;">
                            ${secretNumber}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <p style="color: #ff6b6b;"><strong>Hund wählte</strong></p>
                        <div style="background: #5a2727; padding: 15px; border-radius: 50%; width: 60px; height: 60px; 
                                    display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold;">
                            ${dogChoice}
                        </div>
                    </div>
                </div>
            </div>
        `;

        setTimeout(() => {
            if (playerChoice === dogChoice) {
                resultDiv.innerHTML += '<p class="winner-text" style="color: #ffd700; font-weight: bold;">***Gleiche Zahl - Unentschieden!***</p>';
                setTimeout(() => this.completeGame('TIE'), 2000);
                return;
            }

            const playerDistance = Math.abs(secretNumber - playerChoice);
            const dogDistance = Math.abs(secretNumber - dogChoice);

            // Bonus für Hinweis-Nutzung (leichte Erschwernis)
            const playerPenalty = hintUsed ? 0.5 : 0;
            const adjustedPlayerDistance = playerDistance + playerPenalty;

            if (adjustedPlayerDistance === dogDistance) {
                resultDiv.innerHTML += '<p class="winner-text" style="color: #ffd700; font-weight: bold;">***Gleicher Abstand - Unentschieden!***</p>';
                if (hintUsed) {
                    resultDiv.innerHTML += '<p style="color: #aaa; font-size: 12px;">(Hinweis-Penalty: +0.5 Distanz)</p>';
                }
                setTimeout(() => this.completeGame('TIE'), 2500);
            } else if (adjustedPlayerDistance > dogDistance) {
                resultDiv.innerHTML += `<p class="winner-text" style="color: #ff6b6b; font-weight: bold;">***Der Hund ist näher dran (Abstand ${dogDistance}). Dein Abstand ist ${playerDistance}${hintUsed ? ' (+0.5 Penalty)' : ''}. Der Hund gewinnt!***</p>`;
                setTimeout(() => this.completeGame('WON'), 2500);
            } else {
                resultDiv.innerHTML += `<p class="winner-text" style="color: #90ee90; font-weight: bold;">***Du bist näher dran (Abstand ${playerDistance}${hintUsed ? ', mit Penalty trotzdem' : ''}). Abstand des Hundes ist ${dogDistance}. Du gewinnst!***</p>`;
                setTimeout(() => this.completeGame('LOST'), 2500);
            }
        }, 1500);
    }

    // ============== STATISTIKEN ANZEIGEN ==============

    showStats() {
        const overlay = document.getElementById('minigame-overlay');
        const container = document.getElementById('minigame-container');

        overlay.style.display = 'flex';

        let totalGames = 0;
        let totalWins = 0;

        const statsHtml = Object.entries(this.playerStats).map(([game, stats]) => {
            const total = stats.won + stats.lost + stats.tie;
            totalGames += total;
            totalWins += stats.won;

            const winRate = total > 0 ? Math.round((stats.won / total) * 100) : 0;

            return `
                <div style="background: rgba(139, 69, 19, 0.3); padding: 15px; margin: 10px 0; border-radius: 8px;">
                    <h3 style="color: #ffd700; margin-bottom: 10px;">${game.replace('_', ' ').toUpperCase()}</h3>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Siege: <strong style="color: #90ee90;">${stats.won}</strong></span>
                        <span>Niederlagen: <strong style="color: #ff6b6b;">${stats.lost}</strong></span>
                        <span>Unentschieden: <strong style="color: #ffd700;">${stats.tie}</strong></span>
                    </div>
                    <div style="margin-top: 5px; text-align: center;">
                        <strong>Siegrate: ${winRate}%</strong>
                    </div>
                </div>
            `;
        }).join('');

        const overallWinRate = totalGames > 0 ? Math.round((totalWins / totalGames) * 100) : 0;

        container.innerHTML = `
            <h2>📊 Deine Mini-Game Statistiken</h2>
            <div style="text-align: center; margin: 20px 0; font-size: 18px;">
                <strong>Gesamt-Siegrate: ${overallWinRate}% (${totalWins}/${totalGames})</strong>
            </div>
            ${statsHtml}
            <div style="text-align: center; margin-top: 30px;">
                <button onclick="miniGames.hideGame()" style="
                    background: #8b4513; color: #f5deb3; border: 2px solid #cd853f;
                    padding: 15px 30px; font-size: 16px; border-radius: 8px; cursor: pointer;">
                    Schließen
                </button>
            </div>
        `;
    }

    // ============== SETTINGS PANEL ==============

    showSettings() {
        const overlay = document.getElementById('minigame-overlay');
        const container = document.getElementById('minigame-container');

        overlay.style.display = 'flex';

        container.innerHTML = `
            <h2>⚙️ Mini-Game Einstellungen</h2>
            <div style="text-align: left; margin: 20px 0;">
                <div style="margin: 15px 0;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="sound-toggle" ${this.soundEnabled ? 'checked' : ''} 
                               style="margin-right: 10px;">
                        <span>🔊 Sound-Effekte aktivieren</span>
                    </label>
                </div>
                
                <div style="margin: 15px 0;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="animations-toggle" ${this.animationsEnabled ? 'checked' : ''} 
                               style="margin-right: 10px;">
                        <span>✨ Animationen aktivieren</span>
                    </label>
                </div>
                
                <div style="margin: 20px 0; padding: 15px; background: rgba(139, 69, 19, 0.3); border-radius: 8px;">
                    <h4>🎮 Tastatur-Shortcuts:</h4>
                    <ul style="list-style: none; padding: 0;">
                        <li><strong>1-4:</strong> Circle Fight Auswahl</li>
                        <li><strong>1-5:</strong> Odd/Even Fight Auswahl</li>
                        <li><strong>Enter:</strong> Bestätigen</li>
                        <li><strong>Esc:</strong> Spiel beenden</li>
                    </ul>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <button onclick="miniGames.applySettings()" style="
                    background: #2d5a27; color: #90ee90; border: 2px solid #90ee90;
                    padding: 15px 30px; font-size: 16px; border-radius: 8px; cursor: pointer; margin-right: 10px;">
                    Anwenden
                </button>
                <button onclick="miniGames.hideGame()" style="
                    background: #8b4513; color: #f5deb3; border: 2px solid #cd853f;
                    padding: 15px 30px; font-size: 16px; border-radius: 8px; cursor: pointer;">
                    Schließen
                </button>
            </div>
        `;

        // Event-Listener für Checkboxen
        document.getElementById('sound-toggle').addEventListener('change', (e) => {
            if (e.target.checked) {
                this.playSound('button_click');
            }
        });
    }

    applySettings() {
        this.soundEnabled = document.getElementById('sound-toggle').checked;
        this.animationsEnabled = document.getElementById('animations-toggle').checked;

        // Speichere Einstellungen
        try {
            localStorage.setItem('adventure_minigame_settings', JSON.stringify({
                sound: this.soundEnabled,
                animations: this.animationsEnabled
            }));
        } catch(e) {
            console.log('Settings konnten nicht gespeichert werden');
        }

        this.playSound('button_click');
        this.hideGame();
    }

    // Lade Einstellungen beim Start
    loadSettings() {
        try {
            const settings = JSON.parse(localStorage.getItem('adventure_minigame_settings') || '{}');
            const stats = JSON.parse(localStorage.getItem('adventure_minigame_stats') || '{}');

            this.soundEnabled = settings.sound !== false; // Default: true
            this.animationsEnabled = settings.animations !== false; // Default: true

            if (stats.circle_fight) {
                this.playerStats = stats;
            }
        } catch(e) {
            console.log('Einstellungen konnten nicht geladen werden');
        }
    }
}

// ============== GLOBALE ERWEITERUNGEN ==============

// Ersetze die globale miniGames Instanz
document.addEventListener('DOMContentLoaded', function() {
    if (typeof EnhancedMiniGames !== 'undefined') {
        miniGames = new EnhancedMiniGames();
        miniGames.loadSettings();

        // Füge Tastatur-Shortcuts hinzu
        document.addEventListener('keydown', function(e) {
            if (!miniGames.currentGame) return;

            // ESC zum Beenden
            if (e.key === 'Escape') {
                miniGames.hideGame();
                return;
            }

            // Spiel-spezifische Shortcuts
            if (miniGames.currentGame === 'circle_fight') {
                if (['1', '2', '3', '4'].includes(e.key)) {
                    const btn = document.querySelector(`[data-choice="${e.key}"]`);
                    if (btn && !btn.disabled) {
                        btn.click();
                    }
                }
            } else if (miniGames.currentGame === 'odd_even_fight') {
                if (['1', '2', '3', '4', '5'].includes(e.key)) {
                    const btn = document.querySelector(`[data-choice="${e.key}"]`);
                    if (btn && !btn.disabled) {
                        btn.click();
                    }
                }
            }
        });

        console.log('✅ Enhanced Mini-Games geladen');
    }
});

// Globale Funktionen für HTML-Buttons
window.showMiniGameStats = function() {
    if (miniGames && miniGames.showStats) {
        miniGames.showStats();
    }
};

window.showMiniGameSettings = function() {
    if (miniGames && miniGames.showSettings) {
        miniGames.showSettings();
    }
};
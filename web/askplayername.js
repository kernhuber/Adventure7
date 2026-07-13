/**
 * askPlayerName() - Standalone JavaScript Funktion
 * Fragt den Spielernamen über einen Overlay mit Milchglas-Effekt ab
 *
 * Usage:
 * <script src="askPlayerName.js"></script>
 * <script>
 *   askPlayerName().then(name => console.log(name));
 * </script>
 *
 * @returns {Promise<string>} Der eingegebene Spielername
 */
function askPlayerName() {
    return new Promise((resolve) => {
        // CSS-Styles dynamisch hinzufügen
        const styleId = 'player-name-overlay-styles';
        if (!document.getElementById(styleId)) {
            const style = document.createElement('style');
            style.id = styleId;
            style.textContent = `
                .player-name-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.3);
                    backdrop-filter: blur(8px);
                    -webkit-backdrop-filter: blur(8px);
                    z-index: 10000;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    opacity: 1;
                    transition: opacity 1s ease-out;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                }

                .player-name-overlay.fade-out {
                    opacity: 0;
                }

                .player-name-modal {
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(20px);
                    -webkit-backdrop-filter: blur(20px);
                    border-radius: 20px;
                    padding: 40px;
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
                    text-align: center;
                    max-width: 400px;
                    width: 90%;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    transform: scale(1);
                    transition: transform 0.15s ease;
                }

                .player-name-title {
                    font-size: 24px;
                    color: #333;
                    margin: 0 0 30px 0;
                    font-weight: 300;
                    line-height: 1.4;
                }

                .player-name-input {
                    width: 100%;
                    padding: 15px;
                    font-size: 18px;
                    border: 2px solid #e0e0e0;
                    border-radius: 10px;
                    background: rgba(255, 255, 255, 0.8);
                    backdrop-filter: blur(10px);
                    -webkit-backdrop-filter: blur(10px);
                    box-sizing: border-box;
                    transition: border-color 0.3s ease, box-shadow 0.3s ease;
                    outline: none;
                    font-family: inherit;
                }

                .player-name-input:focus {
                    border-color: #4ecdc4;
                    box-shadow: 0 0 0 3px rgba(78, 205, 196, 0.2);
                }

                .player-name-hint {
                    font-size: 14px;
                    color: #666;
                    margin: 15px 0 0 0;
                    font-style: italic;
                }
            `;
            document.head.appendChild(style);
        }

        // Overlay-Element erstellen
        const overlay = document.createElement('div');
        overlay.className = 'player-name-overlay';

        // Modal-Container erstellen
        const modal = document.createElement('div');
        modal.className = 'player-name-modal';

        // Titel erstellen
        const title = document.createElement('div');
        title.className = 'player-name-title';
        title.textContent = 'Wie möchtest Du in diesem Spiel heissen?';

        // Eingabefeld erstellen
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'player-name-input';
        input.placeholder = 'Dein Spielername...';
        input.maxLength = 20;
        input.autocomplete = 'off';

        // Hinweis erstellen
        const hint = document.createElement('div');
        hint.className = 'player-name-hint';
        hint.textContent = 'Drücke Enter, um zu bestätigen';

        // Elemente zusammenfügen
        modal.appendChild(title);
        modal.appendChild(input);
        modal.appendChild(hint);
        overlay.appendChild(modal);

        // Start-Screen-Musik (game_start.mp3); wird beim Anzeigen gestartet und beim
        // Abschicken des Namens wieder gestoppt, damit sie nicht ins Spiel hineinläuft.
        let startMusic = null;
        const stopStartMusic = () => { if (startMusic) { try { startMusic.pause(); } catch (e) {} } };

        // Cleanup-Funktion
        const cleanup = () => {
            if (overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
            // Optional: CSS-Styles entfernen, wenn nicht mehr benötigt
            // const style = document.getElementById(styleId);
            // if (style) style.parentNode.removeChild(style);
        };

        // Event-Listener für Enter-Taste
        const handleKeyDown = (event) => {
            if (event.key === 'Enter') {
                const playerName = input.value.trim();

                // Nur fortfahren, wenn ein Name eingegeben wurde
                if (playerName) {
                    // Event-Listener entfernen
                    input.removeEventListener('keydown', handleKeyDown);
                    overlay.removeEventListener('click', handleOverlayClick);

                    // Fade-Out-Animation starten
                    overlay.classList.add('fade-out');
                    stopStartMusic();

                    // Nach 1 Sekunde Overlay entfernen und Wert zurückgeben
                    setTimeout(() => {
                        cleanup();
                        resolve(playerName);
                    }, 1000);
                }
            }
        };

        // Event-Listener für Overlay-Klicks (Animation bei Außenklick)
        const handleOverlayClick = (event) => {
            if (event.target === overlay) {
                // Leichte Shake-Animation zur Aufmerksamkeit
                modal.style.transform = 'scale(1.05)';
                setTimeout(() => {
                    modal.style.transform = 'scale(1)';
                }, 150);
            }
        };

        // Event-Listener hinzufügen
        input.addEventListener('keydown', handleKeyDown);
        overlay.addEventListener('click', handleOverlayClick);

        // Overlay zum DOM hinzufügen
        document.body.appendChild(overlay);

        // Start-Screen-Musik abspielen. Der Welcome-Overlay davor wird per Klick geschlossen,
        // es gab also i.d.R. schon eine User-Geste -> Autoplay erlaubt; eine Blockade wird
        // still abgefangen.
        try {
            startMusic = new Audio('game_start.mp3');
            startMusic.volume = 0.6;
            startMusic.loop = true;   // solange der Namens-Screen offen ist, in Schleife
            startMusic.play().catch(() => {});
        } catch (e) {
            console.warn('Start-Musik nicht abspielbar:', e);
        }

        // Eingabefeld nach kurzer Verzögerung fokussieren
        setTimeout(() => {
            input.focus();
        }, 100);

        // Notfall-Cleanup bei Problemen
        setTimeout(() => {
            if (document.body.contains(overlay)) {
                console.warn('askPlayerName: Overlay wurde nach 5 Minuten automatisch entfernt');
                cleanup();
                resolve(''); // Leeren String zurückgeben
            }
        }, 300000); // 5 Minuten Timeout
    });
}

// Globale Verfügbarkeit sicherstellen
if (typeof window !== 'undefined') {
    window.askPlayerName = askPlayerName;
}

// Export für Module (falls benötigt)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = askPlayerName;
}
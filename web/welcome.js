// --- Start-Screen-Musik (game_start.mp3) ---------------------------------------------
// Gemeinsamer, kleiner Audio-Controller für den Startablauf: Der Welcome-Overlay startet
// die Musik beim ersten Klick (echte User-Geste -> Autoplay erlaubt), die Namenseingabe
// (askplayername.js) blendet sie beim Abschicken sanft aus. So läuft sie sofort, sobald
// der Spieler auf "Weiter" klickt - noch bevor der Namens-Screen erscheint.
window.__gameStartMusic = window.__gameStartMusic || null;

function startGameStartMusic() {
    if (!window.__gameStartMusic) {
        try {
            const m = new Audio('game_start.mp3');
            m.volume = 1.0;   // volle Lautstärke (war zu leise)
            m.loop = true;
            window.__gameStartMusic = m;
        } catch (e) { return; }
    }
    try { window.__gameStartMusic.play().catch(() => {}); } catch (e) {}
}

function stopGameStartMusic() {
    const m = window.__gameStartMusic;
    if (!m) return;
    // Sanft ausblenden, dann pausieren (statt hartem Abbruch beim Return).
    if (m._fade) clearInterval(m._fade);
    m._fade = setInterval(() => {
        const v = (m.volume || 0) - 0.05;
        if (v <= 0) {
            clearInterval(m._fade);
            m._fade = null;
            try { m.pause(); m.currentTime = 0; } catch (e) {}
            m.volume = 1.0;   // für einen evtl. erneuten Start zurücksetzen
        } else {
            m.volume = v;
        }
    }, 70);
}

function showWelcome(htmlContent = "Willkommen!<br><br>Klicken Sie, um fortzufahren.") {
    // Overlay-Element erstellen
    const overlay = document.createElement('div');
    overlay.id = 'welcomeOverlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: 9999;
        background: linear-gradient(to bottom,
            #1a237e 0%,           /* Dunkelblau oben */
            #42a5f5 50%,          /* Hellblau zur Mitte */
            #ffffff 55%,          /* Weiß nach wenigen Zeilen */
            #ffffff 60%,          /* Wenige Zeilen weiß bleiben */
            #fff9c4 75%,          /* Hellgelb bis 3/4 */
            #bf8f00 100%          /* Ocker bis unten */
        );
        display: flex;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        opacity: 1;
        transition: opacity 1s ease-out;
    `;

    // Durchsichtiges Textfeld erstellen
    const textContainer = document.createElement('div');
    textContainer.style.cssText = `
        background-color: rgba(255, 255, 255, 0.8);
        border: 2px solid rgba(0, 0, 0, 0.2);
        border-radius: 10px;
        padding: 30px;
        max-width: 800px;
        min-height: 600px
        max-height: 700px;
        overflow-y: auto;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        font-family: 'Courier New', monospace;
        font-size: 14pt;
        line-height: 1.6;
        color: #333;
        text-align: center;
        backdrop-filter: blur(5px);
    `;

    // HTML-Content einsetzen
    textContainer.innerHTML = htmlContent;

    // Textcontainer zum Overlay hinzufügen
    overlay.appendChild(textContainer);

    // Overlay zum Body hinzufügen
    document.body.appendChild(overlay);

    // Musik beim ERSTEN User-Input (Klick/Taste irgendwo) starten - das ist die früheste von
    // der Autoplay-Policy erlaubte Stelle und funktioniert unabhängig davon, ob der Spieler
    // zuerst den Welcome-Screen wegklickt oder direkt in die Namenseingabe tippt. Danach läuft
    // sie durch (loop) bis zum Spielende (game_over.js stoppt sie dann).
    const firstGestureStart = () => {
        document.removeEventListener('pointerdown', firstGestureStart);
        document.removeEventListener('keydown', firstGestureStart);
        startGameStartMusic();
    };
    document.addEventListener('pointerdown', firstGestureStart);
    document.addEventListener('keydown', firstGestureStart);

    // Click-Event für das Ausblenden
    function closeOverlay() {
        overlay.style.opacity = '0';

        // Nach der Transition das Element entfernen
        setTimeout(() => {
            if (overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
        }, 1000);

        // Event Listener entfernen
        overlay.removeEventListener('click', closeOverlay);
    }

    // Event Listener hinzufügen
    overlay.addEventListener('click', closeOverlay);

    // Escape-Taste zum Schließen
    function handleKeyPress(event) {
        if (event.key === 'Escape') {
            closeOverlay();
            document.removeEventListener('keydown', handleKeyPress);
        }
    }
    document.addEventListener('keydown', handleKeyPress);

    // Optional: Nach bestimmter Zeit automatisch schließen (auskommentiert)
    // setTimeout(closeOverlay, 5000);
}

// Export für Module (optional)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { showWelcome };
}
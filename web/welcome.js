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

// options.choices = true: Startauswahl (Altes Spiel laden / selbst spielen / Agent spielen lassen) statt "Klick zum Weiter".
function showWelcome(htmlContent = "Willkommen!<br><br>Klicken Sie, um fortzufahren.", options = {}) {
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
    if (options.choices) {
        overlay.style.cursor = 'default';
        renderStartChoices(textContainer, () => closeOverlay());
    }

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
    if (!options.choices) overlay.addEventListener('click', closeOverlay);   // mit Auswahl schließen nur die Knöpfe

    // Escape-Taste zum Schließen
    function handleKeyPress(event) {
        if (event.key === 'Escape' && !options.choices) {
            closeOverlay();
            document.removeEventListener('keydown', handleKeyPress);
        }
    }
    document.addEventListener('keydown', handleKeyPress);

    // Optional: Nach bestimmter Zeit automatisch schließen (auskommentiert)
    // setTimeout(closeOverlay, 5000);
}

// --- Startauswahl im Welcome-Screen ------------------------------------------------------
// Drei Wege: (1) selbst spielen -> die WebSocket-Verbindung wird erst JETZT aufgebaut (backend.connect(), der
// Server fragt dann den Namen), (2) Agent spielen lassen und (3) einen alten Spielstand laden: beides lädt die
// Seite mit einem URL-Parameter neu (?mode=agent bzw. ?load=<name> / ?mode=agent&save=<name>), weil der
// Server die Spielart beim Verbinden aus der URL liest.
function renderStartChoices(container, onSelf) {
    const box = document.createElement('div');
    box.style.cssText = 'margin-top:22px;display:flex;flex-direction:column;gap:12px;align-items:stretch';
    container.appendChild(box);

    const btnStyle = 'font:bold 15pt "Courier New",monospace;padding:12px 18px;cursor:pointer;border-radius:8px;'
        + 'border:2px solid #8a6d1f;background:#fff3c4;color:#333;';
    const mkBtn = (text, onclick, small) => {
        const b = document.createElement('button');
        b.textContent = text;
        b.style.cssText = btnStyle + (small ? 'font-size:12pt;padding:6px 12px;' : '');
        b.onmouseenter = () => { b.style.background = '#ffe48a'; };
        b.onmouseleave = () => { b.style.background = '#fff3c4'; };
        b.onclick = (e) => { e.stopPropagation(); onclick(); };
        return b;
    };
    const go = (query) => { window.location.href = window.location.pathname + query; };

    function showMain() {
        box.innerHTML = '';
        box.appendChild(mkBtn('🎮 Neues Spiel – selbst spielen', () => {
            if (typeof backend !== 'undefined' && backend) backend.connect();
            onSelf();
        }));
        box.appendChild(mkBtn('🤖 Neues Spiel – Agent spielen lassen', () => go('?mode=agent')));
        box.appendChild(mkBtn('📂 Altes Spiel laden', showSlots));
    }

    function showSlots() {
        box.innerHTML = '<div style="font-size:12pt">Lade Spielstände …</div>';
        fetch('slots.json', { cache: 'no-store' }).then(r => r.json()).then(slots => {
            box.innerHTML = '';
            const hinweis = document.createElement('div');
            hinweis.style.cssText = 'font-size:11pt;text-align:left';
            hinweis.textContent = '🤖 = enthält das Gedächtnis eines Agenten (Notizbuch, Notiz an sich selbst). '
                + 'Ohne 🤖 startet der Agent ohne Gedächtnis.';
            box.appendChild(hinweis);
            const liste = document.createElement('div');
            liste.style.cssText = 'max-height:320px;overflow-y:auto;text-align:left';
            if (!slots.length) liste.textContent = 'Keine Spielstände vorhanden.';
            slots.forEach(s => {
                const zeile = document.createElement('div');
                zeile.style.cssText = 'margin:6px 0;padding:6px;border-bottom:1px solid rgba(0,0,0,0.15)';
                const name = document.createElement('div');
                name.style.cssText = 'font-size:12pt;font-weight:bold';
                name.textContent = (s.agent ? '🤖 ' : '') + s.name;
                zeile.appendChild(name);
                if (s.agent && s.notiz) {
                    const n = document.createElement('div');
                    n.style.cssText = 'font-size:10pt;color:#7a4b00';
                    n.textContent = '📝 ' + s.notiz;
                    zeile.appendChild(n);
                }
                zeile.appendChild(mkBtn('👤 selbst spielen', () => go('?load=' + encodeURIComponent(s.name)), true));
                zeile.appendChild(document.createTextNode(' '));
                zeile.appendChild(mkBtn('🤖 Agent spielen lassen', () => go('?mode=agent&save=' + encodeURIComponent(s.name)), true));
                liste.appendChild(zeile);
            });
            box.appendChild(liste);
            box.appendChild(mkBtn('← Zurück', showMain, true));
        }).catch(() => {
            box.innerHTML = '<div style="color:#a00">Spielstände konnten nicht geladen werden.</div>';
            box.appendChild(mkBtn('← Zurück', showMain, true));
        });
    }

    showMain();
}

// Export für Module (optional)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { showWelcome };
}
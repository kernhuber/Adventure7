// explosion_message.js
// Eindeutiger Name für das Overlay
const EXPLOSION_OVERLAY_ID = 'explosionMessageOverlay';
let blinkInterval = null;

/**
 * Zeigt eine Explosions-Nachricht mit rhythmischem Blinken an
 * @param {string} text - HTML-Text der angezeigt werden soll
 */
window.showExplosionMessage = function(text) {
    let overlay = document.getElementById(EXPLOSION_OVERLAY_ID);

    // Overlay erstellen falls es noch nicht existiert
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = EXPLOSION_OVERLAY_ID;

        // Overlay-Styling
        overlay.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 10000;
            background-color: #000033;
            border: 5px solid #ff0000;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
            min-width: 300px;
            max-width: 500px;
        `;

        // Text-Container erstellen
        const textContainer = document.createElement('div');
        textContainer.id = EXPLOSION_OVERLAY_ID + '_text';
        textContainer.style.cssText = `
            color: #ffff00;
            font-weight: bold;
            font-size: 18px;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
        `;

        // Bild-Element erstellen
        const image = document.createElement('img');
        image.src = 'sprengladung.png';
        image.alt = 'Sprengladung';
        image.style.cssText = `
            //max-width: 200px;
            //max-height: 200px;
            min-width: 290px;
            max-width: 290px;
            display: block;
            margin: 0 auto;
        `;

        // Elemente zum Overlay hinzufügen
        overlay.appendChild(textContainer);
        overlay.appendChild(image);


        // Overlay zum Body hinzufügen
        document.body.appendChild(overlay);

        // Blink-Animation starten
        startBlinkAnimation(overlay);
    }

    // Text aktualisieren (auch wenn Overlay bereits existiert)
    const textContainer = document.getElementById(EXPLOSION_OVERLAY_ID + '_text');
    if (textContainer) {
        textContainer.innerHTML = text;
    }
}

/**
 * Versteckt die Explosions-Nachricht und stoppt die Animation
 */
window.hideExplosionMessage = function() {
    const overlay = document.getElementById(EXPLOSION_OVERLAY_ID);
    if (overlay) {
        // Blink-Animation stoppen
        if (blinkInterval) {
            clearInterval(blinkInterval);
            blinkInterval = null;
        }

        // Overlay entfernen
        overlay.remove();
    }
}

/**
 * Startet die Blink-Animation für das Overlay
 * @param {HTMLElement} element - Das Element das blinken soll
 */
function startBlinkAnimation(element) {
    // Vorherige Animation stoppen falls vorhanden
    if (blinkInterval) {
        clearInterval(blinkInterval);
    }

    let isVisible = true;
    let startTime = Date.now();

    blinkInterval = setInterval(() => {
        const elapsed = Date.now() - startTime;
        const cycleTime = elapsed % 2200; // 2,2 Sekunden pro Zyklus (1s ein, 0,1s pause, 1s aus, 0,1s pause)

        if (cycleTime < 1000) {
            // Erste Sekunde: Einblenden (0 -> 1)
            const progress = cycleTime / 1000;
            element.style.opacity = progress.toString();
        } else if (cycleTime < 1100) {
            // 100ms Pause: Vollständig sichtbar
            element.style.opacity = '1';
        } else if (cycleTime < 2100) {
            // Eine Sekunde: Ausblenden (1 -> 0)
            const progress = (cycleTime - 1100) / 1000;
            element.style.opacity = (1 - progress).toString();
        } else {
            // 100ms Pause: Vollständig unsichtbar
            element.style.opacity = '0';
        }
    }, 16); // ~60 FPS für flüssige Animation


}

// Bestätigung dass die Datei geladen wurde
console.log('explosion_message.js erfolgreich geladen');
// text_popup.js
// Ein einfaches, schließbares Text-Popup (read-only) für längere Lesetexte wie
// das Betriebshandbuch. Wird vom Server über die Nachricht {type:"manual_popup",
// title, content} ausgelöst (siehe websockets.js / command_engine.py).
//
// Der Inhalt ist als monospace formatierter Text (ASCII-Layout) gedacht und wird
// daher in einem <pre> dargestellt.

const TEXT_POPUP_ID = 'textPopupOverlay';

/**
 * Zeigt ein modales Text-Popup mit Titel und (monospace) Inhalt.
 * @param {string} title   - Überschrift des Popups
 * @param {string} content - Anzuzeigender Text (Zeilenumbrüche bleiben erhalten)
 */
window.showTextPopup = function(title, content) {
    // Falls schon eines offen ist: entfernen, damit wir nicht stapeln.
    hideTextPopup();

    const overlay = document.createElement('div');
    overlay.id = TEXT_POPUP_ID;
    overlay.style.cssText = `
        position: fixed;
        inset: 0;
        z-index: 10001;
        background: rgba(0, 0, 0, 0.6);
        display: flex;
        align-items: center;
        justify-content: center;
    `;

    const box = document.createElement('div');
    box.style.cssText = `
        background: #f4ecd8;
        color: #2b2b2b;
        border: 3px solid #8a6d3b;
        border-radius: 8px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6);
        max-width: 640px;
        width: 90%;
        max-height: 85vh;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    `;

    const header = document.createElement('div');
    header.style.cssText = `
        background: #8a6d3b;
        color: #fff;
        font-weight: bold;
        font-size: 18px;
        padding: 10px 16px;
    `;
    header.textContent = title || 'Dokument';

    const body = document.createElement('pre');
    body.style.cssText = `
        margin: 0;
        padding: 18px;
        overflow: auto;
        font-family: 'Courier New', monospace;
        font-size: 14px;
        line-height: 1.45;
        white-space: pre-wrap;
        word-break: break-word;
    `;
    body.textContent = content || '';

    const footer = document.createElement('div');
    footer.style.cssText = `
        padding: 10px 16px;
        text-align: right;
        border-top: 1px solid #d8c9a3;
    `;

    const closeBtn = document.createElement('button');
    closeBtn.textContent = 'Schließen';
    closeBtn.style.cssText = `
        background: #8a6d3b;
        color: #fff;
        border: none;
        border-radius: 5px;
        padding: 8px 18px;
        font-size: 14px;
        cursor: pointer;
    `;
    closeBtn.addEventListener('click', hideTextPopup);
    footer.appendChild(closeBtn);

    box.appendChild(header);
    box.appendChild(body);
    box.appendChild(footer);
    overlay.appendChild(box);

    // Klick auf den Hintergrund (nicht auf die Box) schließt ebenfalls.
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) hideTextPopup();
    });

    document.body.appendChild(overlay);
};

/** Schließt das Text-Popup, falls offen. */
window.hideTextPopup = function() {
    const existing = document.getElementById(TEXT_POPUP_ID);
    if (existing) existing.remove();
};

console.log('text_popup.js erfolgreich geladen');

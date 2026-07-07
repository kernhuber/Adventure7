// spielleitung_modal.js — modales Fenster, das erscheint, wenn eine Eingabe wegen
// eines Gemini-/LLM-Fehlers nicht ausgeführt werden konnte ("Systemfehler").
// Bewusst als zentriertes Vollbild-Overlay (NICHT oben rechts bei Hund/Zombie),
// damit der Spieler die Grafik nicht für eine Spielfigur hält.
const SPIELLEITUNG_OVERLAY_ID = 'spielleitungOverlay';

function showSpielleitungModal() {
    hideSpielleitungModal();

    if (!document.getElementById('spielleitungModalStyle')) {
        const st = document.createElement('style');
        st.id = 'spielleitungModalStyle';
        st.textContent =
            '@keyframes spielleitungFadeIn{from{opacity:0}to{opacity:1}}' +
            // Roter Glow-Effekt: pulsierender roter Schein um das Fenster.
            '@keyframes spielleitungGlow{' +
            '0%,100%{box-shadow:0 0 26px 6px rgba(255,0,0,0.55)}' +
            '50%{box-shadow:0 0 60px 20px rgba(255,0,0,0.95)}}';
        document.head.appendChild(st);
    }

    const overlay = document.createElement('div');
    overlay.id = SPIELLEITUNG_OVERLAY_ID;
    overlay.style.cssText = `
        position: fixed; inset: 0; z-index: 12000;
        display: flex; align-items: center; justify-content: center;
        background: radial-gradient(circle, rgba(120,0,0,0.45) 0%, rgba(0,0,0,0.85) 80%);
        cursor: pointer; animation: spielleitungFadeIn 0.15s ease-out;
    `;

    const box = document.createElement('div');
    box.style.cssText = `
        max-width: 420px; margin: 20px; padding: 28px 34px; text-align: center;
        background: #1a0000; border: 3px solid #ff2222; border-radius: 14px;
        animation: spielleitungGlow 1.4s ease-in-out infinite;
    `;

    const img = document.createElement('img');
    img.src = 'gemini_large.png';
    img.width = 256;
    img.height = 256;
    img.alt = 'Spielleitung';
    img.style.cssText = 'width:320px; height:256px; border-radius:10px; display:block; margin:0 auto 18px;';
    box.appendChild(img);

    const text = document.createElement('div');
    text.style.cssText = 'color:#ffd0d0; font-size:1.15em; line-height:1.45; text-shadow:1px 1px 4px #000;';
    text.textContent = 'Wir sind die Spielleitung - es gab ein Problem. Bitte versuche es nochmal';
    box.appendChild(text);

    const hint = document.createElement('div');
    hint.style.cssText = 'color:#aa6666; font-size:0.8em; margin-top:16px;';
    hint.textContent = '(Klicken zum Schließen)';
    box.appendChild(hint);

    overlay.appendChild(box);
    overlay.addEventListener('click', hideSpielleitungModal);
    document.body.appendChild(overlay);
}

function hideSpielleitungModal() {
    const o = document.getElementById(SPIELLEITUNG_OVERLAY_ID);
    if (o && o.parentNode) o.parentNode.removeChild(o);
}

console.log('✅ spielleitung_modal.js geladen');

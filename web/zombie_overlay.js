// Zombie status icon, top-right (right of the dog@250, left of the power bulb@0).
// Shown when the zombie is at the player's location. The icon GLOWS according to the
// zombie's state (so the player can read his real mood, even when the chat persona
// "lies"):
//   AWAKENING  -> kein Glühen
//   HUNTING    -> rot
//   COOPERATIVE-> blau
//   DOUBTING   -> orange
//   CONVINCED  -> grün
//   REDEEMED   -> weiß
//   PETRIFIED  -> schwarz (+ Bild in Graustufen = "zu Stein")
const ZOMBIE_OVERLAY_ID = 'zombieOverlay';

// Glüh-Farbe je Zustand (null = kein Glühen).
const ZOMBIE_GLOW = {
    AWAKENING:   null,
    HUNTING:     '#ff2222',
    COOPERATIVE: '#3399ff',
    DOUBTING:    '#ff9900',
    CONVINCED:   '#33cc44',
    REDEEMED:    '#ffffff',
    PETRIFIED:   '#000000',
};

function showZombieOverlay(visible, state) {
    let overlay = document.getElementById(ZOMBIE_OVERLAY_ID);

    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = ZOMBIE_OVERLAY_ID;

        overlay.style.cssText = `
            position: fixed;
            top: 0;
            right: 125px;
            z-index: -1;
            width: 125px;
            height: 180px;
            border-radius: 14px;
            pointer-events: none;
        `;

        const img = document.createElement('img');
        img.id = ZOMBIE_OVERLAY_ID + '_img';
        img.src = 'zombie.png';
        img.style.cssText = `
            position: absolute;
            width: 100%;
            height: 100%;
            object-fit: contain;
            transition: opacity 0.5s ease, filter 0.5s ease;
            opacity: 0;
            -webkit-mask-image: radial-gradient(ellipse at center, black 70%, transparent 100%);
            mask-image: radial-gradient(ellipse at center, black 70%, transparent 100%);
            -webkit-mask-repeat: no-repeat;
            mask-repeat: no-repeat;
            -webkit-mask-size: 100% 100%;
            mask-size: 100% 100%;
        `;
        overlay.appendChild(img);

        document.body.appendChild(overlay);
    }

    const img = document.getElementById(ZOMBIE_OVERLAY_ID + '_img');
    img.style.opacity = visible ? '1' : '0';

    // Glühen je Zustand auf dem (unmaskierten) Container, damit es voll sichtbar ist.
    const color = visible ? ZOMBIE_GLOW[(state || '').toUpperCase()] : null;
    overlay.style.boxShadow = color ? `0 0 0 3px ${color}, 0 0 22px 8px ${color}` : 'none';
    // "Zu Stein": Bild entsättigen, damit PETRIFIED auch ohne sichtbares schwarzes
    // Glühen erkennbar ist.
    img.style.filter = (visible && (state || '').toUpperCase() === 'PETRIFIED')
        ? 'grayscale(1) brightness(0.6)' : 'none';
}

console.log('✅ zombie_overlay.js geladen');

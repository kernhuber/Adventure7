// Dog status icon, top-right (left of the zombie@125 and the power lightbulb@0).
// Shown when the dog is at the player's location. The frame blinks yellow when the
// dog is angry ("sauer") and red when it goes to attack (a mini-game starts).
const DOG_OVERLAY_ID = 'dogOverlay';

function showDogOverlay(visible, mode) {
    let overlay = document.getElementById(DOG_OVERLAY_ID);

    if (!overlay) {
        // inject blink keyframes once
        if (!document.getElementById('dogOverlayStyle')) {
            const st = document.createElement('style');
            st.id = 'dogOverlayStyle';
            st.textContent =
                '@keyframes dogBlinkYellow{0%,100%{box-shadow:none}50%{box-shadow:0 0 0 4px #ffd700,0 0 18px 6px #ffd700}}' +
                '@keyframes dogBlinkRed{0%,100%{box-shadow:none}50%{box-shadow:0 0 0 4px #ff2222,0 0 22px 8px #ff2222}}';
            document.head.appendChild(st);
        }

        overlay = document.createElement('div');
        overlay.id = DOG_OVERLAY_ID;
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            right: 250px;
            z-index: -1;
            width: 125px;
            height: 180px;
            border-radius: 14px;
            pointer-events: none;
        `;

        const img = document.createElement('img');
        img.id = DOG_OVERLAY_ID + '_img';
        img.src = 'dog.png';
        img.style.cssText = `
            position: absolute;
            width: 100%;
            height: 100%;
            object-fit: contain;
            transition: opacity 0.5s ease;
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

    const img = document.getElementById(DOG_OVERLAY_ID + '_img');
    img.style.opacity = visible ? '1' : '0';

    // Blinking frame on the (unmasked) container so the glow is fully visible.
    overlay.style.animation = 'none';
    if (visible && mode === 'attack') {
        overlay.style.animation = 'dogBlinkRed 0.4s steps(1) infinite';
    } else if (visible && mode === 'angry') {
        overlay.style.animation = 'dogBlinkYellow 0.6s steps(1) infinite';
    }
}

console.log('✅ dog_overlay.js geladen');

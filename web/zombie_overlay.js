const ZOMBIE_OVERLAY_ID = 'zombieOverlay';

function showZombieOverlay(visible) {
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

    const img = document.getElementById(ZOMBIE_OVERLAY_ID + '_img');
    img.style.opacity = visible ? '1' : '0';
}

console.log('✅ zombie_overlay.js geladen');

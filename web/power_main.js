const POWERMAIN_OVERLAY_ID = 'powerMainOverlay';

function showPowerMain(onoff) {
    let overlay = document.getElementById(POWERMAIN_OVERLAY_ID);

    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = POWERMAIN_OVERLAY_ID;

        overlay.style.cssText = `
            position: fixed;
            top: 0;
            right: 0;
            z-index: -1;
            width: 112px;
            height: 150px;
            pointer-events: none;
        `;

        // Zwei überlappende <img>-Elemente
        ['on', 'off'].forEach(state => {
            const img = document.createElement('img');
            img.id = POWERMAIN_OVERLAY_ID + '_img_' + state;
            img.src = state === 'on' ? 'power_on.png' : 'power_off.png';
            img.style.cssText = `
                position: absolute;
                width: 100%;
                height: 100%;
                object-fit: contain;
                transition: opacity 0.5s ease;
                opacity: ${state === 'on' ? '0' : '1'}; /* off ist initial sichtbar */
            `;
            overlay.appendChild(img);
        });

        document.body.appendChild(overlay);
    }

    // Hole beide Bilder
    const imgOn  = document.getElementById(POWERMAIN_OVERLAY_ID + '_img_on');
    const imgOff = document.getElementById(POWERMAIN_OVERLAY_ID + '_img_off');

    // Wechsle Sichtbarkeit durch Überblenden
    if (onoff) {
        imgOn.style.opacity  = '1';
        imgOff.style.opacity = '0';
    } else {
        imgOn.style.opacity  = '0';
        imgOff.style.opacity = '1';
    }
}

console.log('✅ power_main.js mit sanfter Überblendung geladen');
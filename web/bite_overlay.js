// bite_overlay.js — dramatic popup shown when the zombie bites the player.
const BITE_OVERLAY_ID = 'biteOverlay';
let _biteTimer = null;

function showBiteOverlay(message) {
    hideBiteOverlay();

    if (!document.getElementById('biteOverlayStyle')) {
        const st = document.createElement('style');
        st.id = 'biteOverlayStyle';
        st.textContent =
            '@keyframes biteFadeIn{from{opacity:0}to{opacity:1}}' +
            '@keyframes biteShake{0%,100%{transform:translateX(0)}25%{transform:translateX(-9px)}75%{transform:translateX(9px)}}' +
            '@keyframes biteThrob{0%,100%{box-shadow:0 0 30px 6px rgba(255,0,0,0.55)}50%{box-shadow:0 0 60px 18px rgba(255,0,0,0.95)}}';
        document.head.appendChild(st);
    }

    const overlay = document.createElement('div');
    overlay.id = BITE_OVERLAY_ID;
    overlay.style.cssText = `
        position: fixed; inset: 0; z-index: 11000;
        display: flex; align-items: center; justify-content: center;
        background: radial-gradient(circle, rgba(140,0,0,0.45) 0%, rgba(0,0,0,0.85) 80%);
        cursor: pointer; animation: biteFadeIn 0.15s ease-out;
    `;

    const box = document.createElement('div');
    box.style.cssText = `
        max-width: 620px; margin: 20px; padding: 30px 40px; text-align: center;
        background: #1a0000; border: 4px solid #ff2222; border-radius: 14px;
        animation: biteShake 0.4s ease-in-out 0s 3, biteThrob 0.8s ease-in-out infinite;
    `;
    box.innerHTML =
        '<div style="font-size:3em;line-height:1;margin-bottom:10px">🧟‍♂️🩸</div>' +
        '<div style="color:#ff3b3b;font-weight:bold;font-size:2em;text-shadow:2px 2px 6px #000;margin-bottom:14px">' +
        'Der Zombie hat dich gebissen!!</div>' +
        '<div style="color:#ffd0d0;font-size:1.1em;line-height:1.4">' +
        String(message || '').replace(/\n/g, '<br>') + '</div>' +
        '<div style="color:#aa6666;font-size:0.8em;margin-top:18px">(Klicken zum Schließen)</div>';
    overlay.appendChild(box);

    overlay.addEventListener('click', hideBiteOverlay);
    document.body.appendChild(overlay);
    _biteTimer = setTimeout(hideBiteOverlay, 2800);
}

function hideBiteOverlay() {
    if (_biteTimer) { clearTimeout(_biteTimer); _biteTimer = null; }
    const o = document.getElementById(BITE_OVERLAY_ID);
    if (o && o.parentNode) o.parentNode.removeChild(o);
}

console.log('✅ bite_overlay.js geladen');

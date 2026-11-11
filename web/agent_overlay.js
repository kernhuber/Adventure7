// Agent status icon, top-right (left of the dog@250, zombie@125 and the power lightbulb@0).
// Nur im Agentenmodus sichtbar (agent_panel.js ruft showAgentOverlay auf). Gleiche Größe und
// Maskierung wie die anderen Icons; solange der Agent arbeitet, pulsiert ein bläulicher Rahmen.
// Die Position folgt dem Agenten-Panel über die CSS-Variable --agent-offset (siehe agent_panel.js).
const AGENT_OVERLAY_ID = 'agentOverlay';

function showAgentOverlay(visible, active) {
    let overlay = document.getElementById(AGENT_OVERLAY_ID);

    if (!overlay) {
        if (!document.getElementById('agentOverlayStyle')) {
            const st = document.createElement('style');
            st.id = 'agentOverlayStyle';
            st.textContent =
                '@keyframes agentPulse{0%,100%{box-shadow:0 0 0 2px #33ccff,0 0 8px 2px #33ccff}' +
                '50%{box-shadow:0 0 0 4px #33ccff,0 0 22px 8px #33ccff}}';
            document.head.appendChild(st);
        }

        overlay = document.createElement('div');
        overlay.id = AGENT_OVERLAY_ID;
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            right: calc(var(--agent-offset, 0px) + 375px);
            z-index: -1;
            width: 125px;
            height: 180px;
            border-radius: 14px;
            pointer-events: none;
        `;

        const img = document.createElement('img');
        img.id = AGENT_OVERLAY_ID + '_img';
        img.src = 'agent.png';
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

    document.getElementById(AGENT_OVERLAY_ID + '_img').style.opacity = visible ? '1' : '0';
    overlay.style.animation = (visible && active) ? 'agentPulse 1.2s ease-in-out infinite' : 'none';
}

console.log('✅ agent_overlay.js geladen');

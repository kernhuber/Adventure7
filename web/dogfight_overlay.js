// dogfight_overlay.js - Kampf zwischen Agent und Hund (nur im Agentenmodus).
//
// Ablauf (der Server wartet währenddessen, siehe AgentDialogs.do_minigame):
//   0-3 s   dogfight.png mit gefährlich wabernder roter Umrandung
//   3 s     Ergebnis: Hund gewinnt  -> Rahmen bleibt rot, der Hund zoomt über das Bild, "Der Hund gewinnt!"
//                     Agent gewinnt -> Rahmen wird grün, der Agent zoomt über das Bild, "Agent gewinnt!"
//                     Gleichstand   -> Rahmen wird gelb, "Unentschieden!"
//   +3 s    Overlay blendet aus, das Spiel geht weiter (ggf. Game Over)
// Das Wabern ist ein SVG-Filter (feTurbulence + feDisplacementMap), dessen Frequenz laufend verändert wird;
// er verzerrt nur den Rahmen, nicht das Bild.
const DOGFIGHT_PHASE_MS = 3000;

function showDogfight(result) {
    return new Promise((resolve) => {
        const old = document.getElementById('dogfightOverlay');
        if (old) old.remove();

        const COLORS = { red: '#ff2222', green: '#22dd44', gold: '#ffcc00' };
        const overlay = document.createElement('div');
        overlay.id = 'dogfightOverlay';
        overlay.style.cssText = 'position:fixed;inset:0;z-index:25000;background:rgba(0,0,0,0.88);display:flex;'
            + 'align-items:center;justify-content:center;opacity:0;transition:opacity 0.4s ease';

        overlay.innerHTML = `
            <svg width="0" height="0" style="position:absolute">
              <filter id="dogfightWaber" x="-20%" y="-20%" width="140%" height="140%">
                <feTurbulence id="dogfightTurb" type="turbulence" baseFrequency="0.015 0.02" numOctaves="2" seed="3" result="t"/>
                <feDisplacementMap in="SourceGraphic" in2="t" scale="22" xChannelSelector="R" yChannelSelector="G"/>
              </filter>
            </svg>
            <style>
              @keyframes dogfightGlow { 0%,100% { box-shadow: 0 0 25px 6px var(--df-color), inset 0 0 25px 6px var(--df-color); }
                                        50%     { box-shadow: 0 0 55px 18px var(--df-color), inset 0 0 55px 18px var(--df-color); } }
              @keyframes dogfightZoom { from { transform: translate(-50%,-50%) scale(0.05); opacity: 0; }
                                        to   { transform: translate(-50%,-50%) scale(1);    opacity: 1; } }
              @keyframes dogfightText { from { transform: translateX(-50%) scale(0.4); opacity: 0; }
                                        to   { transform: translateX(-50%) scale(1);   opacity: 1; } }
            </style>
            <div id="dogfightStage" style="position:relative;width:min(80vw, 118vh);aspect-ratio:1490/1055;--df-color:${COLORS.red}">
              <img src="dogfight.png" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border-radius:16px">
              <div id="dogfightFrame" style="position:absolute;inset:-8px;border:14px solid var(--df-color);border-radius:22px;
                   filter:url(#dogfightWaber);animation:dogfightGlow 0.9s ease-in-out infinite;pointer-events:none;
                   transition:border-color 0.6s ease"></div>
            </div>`;
        document.body.appendChild(overlay);
        const stage = overlay.querySelector('#dogfightStage');
        const turb = overlay.querySelector('#dogfightTurb');
        requestAnimationFrame(() => { overlay.style.opacity = '1'; });

        // Wabern: Frequenz der Turbulenz sanft hin- und herlaufen lassen.
        let t = 0, raf = 0;
        const wobble = () => {
            t += 0.05;
            turb.setAttribute('baseFrequency', `${0.012 + 0.006 * Math.sin(t)} ${0.02 + 0.008 * Math.cos(t * 1.3)}`);
            raf = requestAnimationFrame(wobble);
        };
        wobble();

        // Phase 2: Ergebnis
        setTimeout(() => {
            const dogWins = result === 'WON';          // 'WON' = der Hund gewinnt (wie in handle_minigame_result)
            const agentWins = result === 'LOST';
            const color = dogWins ? COLORS.red : agentWins ? COLORS.green : COLORS.gold;
            stage.style.setProperty('--df-color', color);   // Rahmen (und Glühen) wechseln die Farbe
            const text = dogWins ? 'Der Hund gewinnt!' : agentWins ? 'Agent gewinnt!' : 'Unentschieden!';

            if (dogWins || agentWins) {
                const img = document.createElement('img');
                img.src = dogWins ? 'dog.png' : 'agent.png';
                img.style.cssText = 'position:absolute;left:50%;top:50%;height:92%;width:auto;object-fit:contain;'
                    + 'transform:translate(-50%,-50%);animation:dogfightZoom 1s ease-out both;'
                    + '-webkit-mask-image:radial-gradient(ellipse at center,black 65%,transparent 100%);'
                    + 'mask-image:radial-gradient(ellipse at center,black 65%,transparent 100%)';
                stage.appendChild(img);
            }
            const label = document.createElement('div');
            label.textContent = text;
            label.style.cssText = `position:absolute;left:50%;bottom:6%;white-space:nowrap;font:bold clamp(28px,6vw,72px) Impact,Arial,sans-serif;`
                + `color:${color};text-shadow:0 0 12px #000,0 0 30px #000,3px 3px 0 #000;animation:dogfightText 0.7s ease-out 0.5s both`;
            stage.appendChild(label);

            // Phase 3: nach weiteren 3 s ausblenden, dann geht das Spiel weiter.
            setTimeout(() => {
                overlay.style.opacity = '0';
                setTimeout(() => { cancelAnimationFrame(raf); overlay.remove(); resolve(); }, 450);
            }, DOGFIGHT_PHASE_MS);
        }, DOGFIGHT_PHASE_MS);
    });
}

console.log('✅ dogfight_overlay.js geladen');

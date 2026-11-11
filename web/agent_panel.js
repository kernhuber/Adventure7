// agent_panel.js - Zuschauer-Panel für den Agentenmodus (?mode=agent).
//
// Im normalen Spiel tut diese Datei nur eines: einen Link "Agent spielen lassen" anzeigen.
// Im Agentenmodus baut sie ein ausklappbares Panel mit Steuerung (Start, Pause,
// Einzelschritt, Runde, Stopp, Tempo), Speichern/Laden und einem Protokoll aller Agenten-Aktionen.
// Alles plain JavaScript, kein Framework.

const agentPanel = (function () {
    const params = new URLSearchParams(window.location.search);
    const agentMode = params.get('mode') === 'agent';

    // Farben je Ereignisart (siehe Legende im Panel). 'hint' erscheint beim Mouseover der Legende.
    const KIND = {
        free:  { label: 'Freie Aktion', color: '#4da3ff', hint: 'Kostet keine Spielrunde: nachsehen, notieren, speichern.' },
        move:  { label: 'Zug',          color: '#5fd068', hint: 'Kostet genau eine Runde. Danach handeln die anderen Figuren.' },
        error: { label: 'Fehler',       color: '#ff6b6b', hint: 'Ungültiger Aufruf: kostet keine Runde, der Agent versucht es neu.' },
        chat:  { label: 'Chat',         color: '#c792ea', hint: 'Gespräch mit Hund oder Zombie.' },
        pin:   { label: 'PIN',          color: '#ffb347', hint: 'Eingabe am PIN-Pad des Geldautomaten.' },
        text:  { label: 'Modelltext',   color: '#aaaaaa', hint: 'Was das Modell tatsächlich ausgibt (keine erfundene Gedankenwiedergabe).' },
    };
    const STATE_TEXT = {
        idle: 'bereit', running: '▶ läuft', paused: '⏸ pausiert', waiting: '⏳ wartet auf Freigabe (Schritt / Runde / Start)',
        stopped: '⏹ gestoppt', finished: '🏁 beendet', game_over: '🏁 Spiel zu Ende',
    };
    const PANEL_WIDTH = 450;        // in "ungezoomten" Pixeln

    let logEl = null, statusEl = null, statsEl = null, notebookEl = null, panelEl = null;
    let zoom = 1, collapsed = false;

    function esc(t) {
        return String(t ?? '').replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
    }

    function send(action, extra) {
        if (backend && backend.ws && backend.ws.readyState === WebSocket.OPEN) {
            backend.ws.send(JSON.stringify(Object.assign({ type: 'agent_control', action: action }, extra || {})));
        }
    }

    function addModeLink() {
        const host = document.getElementById('mode-switch');
        if (!host) return;
        const a = document.createElement('a');
        a.style.cssText = 'color:#ffd700;font-size:16px;text-decoration:none;border:1px solid #cd853f;padding:6px 14px;border-radius:6px;background:#5a4633';
        if (agentMode) {
            a.href = window.location.pathname;           // ohne Query = Mensch spielt
            a.textContent = '👤 Selbst spielen';
        } else {
            a.href = '?mode=agent';
            a.textContent = '🤖 Agent spielen lassen';
        }
        host.appendChild(a);
    }

    function btn(text, title, onclick) {
        const b = document.createElement('button');
        b.textContent = text;
        b.title = title;
        b.style.cssText = 'font-size:16px;padding:6px 10px;margin:2px;background:#5a4633;color:#f5deb3;border:1px solid #cd853f;border-radius:5px;cursor:pointer';
        b.onclick = onclick;
        return b;
    }

    // --- Beamer-Zoom: das ganze Panel vergrößern/verkleinern (merkt sich die Einstellung) ---------
    function layout() {
        if (!panelEl) return;
        panelEl.style.zoom = zoom;
        const w = (collapsed ? 150 : PANEL_WIDTH) * zoom;
        panelEl.style.width = (collapsed ? 150 : PANEL_WIDTH) + 'px';
        document.body.style.marginRight = (w + 10) + 'px';
    }
    function setZoom(z) {
        zoom = Math.min(2, Math.max(0.7, Math.round(z * 100) / 100));
        try { localStorage.setItem('agentPanelZoom', String(zoom)); } catch (e) { /* Speicher evtl. gesperrt */ }
        layout();
    }

    // --- Spielstände laden: Liste vom Server, Auswahl lädt die Seite neu mit &save=... ------------
    function showSlots(slots) {
        const old = document.getElementById('agent-slots');
        if (old) old.remove();
        const overlay = document.createElement('div');
        overlay.id = 'agent-slots';
        overlay.style.cssText = 'position:fixed;inset:0;z-index:30000;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center';
        const box = document.createElement('div');
        box.style.cssText = 'background:#1d1a17;color:#f5deb3;border:2px solid #cd853f;border-radius:8px;padding:16px;max-width:600px;max-height:80vh;overflow-y:auto;font-size:16px';
        box.innerHTML = '<b style="font-size:20px">📂 Spielstand laden (Agentenmodus)</b>'
            + '<div style="font-size:14px;margin:6px 0">🤖 = enthält Gedächtnis des Agenten (Notizbuch, Verlauf, Notiz an sich selbst). '
            + 'Ohne 🤖 startet der Agent ohne Gedächtnis.</div>';
        (slots || []).forEach(s => {
            const row = document.createElement('div');
            row.style.cssText = 'margin:6px 0';
            row.appendChild(btn((s.agent ? '🤖 ' : '') + s.name, 'Diesen Spielstand laden', () => {
                const p = new URLSearchParams(window.location.search);
                p.set('mode', 'agent');
                p.set('save', s.name);
                window.location.href = window.location.pathname + '?' + p.toString();
            }));
            if (s.agent && s.notiz) {
                const n = document.createElement('div');
                n.style.cssText = 'font-size:13px;color:#ffd700;margin-left:10px';
                n.textContent = '📝 ' + s.notiz;
                row.appendChild(n);
            }
            box.appendChild(row);
        });
        if (!slots || !slots.length) box.appendChild(document.createTextNode('Keine Spielstände vorhanden.'));
        const close = btn('Schließen', '', () => overlay.remove());
        close.style.marginTop = '10px';
        box.appendChild(close);
        overlay.appendChild(box);
        document.body.appendChild(overlay);
    }

    function buildPanel() {
        const bar = document.getElementById('input-bar');      // Menschen-Eingabe im Agentenmodus ausblenden
        if (bar) bar.style.display = 'none';
        try { zoom = parseFloat(localStorage.getItem('agentPanelZoom')) || 1; } catch (e) { zoom = 1; }

        const panel = document.createElement('div');
        panel.id = 'agent-panel';
        panelEl = panel;
        panel.style.cssText = 'position:fixed;top:0;right:0;bottom:0;z-index:20000;background:#1d1a17;'
            + 'color:#f5deb3;border-left:2px solid #cd853f;padding:10px;font-size:16px;box-sizing:border-box;display:flex;flex-direction:column';

        const title = document.createElement('div');
        title.innerHTML = '<b style="font-size:20px">🤖 Agent</b>';
        const toggle = btn('⮜ einklappen', 'Panel ein-/ausklappen', () => {
            const body = document.getElementById('agent-body');
            collapsed = !collapsed;
            body.style.display = collapsed ? 'none' : 'flex';
            toggle.textContent = collapsed ? '⮞ ausklappen' : '⮜ einklappen';
            layout();
        });
        toggle.style.float = 'right';
        title.appendChild(toggle);
        panel.appendChild(title);

        const body = document.createElement('div');
        body.id = 'agent-body';
        // Steuerung/Status bleiben oben stehen; nur Notizbuch und Protokoll (agent-scroll) scrollen.
        body.style.cssText = 'display:flex;flex-direction:column;flex:1;min-height:0';

        statusEl = document.createElement('div');
        statusEl.style.cssText = 'margin:8px 0;padding:6px;background:#2b2621;border-radius:5px';
        statusEl.textContent = 'bereit – „Start“ drücken';
        body.appendChild(statusEl);

        statsEl = document.createElement('div');
        statsEl.style.cssText = 'margin:4px 0;padding:6px;background:#2b2621;border-radius:5px;font-size:14px';
        statsEl.textContent = 'Aufrufe diese Runde: – · Tokens: – · Modellaufrufe: –';
        body.appendChild(statsEl);

        const controls = document.createElement('div');
        controls.appendChild(btn('▶ Start', 'Agent laufen lassen', () => send('start')));
        controls.appendChild(btn('⏸ Pause', 'Anhalten', () => send('pause')));
        controls.appendChild(btn('⏭ Schritt', 'Genau einen Schritt (Werkzeugaufruf)', () => send('step')));
        controls.appendChild(btn('⏩ Runde', 'Bis zum nächsten Zug', () => send('round')));
        controls.appendChild(btn('⏹ Stopp', 'Beenden', () => send('stop')));
        body.appendChild(controls);

        const extras = document.createElement('div');
        extras.appendChild(btn('💾 Speichern', 'Spielstand UND Gedächtnis des Agenten speichern', () => {
            const vorschlag = 'agent_' + new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
            const name = window.prompt('Name des Spielstands:', vorschlag);
            if (name) send('save', { name: name });
        }));
        extras.appendChild(btn('📂 Laden', 'Spielstand laden (Seite lädt neu)', () => send('slots')));
        extras.appendChild(btn('A−', 'Schrift kleiner', () => setZoom(zoom - 0.15)));
        extras.appendChild(btn('A+', 'Schrift größer (Beamer)', () => setZoom(zoom + 0.15)));
        body.appendChild(extras);

        const hint = document.createElement('div');
        hint.style.margin = '6px 0';
        hint.innerHTML = '<input id="agent-hint" type="text" placeholder="💬 Hinweis an den Agenten, z. B. „Sprich mit dem Hund“" '
            + 'style="width:68%;font-size:15px;padding:5px;background:#2b2621;color:#f5deb3;border:1px solid #cd853f;border-radius:4px"> ';
        const sendHint = () => {
            const input = document.getElementById('agent-hint');
            if (input.value.trim()) { send('hint', { text: input.value.trim() }); input.value = ''; }
        };
        hint.appendChild(btn('Senden', 'Gilt ab der nächsten Runde', sendHint));
        hint.querySelector('input').onkeydown = (e) => { if (e.key === 'Enter') sendHint(); };
        body.appendChild(hint);

        const tempo = document.createElement('div');
        tempo.style.margin = '6px 0';
        tempo.innerHTML = 'Tempo: <input id="agent-tempo" type="range" min="0" max="3000" step="100" value="800" style="vertical-align:middle">'
            + ' <span id="agent-tempo-val">800 ms</span>';
        body.appendChild(tempo);
        tempo.querySelector('input').oninput = (e) => {
            document.getElementById('agent-tempo-val').textContent = e.target.value + ' ms';
            send('tempo', { delay_ms: Number(e.target.value) });
        };

        const legend = document.createElement('div');
        legend.style.cssText = 'font-size:14px;margin:6px 0';
        legend.innerHTML = Object.values(KIND).map(k => `<span style="color:${k.color}" title="${esc(k.hint)}">■ ${k.label}</span>`).join(' &nbsp; ');
        body.appendChild(legend);

        const scrollEl = document.createElement('div');
        scrollEl.id = 'agent-scroll';
        scrollEl.style.cssText = 'flex:1;min-height:0;overflow-y:auto';
        body.appendChild(scrollEl);

        const nb = document.createElement('details');
        nb.style.cssText = 'margin:8px 0;padding:6px;background:#2b2621;border-radius:5px';
        nb.open = true;
        nb.innerHTML = '<summary style="cursor:pointer"><b>📓 Notizbuch</b></summary>';
        notebookEl = document.createElement('div');
        notebookEl.style.cssText = 'font-size:14px;white-space:pre-wrap;margin-top:4px;color:#ddd';
        notebookEl.textContent = '(leer)';
        nb.appendChild(notebookEl);
        scrollEl.appendChild(nb);

        logEl = document.createElement('div');
        logEl.id = 'agent-log';
        scrollEl.appendChild(logEl);

        panel.appendChild(body);
        document.body.appendChild(panel);
        layout();
    }

    function scrollLog() {
        const sc = document.getElementById('agent-scroll');
        if (sc) sc.scrollTop = sc.scrollHeight;
    }

    function handle(data) {
        if (!agentMode || !logEl) return;
        if (data.type === 'agent_status') {
            statusEl.textContent = `${STATE_TEXT[data.state] || data.state} · Runde ${data.round} · Schritt ${data.step}`
                + (data.model ? ` · ${data.model}` : '');
            if (data.calls_limit !== undefined) {
                statsEl.textContent = `Aufrufe diese Runde: ${data.calls_round}/${data.calls_limit} · `
                    + `Tokens: Runde ${data.tokens_round} / gesamt ${data.tokens_total} · Modellaufrufe: ${data.model_calls}`;
            }
        } else if (data.type === 'agent_event') {
            const k = KIND[data.kind] || KIND.text;
            const args = Object.values(data.args || {}).join(' ');
            const row = document.createElement('div');
            row.style.cssText = `margin:8px 0;padding:6px 8px;border-left:5px solid ${k.color};background:#2b2621;border-radius:4px`;
            row.innerHTML = `<div style="color:${k.color}"><b>${esc(k.label)}</b> · Runde ${esc(data.round)} · <b>${esc(data.tool)}</b> ${esc(args)}</div>`
                + (data.warum ? `<div style="color:#ffd700;font-size:17px;margin:3px 0">💭 ${esc(data.warum)}</div>` : '')
                + (data.result ? `<div style="font-size:14px;color:#ddd;white-space:pre-wrap">${esc(data.result)}</div>` : '');
            logEl.appendChild(row);
            scrollLog();
        } else if (data.type === 'agent_notebook') {
            notebookEl.textContent = data.text || '(leer)';
        } else if (data.type === 'agent_slots') {
            showSlots(data.slots);
        } else if (data.type === 'agent_summary') {
            const row = document.createElement('div');
            row.style.cssText = 'margin:10px 0;padding:10px;border:2px solid #ffd700;border-radius:6px;background:#2b2621';
            row.innerHTML = `<b>🏁 Zusammenfassung: ${esc(data.ergebnis)}</b><div style="font-size:14px;margin-top:4px">`
                + `Runden: ${esc(data.runden)} · Werkzeugaufrufe: ${esc(data.aufrufe)} · Modellaufrufe: ${esc(data.modellaufrufe)}<br>`
                + `Tokens: ${esc(data.tokens)}<br>Letzter Ort: ${esc(data.letzter_ort)}<br>`
                + `Besuchte Orte: ${esc((data.orte || []).join(', '))}<br>Spur: ${esc(data.trace_datei || '-')}</div>`;
            logEl.appendChild(row);
            scrollLog();
        }
    }

    window.addEventListener('DOMContentLoaded', function () {
        addModeLink();
        if (agentMode) buildPanel();
    });

    return { handle: handle };
})();

// save_load.js
// GUI für Speichern/Laden (benannte Slots). Die Buttons öffnen ein kleines Modal; das
// eigentliche Speichern/Laden läuft über den bewährten Text-Befehlspfad
// (backend.sendCommand('speichere <name>' / 'lade <name>')), den der Server in
// command_engine._handle_save_load abfängt. Für die Lade-Auswahl fragt der Client die
// Slot-Liste beim Server an ({type:'list_slots'} -> {type:'slot_list', slots:[...]}).

const SL_MODAL_ID = 'saveLoadOverlay';

function _slClose() {
    const o = document.getElementById(SL_MODAL_ID);
    if (o) o.remove();
}

// Grund-Modal (Backdrop + Box mit Titel + Body). buildBody(box) füllt den Inhalt.
function _slModal(title, buildBody) {
    _slClose();
    const overlay = document.createElement('div');
    overlay.id = SL_MODAL_ID;
    overlay.style.cssText = 'position:fixed;inset:0;z-index:10002;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;';
    overlay.addEventListener('click', (e) => { if (e.target === overlay) _slClose(); });

    const box = document.createElement('div');
    box.style.cssText = 'background:#2b1d10;color:#f5deb3;border:3px solid #cd853f;border-radius:10px;box-shadow:0 10px 40px rgba(0,0,0,0.6);min-width:320px;max-width:90%;max-height:80vh;overflow:auto;';

    const header = document.createElement('div');
    header.style.cssText = 'background:#8b4513;color:#fff;font-weight:bold;font-size:18px;padding:10px 16px;';
    header.textContent = title;
    box.appendChild(header);

    const body = document.createElement('div');
    body.style.cssText = 'padding:16px;display:flex;flex-direction:column;gap:12px;';
    box.appendChild(body);
    buildBody(body);

    overlay.appendChild(box);
    document.body.appendChild(overlay);
    return body;
}

function _slButton(label, onclick, bg) {
    const b = document.createElement('button');
    b.textContent = label;
    b.style.cssText = 'padding:8px 16px;border:none;border-radius:5px;font-size:15px;cursor:pointer;background:' + (bg || '#8b4513') + ';color:#fff;';
    b.addEventListener('click', onclick);
    return b;
}

// --- Speichern: Name eingeben -----------------------------------------------------
window.showSaveDialog = function () {
    const body = _slModal('💾 Spiel speichern', (body) => {
        const label = document.createElement('div');
        label.textContent = 'Speichern unter (Name):';
        const input = document.createElement('input');
        input.type = 'text';
        input.placeholder = 'z.B. hoehle-vor-zombie';
        input.style.cssText = 'padding:8px;font-size:15px;border-radius:5px;border:1px solid #cd853f;background:#f5deb3;color:#2b1d10;';
        input.addEventListener('keypress', (e) => { if (e.key === 'Enter') submit(); });

        const row = document.createElement('div');
        row.style.cssText = 'display:flex;gap:10px;justify-content:flex-end;';
        const submit = () => {
            const name = (input.value || '').trim() || 'quicksave';
            if (backend) backend.sendCommand('speichere ' + name);
            _slClose();
        };
        row.appendChild(_slButton('Abbrechen', _slClose, '#5a4633'));
        row.appendChild(_slButton('Speichern', submit));

        body.appendChild(label);
        body.appendChild(input);
        body.appendChild(row);
        setTimeout(() => input.focus(), 0);
    });
};

// --- Laden: Slot-Liste vom Server anfordern, dann auswählen ------------------------
window.showLoadDialog = function () {
    if (backend && backend.ws && backend.ws.readyState === WebSocket.OPEN) {
        backend.ws.send(JSON.stringify({ type: 'list_slots' }));
    }
    // Das Modal öffnet sich, wenn die Antwort (slot_list) eintrifft -> renderLoadSlots().
};

// Wird von websockets.js aufgerufen, sobald {type:'slot_list'} ankommt.
window.renderLoadSlots = function (slots) {
    _slModal('📂 Spielstand laden', (body) => {
        if (!slots || slots.length === 0) {
            const empty = document.createElement('div');
            empty.textContent = 'Keine Spielstände vorhanden.';
            body.appendChild(empty);
        } else {
            const hint = document.createElement('div');
            hint.textContent = 'Wähle einen Spielstand:';
            body.appendChild(hint);
            slots.forEach((name) => {
                // Erst bestätigen (aktueller Spielstand geht verloren), dann laden.
                const b = _slButton('📂  ' + name, () => _confirmLoad(name, slots));
                b.style.textAlign = 'left';
                body.appendChild(b);
            });
        }
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;justify-content:flex-end;';
        row.appendChild(_slButton('Abbrechen', _slClose, '#5a4633'));
        body.appendChild(row);
    });
};

// Bestätigung vor dem Laden (nur im GUI-Pfad): der aktuelle, ungespeicherte Spielstand
// geht dabei verloren. 'Zurück' rendert die Slot-Liste erneut (ohne erneuten Serverabruf).
function _confirmLoad(name, slots) {
    _slModal('⚠️ Laden bestätigen', (body) => {
        const msg = document.createElement('div');
        msg.style.lineHeight = '1.5';
        msg.innerHTML = "Der <b>aktuelle Spielstand geht verloren</b> (sofern nicht gespeichert)."
            + "<br><br>Spielstand '<b>" + name + "</b>' wirklich laden?";
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;gap:10px;justify-content:flex-end;';
        row.appendChild(_slButton('Zurück', () => renderLoadSlots(slots), '#5a4633'));
        row.appendChild(_slButton('Laden', () => {
            if (backend) backend.sendCommand('lade ' + name);
            _slClose();
        }, '#8b0000'));
        body.appendChild(msg);
        body.appendChild(row);
    });
}

console.log('save_load.js erfolgreich geladen');

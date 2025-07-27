function gameOver(won, text) {
    // Overlay erstellen
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: 10000;
        display: flex;
        align-items: center;
        font-family: 'Courier New', monospace;
        font-size: 18px;
        color: white;
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
    `;

    // Farbverlauf je nach Spielergebnis
    if (won) {
        // Gewonnen: hellgrün -> hellblau -> dunkelblau
        overlay.style.background = `
            linear-gradient(to top, 
                #90EE90 0%, 
                #87CEEB 50%, 
                #1e3a5f 100%)
        `;
    } else {
        // Verloren: hellrot -> dunkelrot -> schwarz
        overlay.style.background = `
            linear-gradient(to top, 
                #FFB6C1 0%, 
                #8B0000 50%, 
                #000000 100%)
        `;
    }

    // Bild-Container für die linke Seite
    const imageContainer = document.createElement('div');
    imageContainer.style.cssText = `
        width: 50%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        padding-left: 50px;
    `;

    const gameImage = document.createElement('img');
    gameImage.src = won ? 'game_won.png' : 'game_lost.png';
    gameImage.style.cssText = `
        max-width: 80%;
        max-height: 60%;
        object-fit: contain;
        filter: drop-shadow(0 0 20px rgba(255, 255, 255, 0.5));
    `;

    // Fehlerbehandlung für Bilder
    gameImage.onerror = function() {
        this.style.display = 'none';
    };

    imageContainer.appendChild(gameImage);

    // Text-Container für die rechte Seite
    const textContainer = document.createElement('div');
    textContainer.style.cssText = `
        width: 50%;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 50px;
        line-height: 1.6;
        overflow: hidden;
    `;

    const textDisplay = document.createElement('div');
    textDisplay.style.cssText = `
        font-size: 20px;
        letter-spacing: 1px;
        word-wrap: break-word;
        overflow-wrap: break-word;
    `;

    textContainer.appendChild(textDisplay);

    // Overlay zusammenbauen
    overlay.appendChild(imageContainer);
    overlay.appendChild(textContainer);
    document.body.appendChild(overlay);

    // Audio-Kontext für SciFi-Piepsen
    let audioContext;
    try {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    } catch (e) {
        console.warn('Audio not supported');
    }

    function playBeep() {
        if (!audioContext) return;

        try {
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            // SciFi-ähnliche Frequenz
            oscillator.frequency.setValueAtTime(800 + Math.random() * 400, audioContext.currentTime);
            oscillator.type = 'square';

            // Kurzer Piepston
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.1);
        } catch (e) {
            // Fehler beim Audio ignorieren
        }
    }

    // EINFACHE TEXT-NORMALISIERUNG + BROWSER-UMBRUCH
    function preprocessText_old(rawText) {
        console.log("📝 Ursprünglicher Text:", JSON.stringify(rawText));

        // 1. Normalisiere alle Zeilenenumbrüche von \r\n nach \n (eliminiere alle \r)
        let processed = rawText.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
        console.log("1️⃣ Nach Normalisierung:", JSON.stringify(processed));

        // 2. Ersetze alle EINZELNEN Zeilenumbrüche zwischen Texten durch ein Leerzeichen
        // 3. Nimm von mehrfachen Zeilenumbrüchen einen weg (aus \n\n wird \n)

        // KORRIGIERTE LOGIK:
        // - \n\n (Absatzende) → \n (bleibt als Absatzende)
        // - \n (einzeln) → Leerzeichen (Zeilenumbruch innerhalb Absatz)

        // Schritt A: Markiere echte Absatzenden (\n\n → ABSATZENDE)
        processed = processed.replace(/\n\n/g, '§§ABSATZENDE§§');
        console.log("2️⃣ Nach Absatzende-Markierung:", JSON.stringify(processed));

        // Schritt B: Alle übrigen einzelnen \n → Leerzeichen
        processed = processed.replace(/\n/g, ' ');
        console.log("3️⃣ Nach Einzelumbruch→Leerzeichen:", JSON.stringify(processed));

        // Schritt C: Absatzenden zurück zu \n
        processed = processed.replace(/§§ABSATZENDE§§/g, '\n');
        console.log("4️⃣ Nach Absatzende-Wiederherstellung:", JSON.stringify(processed));

        // 4. Bereinige mehrfache Leerzeichen
        processed = processed.replace(/\s+/g, ' ');
        console.log("5️⃣ Nach Leerzeichen-Bereinigung:", JSON.stringify(processed));

        return processed.trim();
    }
    function preprocessText(rawText) {
        console.log("📝 Ursprünglicher Text:", JSON.stringify(rawText));

        // 1. Vereinheitliche Zeilenumbrüche
        let processed = rawText.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

        // 2. Markiere doppelte Zeilenumbrüche als Absatzende
        processed = processed.replace(/\n\n+/g, '§§ABSATZENDE§§');

        // 3. Mehrfache Leerzeichen zusammenfassen (aber nicht Zeilenumbrüche)
        processed = processed.replace(/[ \t]+/g, ' ');

        // 4. Absatzmarkierungen zurück zu doppelten \n
        processed = processed.replace(/§§ABSATZENDE§§/g, '\n\n');

        // NICHT: einfache \n löschen! Die brauchst du ja später!
        // => Returniere nun den Text, der echte \n enthält

        console.log("✅ Nach Verarbeitung:", JSON.stringify(processed));
        return processed.trim();
    }
    function createTokens(processedText) {
        const tokens = [];

        console.log("🔧 Token-Erstellung startet für Text:", JSON.stringify(processedText));

        for (let i = 0; i < processedText.length; i++) {
            const char = processedText[i];

            if (char === '\n') {
                // Expliziter Zeilenenumbruch → <br>
                tokens.push({ type: 'break', content: '<br>' });
                console.log(`📍 <br> Token erstellt an Position ${i} (Zeichen: \\n)`);
            } else {
                // Normales Zeichen → HTML-escaped
                tokens.push({
                    type: 'char',
                    content: char
                        .replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;')
                        .replace(/"/g, '&quot;')
                        .replace(/'/g, '&#39;')
                });
            }
        }

        const breakCount = tokens.filter(t => t.type === 'break').length;
        console.log(`🎯 Token-Liste erstellt: ${tokens.length} Tokens total, ${breakCount} <br> Tokens`);

        // Debug: Zeige erste paar und letzte paar Tokens
        const preview = tokens.slice(0, 10).map(t => t.type === 'break' ? '<BR>' : t.content).join('');
        const suffix = tokens.length > 20 ? '...' + tokens.slice(-10).map(t => t.type === 'break' ? '<BR>' : t.content).join('') : '';
        console.log(`📝 Token-Preview: "${preview}${suffix}"`);

        return tokens;
    }

    // Text preprocessing
    const processedText = preprocessText(text);
    const tokens = createTokens(processedText);

    // Typewriter-Effekt mit innerHTML
    let currentTokenIndex = 0;
    let displayedHtml = '';

    function typeNextToken() {
        if (currentTokenIndex >= tokens.length) {
            console.log("✅ Typewriter fertig!");

            // 🔍 DEBUG: Finalen HTML-Inhalt anzeigen
            debugFinalHTML();
            return;
        }

        const token = tokens[currentTokenIndex];
        displayedHtml += token.content;

        // ✨ BROWSER MACHT DEN UMBRUCH! ✨
        textDisplay.innerHTML = displayedHtml;

        // Debug-Info für <br> Tags
        if (token.type === 'break') {
            console.log(`📍 <br> eingefügt an Position ${currentTokenIndex}, HTML-Länge: ${displayedHtml.length}`);
        }

        currentTokenIndex++;

        // Piepsen nur bei sichtbaren Zeichen (nicht bei <br>)
        if (token.type === 'char' && token.content.trim().length > 0) {
            playBeep();
        }

        // Timing
        let delay = 40; // Standard für Zeichen
        if (token.type === 'break') {
            delay = 100; // Pause bei <br>
        } else if (token.content === ' ') {
            delay = 25; // Leerzeichen schneller
        }

        setTimeout(typeNextToken, delay);
    }

    function debugFinalHTML() {
        console.log("\n" + "=".repeat(60));
        console.log("🔍 FINAL DEBUG REPORT");
        console.log("=".repeat(60));

        const finalHTML = textDisplay.innerHTML;

        console.log("📊 Statistics:");
        console.log(`- Total HTML length: ${finalHTML.length} characters`);
        console.log(`- <br> count: ${(finalHTML.match(/<br>/g) || []).length}`);
        console.log(`- Total tokens processed: ${tokens.length}`);
        console.log(`- Break tokens in input: ${tokens.filter(t => t.type === 'break').length}`);

        console.log("\n📝 Final HTML (raw):");
        console.log(JSON.stringify(finalHTML));

        console.log("\n📋 Final HTML (formatted for readability):");
        const formatted = finalHTML
            .replace(/<br>/g, '<br>\n')
            .split('\n')
            .map((line, i) => `${String(i+1).padStart(3, '0')}: ${line}`)
            .join('\n');
        console.log(formatted);

        console.log("\n🔍 Looking for line breaks:");
        if (finalHTML.includes('<br>')) {
            console.log("✅ <br> tags found in final HTML");
            const brPositions = [];
            let index = finalHTML.indexOf('<br>');
            while (index !== -1) {
                brPositions.push(index);
                index = finalHTML.indexOf('<br>', index + 1);
            }
            console.log(`📍 <br> positions: ${brPositions.join(', ')}`);
        } else {
            console.log("❌ NO <br> tags found in final HTML!");
        }

        console.log("\n📐 Container Info:");
        console.log(`- Container width: ${textContainer.offsetWidth}px`);
        console.log(`- Text display width: ${textDisplay.offsetWidth}px`);
        console.log(`- Computed font: ${window.getComputedStyle(textDisplay).font}`);

        console.log("=".repeat(60));
    }

    // Audio-Kontext aktivieren (falls nötig) und Typing starten
    setTimeout(() => {
        console.log("🚀 Starte Typewriter-Effekt mit Browser-Umbruch...");
        console.log("📊 Text-Container Breite:", textContainer.offsetWidth);

        if (audioContext && audioContext.state === 'suspended') {
            audioContext.resume().then(() => {
                typeNextToken();
            }).catch(() => {
                typeNextToken();
            });
        } else {
            typeNextToken();
        }
    }, 500); // Kurze Verzögerung für dramatischen Effekt
}
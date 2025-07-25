function showPinPad(expectedHash) {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.style.position = 'fixed';
    overlay.style.top = 0;
    overlay.style.left = 0;
    overlay.style.width = '100vw';
    overlay.style.height = '100vh';
    overlay.style.backgroundColor = 'rgba(0,0,0,0.7)';
    overlay.style.display = 'flex';
    overlay.style.alignItems = 'center';
    overlay.style.justifyContent = 'center';
    overlay.style.zIndex = 9999;

    let enteredPin = '';
    let resultStatus = null;

    const container = document.createElement('div');
    container.style.backgroundColor = '#222';
    container.style.padding = '20px';
    container.style.borderRadius = '10px';
    container.style.color = 'white';
    container.style.textAlign = 'center';
    container.style.fontFamily = 'monospace';

    const display = document.createElement('div');
    display.textContent = '';
    display.style.backgroundColor = '#444';
    display.style.color = 'white';
    display.style.fontSize = '24px';
    display.style.padding = '10px';
    display.style.marginBottom = '15px';
    display.style.borderRadius = '5px';
    display.style.height = '32px';
    display.style.display = 'flex';
    display.style.alignItems = 'center';
    display.style.justifyContent = 'center';
    display.style.transition = 'background-color 0.5s';

    const keyboard = document.createElement('div');
    keyboard.style.display = 'grid';
    keyboard.style.gridTemplateColumns = 'repeat(3, 60px)';
    keyboard.style.gridGap = '10px';
    keyboard.style.justifyContent = 'center';

    const buttons = ['1','2','3','4','5','6','7','8','9','Del','0','Enter'];

    buttons.forEach(key => {
      const btn = document.createElement('button');
      btn.textContent = key;
      btn.style.padding = '15px';
      btn.style.fontSize = '16px';
      btn.style.borderRadius = '5px';
      btn.style.border = 'none';
      btn.style.cursor = 'pointer';
      btn.style.backgroundColor = '#888';
      btn.style.color = 'white';
      btn.disabled = key === 'Enter';

      btn.addEventListener('click', () => {
        if (resultStatus !== null) return;

        if (key === 'Del') {
          enteredPin = enteredPin.slice(0, -1);
        } else if (key === 'Enter') {
          const hash = CryptoJS.MD5(enteredPin).toString();
          console.log(enteredPin)
          console.log(hash)
          console.log(expectedHash)
          if (hash === expectedHash) {
            display.textContent = 'Geheimzahl korrekt';
            display.style.backgroundColor = 'green';
            resultStatus = 'OK';
          } else {
            display.textContent = 'Geheimzahl falsch';
            display.style.backgroundColor = 'red';
            resultStatus = 'FAIL';
          }
        } else {
          if (enteredPin.length < 4) {
            enteredPin += key;
          }
        }

        if (enteredPin.length === 4) {
          keyboard.querySelectorAll('button').forEach(b => {
            if (b.textContent === 'Enter') b.disabled = false;
          });
        } else {
          keyboard.querySelectorAll('button').forEach(b => {
            if (b.textContent === 'Enter') b.disabled = true;
          });
        }

        if (resultStatus === null) {
          display.textContent = '*'.repeat(enteredPin.length);
        }
      });

      keyboard.appendChild(btn);
    });

    container.appendChild(display);
    container.appendChild(keyboard);
    overlay.appendChild(container);
    document.body.appendChild(overlay);

    overlay.addEventListener('click', (e) => {
      if (resultStatus !== null && e.target === overlay) {
        document.body.removeChild(overlay);
        resolve(resultStatus);
      }
    });
  });
}
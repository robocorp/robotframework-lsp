callback = arguments[arguments.length - 1];

picker =
  document.getElementById('robocode-picker') || document.createElement('div');
picker.setAttribute('id', 'robocode-picker');
highlighted = document.querySelectorAll('[data-robocode-highlight]')[0];

function highlightElement(event) {
  var element = event.target;
  clearHighlight();
  element.setAttribute('data-robocode-highlight', '');
  highlighted = element;
}

function clearHighlight() {
  if (highlighted !== undefined) {
    highlighted.removeAttribute('data-robocode-highlight');
  }
}

function pickElement(event) {
  event.preventDefault();
  event.stopPropagation();

  try {
    var element = document.elementFromPoint(event.clientX, event.clientY);
    callback(Simmer(element));
  } finally {
    removeAll();
  }
}

function cancelPick(event) {
  var evt = event || window.event;
  if (evt.key === 'Escape' || evt.keyCode === 27) {
    removeAll();
    callback();
  }
}

function removeAll() {
  document.body.removeChild(picker);
  document.removeEventListener('mousemove', highlightElement, true);
  document.removeEventListener('click', pickElement, true);
  document.removeEventListener('keydown', cancelPick, true);
  clearHighlight();
}

clearHighlight();

document.addEventListener('mousemove', highlightElement, true);
document.addEventListener('click', pickElement, true);
document.addEventListener('keydown', cancelPick, true);
document.body.appendChild(picker);

var node = document.createElement('style');

node.setAttribute('data-name', 'robocode');
node.innerHTML = `
[data-robocode-highlight] {
  outline: 2px solid #7158F1 !important;
  opacity: 1.0 !important;
}
#robocode-picker {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 9999;
  cursor: crosshair;
  pointer-events: none;
  box-shadow: inset 0px 0px 0px 5px #7158F1;
}
#robocode-picker::after {
  position: fixed;
  content: "Click element to select it";
  font-size: 16px;
  text-align: center;
  bottom: 0;
  left: 50%;
  width: 300px;
  margin-left: -150px;
  padding: 5px;
  color: white;
  background: #7158F1;
  opacity: 1.0;
}
`;

document.head.appendChild(node);

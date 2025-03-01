// static/js/common.js

/**
 * Show an alert message in a modal-style popup.
 * @param {string} message - The message to display.
 * @param {string} [type="info"] - The alert type ("info", "success", "error").
 * @param {number} [duration=3000] - How long (ms) to display the alert.
 */
function showAlert(message, type = "info", duration = 3000) {
    let container = document.getElementById("alert-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "alert-container";
      document.body.appendChild(container);
    }
    const alertDiv = document.createElement("div");
    alertDiv.className = "alert " + type;
    alertDiv.textContent = message;
    container.appendChild(alertDiv);
    setTimeout(() => {
      alertDiv.remove();
    }, duration);
  }
  
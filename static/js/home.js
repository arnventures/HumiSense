// static/js/home.js

let chart; // Chart.js instance
let currentMode = "Auto";
const modeMapping = {
  "Auto": { display: "AUTO", image: "/static/images/ss-short-left-3d.png" },
  "Hand": { display: "EIN", image: "/static/images/ss-short-right-3d.png" },
  "Aus": { display: "AUS", image: "/static/images/ss-short-mid-3d.png" }
};

function initChart() {
  const canvas = document.getElementById('myChart');
  if (!canvas) {
    console.error("Chart canvas element not found");
    showAlert("Chart canvas fehlt", "error");
    return;
  }
  const ctx = canvas.getContext('2d');
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'Inside Absolute Humidity',
          data: [],
          borderColor: 'rgba(75, 192, 192, 1)',
          fill: false
        },
        {
          label: 'Outside Absolute Humidity',
          data: [],
          borderColor: 'rgba(192, 75, 192, 1)',
          fill: false
        },
        {
          label: 'Difference',
          data: [],
          borderColor: 'rgba(192, 192, 75, 1)',
          fill: false
        }
      ]
    },
    options: {
      scales: {
        x: { title: { display: true, text: 'Time' } },
        y: { title: { display: true, text: 'Value' } }
      }
    }
  });
}

function updateChart() {
  fetch('/api/dashboard')
    .then(response => response.json())
    .then(data => {
      const timestamps = data.map(entry => new Date(entry.timestamp * 1000).toLocaleTimeString());
      const insideData = data.map(entry => entry.status.inside_absolute_humidity);
      const outsideData = data.map(entry => entry.status.outside_absolute_humidity);
      const diffData = data.map(entry => entry.status.difference);
      
      if (chart) {
        chart.data.labels = timestamps;
        chart.data.datasets[0].data = insideData;
        chart.data.datasets[1].data = outsideData;
        chart.data.datasets[2].data = diffData;
        chart.update();
      }
    })
    .catch(error => {
      console.error('Error updating chart:', error);
      showAlert("Fehler beim Laden der Grafikdaten", "error");
    });
}

function updateStatus() {
  fetch('/api/status')
    .then(response => response.json())
    .then(data => {
      let html = '<ul>';
      html += `<li><strong>Station:</strong> ${data.api_station_name || data.api_station || 'n.a.'}</li>`;
      html += `<li><strong>Relay:</strong> ${data.regulation_state || 'n.a.'}</li>`;
      html += `<li><strong>Temp (innen):</strong> ${data.local_temperature} °C</li>`;
      html += `<li><strong>Luftfeuchtigkeit (innen):</strong> ${data.local_humidity} %</li>`;
      html += `<li><strong>Inside AH:</strong> ${data.inside_absolute_humidity}</li>`;
      html += `<li><strong>Outside AH:</strong> ${data.outside_absolute_humidity || 'n.a.'}</li>`;
      html += `<li><strong>Diff:</strong> ${data.difference || 'n.a.'}</li>`;
      html += '</ul>';
      const statusDiv = document.getElementById('status-info');
      if (statusDiv) {
        statusDiv.innerHTML = html;
      } else {
        console.error("Status info element not found");
      }
    })
    .catch(error => {
      console.error('Error updating status:', error);
      // Spezifische Fehlermeldung anzeigen
      showAlert("ERROR:root:Error reading sensor: [Errno 121] Remote I/O error", "error");
    });
}


function updateVentilatorStatus() {
  fetch('/api/relay')
    .then(response => response.json())
    .then(data => {
      const ventImg = document.getElementById('ventImg');
      if (!ventImg) {
        console.error("Ventilator image element not found");
        return;
      }
      const relayState = data.relay_state ? data.relay_state.state : false;
      if (relayState) {
        ventImg.src = "/static/images/pl-green-srx-3d.png";
        ventImg.alt = "Ventilator EIN";
      } else {
        ventImg.src = "/static/images/pm-white-sr-3d.png";
        ventImg.alt = "Ventilator AUS";
      }
    })
    .catch(error => {
      console.error("Error updating ventilator status:", error);
      showAlert("Fehler beim Laden des Ventilator-Status", "error");
    });
}

function updateManualControlUI(mode) {
  const modeImg = document.getElementById('modeImgHome');
  const modeLabel = document.getElementById('modeLabelHome');
  if (!modeImg || !modeLabel) return;
  modeImg.src = modeMapping[mode].image;
  modeImg.alt = modeMapping[mode].display;
  modeLabel.textContent = "Aktueller Modus: " + modeMapping[mode].display;
}

function handleModeToggle() {
  if (currentMode === "Auto") {
    currentMode = "Hand";
  } else if (currentMode === "Hand") {
    currentMode = "Aus";
  } else {
    currentMode = "Auto";
  }
  updateManualControlUI(currentMode);
  fetch('/api/relay/mode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: currentMode })
  })
  .then(res => res.json())
  .then(data => console.log("Mode changed:", data))
  .catch(err => console.error("Error setting mode:", err));
}

function updateAll() {
  updateStatus();
  updateChart();
  updateVentilatorStatus();
}

function initHomePage() {
  initChart();
  updateAll();
  fetch('/api/config')
    .then(response => response.json())
    .then(cfg => {
      currentMode = cfg.relay_mode || "Auto";
      updateManualControlUI(currentMode);
      if (!cfg.manual_control_enabled) {
        const manualBox = document.getElementById('manualControlBox');
        if (manualBox) manualBox.style.display = "none";
      }
    })
    .catch(err => console.error("Error loading config:", err));
  
  const modeImg = document.getElementById('modeImgHome');
  if (modeImg) {
    modeImg.addEventListener('click', handleModeToggle);
  }
  setInterval(updateAll, 2000);
}

document.addEventListener('DOMContentLoaded', initHomePage);

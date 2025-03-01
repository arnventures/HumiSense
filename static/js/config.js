// static/js/config.js

function loadConfig() {
  fetch('/api/config')
    .then(res => res.json())
    .then(cfg => {
      if (cfg.api_station_id) {
        document.getElementById('api_station_select').value = cfg.api_station_id;
      }
      document.getElementById('log_file').value = cfg.logging.log_file;
      document.getElementById('api_poll_interval').value = cfg.regulation.api_poll_interval;
      document.getElementById('local_sensor_poll_interval').value = cfg.regulation.local_sensor_poll_interval;
      document.getElementById('max_on_time').value = cfg.regulation.max_on_time;
      document.getElementById('off_delay').value = cfg.regulation.off_delay;
      document.getElementById('off_threshold').value = cfg.regulation.off_threshold;
      document.getElementById('on_delay').value = cfg.regulation.on_delay;
      document.getElementById('on_threshold').value = cfg.regulation.on_threshold;
      if (typeof cfg.manual_control_enabled !== "undefined") {
        document.getElementById('manualControlToggle').checked = cfg.manual_control_enabled;
      }
    })
    .catch(err => {
      console.error("Error loading configuration:", err);
      showAlert("Fehler beim Laden der Konfiguration", "error");
    });
}

function saveConfig() {
  const config = {
    api_station_id: document.getElementById('api_station_select').value,
    regulation: {
      api_poll_interval: parseInt(document.getElementById('api_poll_interval').value),
      local_sensor_poll_interval: parseInt(document.getElementById('local_sensor_poll_interval').value),
      max_on_time: parseInt(document.getElementById('max_on_time').value),
      off_delay: parseInt(document.getElementById('off_delay').value),
      off_threshold: parseFloat(document.getElementById('off_threshold').value),
      on_delay: parseInt(document.getElementById('on_delay').value),
      on_threshold: parseFloat(document.getElementById('on_threshold').value)
    },
    logging: {
      log_file: document.getElementById('log_file').value
    },
    // relay_mode is now controlled via the home page
    relay_mode: "Auto",
    manual_control_enabled: document.getElementById('manualControlToggle').checked
  };

  fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  })
  .then(res => res.json())
  .then(data => {
    console.log("Configuration saved:", data);
    showAlert("Konfiguration gespeichert", "success");
  })
  .catch(err => {
    console.error("Error saving configuration:", err);
    showAlert("Fehler beim Speichern der Konfiguration", "error");
  });
}

function downloadConfig() {
  fetch('/api/config')
    .then(res => res.json())
    .then(data => {
      const jsonString = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonString], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'config.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    })
    .catch(err => {
      console.error("Error downloading configuration:", err);
      showAlert("Fehler beim Download der Konfiguration", "error");
    });
}

function handleUpload() {
  const uploadInput = document.getElementById('uploadConfigInput');
  if (!uploadInput) {
    console.error("Upload input element not found");
    showAlert("Upload-Eingabefeld fehlt", "error");
    return;
  }
  uploadInput.click();
}

const uploadInput = document.getElementById('uploadConfigInput');
if (uploadInput) {
  uploadInput.addEventListener('change', function (e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function (event) {
      try {
        const json = JSON.parse(event.target.result);
        fetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(json)
        })
          .then(res => res.json())
          .then(data => {
            console.log("Configuration uploaded:", data);
            showAlert("Konfiguration hochgeladen", "success");
            loadConfig();
          })
          .catch(err => {
            console.error("Error uploading configuration:", err);
            showAlert("Fehler beim Upload der Konfiguration", "error");
          });
      } catch (err) {
        console.error("Invalid JSON file:", err);
        showAlert("Ungültige JSON-Datei", "error");
      }
    };
    reader.readAsText(file);
  });
} else {
  console.error("Upload input element not found for event listener");
  showAlert("Upload-Eingabefeld fehlt", "error");
}

function loadStations() {
  fetch('/api/stations')
    .then(res => res.json())
    .then(data => {
      const select = document.getElementById('api_station_select');
      select.innerHTML = "";
      if (data.stations && data.stations.length > 0) {
        data.stations.forEach(station => {
          const option = document.createElement('option');
          option.value = station.id;
          option.textContent = `${station.station_name} (${station.id})`;
          select.appendChild(option);
        });
      } else {
        const option = document.createElement('option');
        option.value = "";
        option.textContent = "Keine Stationen gefunden";
        select.appendChild(option);
      }
    })
    .catch(err => {
      console.error("Error loading stations:", err);
      showAlert("Fehler beim Laden der Stationen", "error");
      const select = document.getElementById('api_station_select');
      select.innerHTML = "<option value=''>Fehler beim Laden</option>";
    });
}

function initConfigPage() {
  loadStations();
  loadConfig();
  const saveBtn = document.getElementById('saveConfigButton');
  if (saveBtn) {
    saveBtn.addEventListener('click', saveConfig);
  } else {
    console.error("Save Config button not found");
  }
  const downloadBtn = document.getElementById('downloadConfigButton');
  if (downloadBtn) {
    downloadBtn.addEventListener('click', downloadConfig);
  } else {
    console.error("Download Config button not found");
  }
  const uploadBtn = document.getElementById('uploadConfigButton');
  if (uploadBtn) {
    uploadBtn.addEventListener('click', handleUpload);
  } else {
    console.error("Upload Config button not found");
  }
}

document.addEventListener('DOMContentLoaded', initConfigPage);

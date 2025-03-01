// static/js/logs.js

/**
 * Fetch logs with given query parameters and display them in the log table.
 */
function fetchLogs(params) {
    const url = new URL(window.location.origin + "/api/logs");
    Object.keys(params).forEach(key => {
      if (params[key]) {
        url.searchParams.append(key, params[key]);
      }
    });
  
    fetch(url)
      .then(response => response.json())
      .then(data => {
        const tbody = document.getElementById("log-table").querySelector("tbody");
        tbody.innerHTML = "";  // Clear the table
        data.forEach(entry => {
          const tr = document.createElement("tr");
          const date = new Date(entry.timestamp * 1000);
          const formattedDate = date.toLocaleString();
          const event = entry.event || "";
          let details = "";
          if (entry.message) {
            details = entry.message;
          } else if (entry.status) {
            details = JSON.stringify(entry.status);
          }
          tr.innerHTML = `<td>${formattedDate}</td><td>${event}</td><td>${details}</td>`;
          tbody.appendChild(tr);
        });
      })
      .catch(error => {
        console.error("Error fetching logs:", error);
        showAlert("Fehler beim Laden der Logs", "error");
      });
  }
  
  /**
   * Initialize the Logs Page: set up form listener and initial fetch.
   */
  function initLogPage() {
    document.getElementById("filter-form").addEventListener("submit", function(e) {
      e.preventDefault();
      const start = document.getElementById("start").value;
      const end = document.getElementById("end").value;
      const event = document.getElementById("event").value;
      const startISO = start ? new Date(start).toISOString() : "";
      const endISO = end ? new Date(end).toISOString() : "";
      fetchLogs({ start: startISO, end: endISO, event: event, limit: 100 });
    });
    // Initial fetch
    fetchLogs({ limit: 100 });
  }
  
  document.addEventListener("DOMContentLoaded", initLogPage);
  
import { user } from "../../shared/auth.js";
import { api, fmtDate, minutes } from "../../shared/utils.js";
import { refreshOnLive } from "../../shared/websocket.js";

async function load() {
  const sessionUser = user();
  const employeeId = sessionUser?.employee_id;
  const statuses = await api(`/api/v2/agent/status?employee_id=${encodeURIComponent(employeeId)}`);
  const events = await api(`/api/v2/events?employee_id=${encodeURIComponent(employeeId)}`);
  const status = statuses[0] || {};
  document.querySelector("#statusGrid").innerHTML = `
    <article><strong>${status.connection_status || "OFFLINE"}</strong><span>Agent Status</span></article>
    <article><strong>${status.current_status || "OFFLINE"}</strong><span>Current State</span></article>
    <article><strong>${fmtDate(status.last_heartbeat_at)}</strong><span>Last Heartbeat</span></article>
  `;
  document.querySelector("#eventRows").innerHTML = events.map((item) => `
    <tr><td>${item.event_type}</td><td>${fmtDate(item.event_timestamp)}</td><td>${item.source}</td></tr>
  `).join("");
}

document.querySelectorAll("[data-event]").forEach((button) => {
  button.addEventListener("click", async () => {
    const sessionUser = user();
    await api("/api/v2/events", {
      method: "POST",
      body: JSON.stringify({
        employee_id: sessionUser.employee_id,
        event_type: button.dataset.event,
        event_timestamp: new Date().toISOString(),
        source: "web"
      })
    });
    await load();
  });
});

await load();
await refreshOnLive(load);

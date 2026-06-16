import { fmtDate, minutes, api } from "../../shared/utils.js";
import { refreshOnLive } from "../../shared/websocket.js";


async function load() {
  const rows = await api("/api/v2/manager/live");
  document.querySelector("#liveRows").innerHTML = rows.map((row) => `
    <tr>
      <td>${row.employee_name}</td>
      <td>${row.current_status}</td>
      <td>${row.connection_status}</td>
      <td>${fmtDate(row.last_heartbeat_at)}</td>
      <td>${minutes(row.locked_minutes)}</td>
      <td>${minutes(row.productive_minutes)}</td>
      <td>${row.productivity_score}%</td>
    </tr>
  `).join("");
}

await load();
await refreshOnLive(load);

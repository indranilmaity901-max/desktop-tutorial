import { api } from "../../shared/utils.js";


const rows = await api("/api/v2/admin/users");
document.querySelector("#userRows").innerHTML = rows.map((row) => `
  <tr>
    <td>${row.username}</td>
    <td>${row.role_name}</td>
    <td>${row.employee_id || ""}</td>
    <td>${row.active ? "ACTIVE" : "INACTIVE"}</td>
  </tr>
`).join("");

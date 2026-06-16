const state = {
  user: null,
  loading: true,
  error: "",
  dashboard: { metrics: {}, trend: [] },
  employees: [],
  attendance: [],
  productivity: [],
  reports: [],
  roles: [],
  users: [],
  managers: [],
  employeeOptions: [],
  agentDashboard: null,
  agentStatuses: [],
  dailyProductivity: [],
  agentEvents: [],
  selectedAgentId: "",
  liveSocket: null
};

function icon(name) {
  return `<i data-lucide="${name}" aria-hidden="true"></i>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDateTime(value) {
  return value ? new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value)) : "No event";
}

function minutesLabel(value) {
  const minutes = Number(value || 0);
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return hours ? `${hours}h ${String(remainder).padStart(2, "0")}m` : `${remainder}m`;
}

function selectedAgentId() {
  return state.user?.employee_id || state.selectedAgentId || state.employeeOptions[0]?.employee_id || "";
}

function currentStateLabel(status) {
  if (status?.current_status === "LOCKED") {
    return "LOCKED";
  }
  if (status?.shift_state === "ACTIVE") {
    return "ACTIVE";
  }
  return "IDLE";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  if (response.status === 204) {
    return {};
  }
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    throw new Error(payload.message || "Request failed");
  }
  return payload.data ?? {};
}

function sidebar() {
  const role = state.user?.role || "";
  const operationItems = [
    ["monitor-dot", "Agent", "#agent"],
    ["activity", "Productivity", "#productivity"],
    ["file-bar-chart", "Reports", "#reports"]
  ];
  const groups = [
    { title: "WPACS", items: [["radar", "Dashboard", "#dashboard", true]] },
    ...(role === "ADMIN" || role === "MANAGER"
      ? [{ title: "Workforce", items: [["users", "Employees", "#employees"], ["calendar-check", "Attendance", "#attendance"]] }]
      : [{ title: "Workforce", items: [["calendar-check", "Attendance", "#attendance"]] }]),
    { title: "Operations", items: operationItems },
    ...(role === "ADMIN"
      ? [{ title: "Administration", items: [["user-cog", "Users", "#users"]] }]
      : [])
  ];

  return `
    <aside class="sidebar" aria-label="Main navigation">
      <div class="brand">
        <div class="brand-mark">W</div>
        <div>
          <strong>WPACS</strong>
          <span>RBAC dashboard</span>
        </div>
      </div>
      <nav class="nav-list">
        ${groups.map((group) => `
          <div class="nav-group">
            <p>${group.title}</p>
            ${group.items.map(([itemIcon, label, href, active]) => `
              <a class="nav-item ${active ? "active" : ""}" href="${href}">
                ${icon(itemIcon)}
                <span>${label}</span>
              </a>
            `).join("")}
          </div>
        `).join("")}
      </nav>
    </aside>
  `;
}

function topbar() {
  const titles = {
    ADMIN: "WPACS Admin Dashboard",
    MANAGER: "WPACS Manager Dashboard",
    SUPERVISOR: "WPACS Supervisor Dashboard"
  };
  return `
    <header class="topbar">
      <div>
        <p class="eyebrow">${escapeHtml(state.user?.role || "WPACS")}</p>
        <h1>${titles[state.user?.role] || "WPACS Dashboard"}</h1>
      </div>
      <div class="topbar-actions">
        <span class="session-role">${escapeHtml(state.user?.role || "")}</span>
        <button class="text-button" id="logoutButton" type="button">${icon("log-out")} Logout</button>
      </div>
    </header>
  `;
}

function metricCard(label, value, detail, href) {
  return `
    <a class="metric-panel" href="${href}">
      <div class="metric-topline">
        <span class="metric-label">${label}</span>
        <span class="trend neutral">Live</span>
      </div>
      <strong>${escapeHtml(value)}</strong>
      <div class="evidence-list"><span>${escapeHtml(detail)}</span></div>
    </a>
  `;
}

function emptyState(text = "No records available.") {
  return `<div class="empty-state">${escapeHtml(text)}</div>`;
}

function onboardingState() {
  return emptyState("No PostgreSQL employee records found.");
}

function loginPage() {
  return `
    <main class="login-page">
      <section class="login-hero" aria-label="WPACS access">
        <header class="login-brand-row">
          <div class="brand large">
            <div class="brand-mark">W</div>
            <div>
              <strong>WPACS</strong>
              <span>Workforce Productivity & Activity Correlation</span>
            </div>
          </div>
          <div class="security-pill">${icon("shield-check")} Secured</div>
        </header>
        <div class="identity-message">
          <p class="eyebrow">Identity Gateway</p>
          <h1>Secure access for WPACS V1.</h1>
          <p>Sign in to open manager dashboard data.</p>
        </div>
      </section>
      <section class="login-panel-shell" aria-label="Login form">
        <form class="login-panel" id="loginForm">
          <div class="login-panel-header">
            <div class="login-lock">${icon("lock-keyhole")}</div>
            <div>
              <p class="eyebrow">Identity Gateway</p>
              <h2>Sign in to WPACS</h2>
            </div>
          </div>
          <label>
            <span>Role</span>
            <select name="role" required>
              <option value="ADMIN">ADMIN</option>
              <option value="MANAGER">MANAGER</option>
              <option value="SUPERVISOR">SUPERVISOR</option>
            </select>
          </label>
          <label>
            <span>Username</span>
            <input name="username" autocomplete="username" required>
          </label>
          <label>
            <span>Password</span>
            <input name="password_hash" autocomplete="current-password" type="password" required>
          </label>
          <button type="submit">${icon("log-in")} Authenticate</button>
          <div class="login-result" id="loginResult"></div>
        </form>
      </section>
    </main>
  `;
}

function dashboardShell(content) {
  return `
    <div class="app-shell">
      ${sidebar()}
      <main class="workspace">
        ${topbar()}
        ${state.error ? `<section class="panel wide">${escapeHtml(state.error)}</section>` : ""}
        ${content}
      </main>
    </div>
  `;
}

function managerDashboard() {
  const metrics = state.dashboard.metrics || {};
  const productivityMetric = metrics.productivity_records > 0 ? `${metrics.productivity_score}%` : "Awaiting data";
  const role = state.user?.role || "";
  const canManageEmployees = role === "ADMIN" || role === "MANAGER";
  const canManageUsers = role === "ADMIN";
  return dashboardShell(`
    <section class="kpi-grid" id="dashboard" aria-label="Manager KPIs">
      ${metricCard("Employees", metrics.employees || 0, "Live employee records", "#employees")}
      ${metricCard("Productivity Score", productivityMetric, "Average productivity", "#productivity")}
      ${metricCard("Attendance Records", metrics.attendance_records || 0, "Attendance rows", "#attendance")}
      ${metricCard("Reports", state.reports.length, "Generated reports", "#reports")}
    </section>
    <div class="content-grid">
      ${state.user?.employee_id ? agentDashboardPanel() : ""}
      ${role === "MANAGER" || role === "ADMIN" || role === "SUPERVISOR" ? managerLivePanel() : ""}
      ${canManageEmployees ? employeesPanel() : ""}
      ${attendancePanel()}
      ${productivityPanel()}
      ${reportsPanel()}
      ${canManageUsers ? usersPanel() : ""}
    </div>
  `);
}

function agentDashboardPanel() {
  const status = state.agentDashboard?.status || {};
  const productivity = state.agentDashboard?.productivity || {};
  const attendance = state.agentDashboard?.attendance || [];
  const activeAgentId = selectedAgentId();
  const canPostShift = state.user?.role !== "SUPERVISOR" && Boolean(activeAgentId);
  const agentOptions = state.employeeOptions.map((employee) => `
    <option value="${escapeHtml(employee.employee_id)}" ${employee.employee_id === activeAgentId ? "selected" : ""}>
      ${escapeHtml(employee.employee_name)} (${escapeHtml(employee.employee_id)})
    </option>
  `).join("");
  return `
    <section class="panel wide agent-dashboard-panel" id="agent">
      <div class="panel-header">
        <div>
          <h2>Agent Dashboard</h2>
          <p>Current shift state from PostgreSQL workstation events.</p>
        </div>
        <span class="state">${escapeHtml(status.connection_status || "OFFLINE")}</span>
      </div>
      ${state.user?.employee_id ? "" : `
        <label class="agent-selector">
          <span>Agent</span>
          <select id="agentSelector" ${state.employeeOptions.length ? "" : "disabled"}>
            ${agentOptions || `<option value="">No scoped employees</option>`}
          </select>
        </label>
      `}
      <div class="agent-dashboard-kpis">
        <article class="agent-kpi-card"><span>Agent Status</span><strong>${escapeHtml(status.connection_status || "OFFLINE")}</strong></article>
        <article class="agent-kpi-card"><span>Current State</span><strong>${escapeHtml(currentStateLabel(status))}</strong></article>
        <article class="agent-kpi-card"><span>Today's Attendance</span><strong>${attendance.length ? escapeHtml(attendance[0].status) : "No record"}</strong></article>
        <article class="agent-kpi-card"><span>Last Heartbeat</span><strong>${formatDateTime(status.last_heartbeat_at)}</strong></article>
      </div>
      <div class="agent-shift-actions">
        <button type="button" data-agent-event="SHIFT_START" ${canPostShift ? "" : "disabled"}>${icon("play")} Start Shift</button>
        <button type="button" data-agent-event="SHIFT_END" ${canPostShift ? "" : "disabled"}>${icon("square")} End Shift</button>
        <button type="button" data-agent-event="HEARTBEAT" ${canPostShift ? "" : "disabled"}>${icon("radio")} Heartbeat</button>
      </div>
      <div class="agent-dashboard-grid compact">
        <article class="agent-inner-panel">
          <span>Connection Status</span>
          <strong>${escapeHtml(status.connection_status || "OFFLINE")}</strong>
          <small>Last activity: ${formatDateTime(status.last_activity_at)}</small>
        </article>
        <article class="agent-inner-panel">
          <span>Productive Time</span>
          <strong>${minutesLabel(productivity.productive_minutes)}</strong>
          <small>Locked time: ${minutesLabel(productivity.locked_minutes)}</small>
        </article>
        <article class="agent-inner-panel">
          <span>Productivity %</span>
          <strong>${escapeHtml(productivity.productivity_score ?? 0)}%</strong>
          <small>Shift state: ${escapeHtml(status.shift_state || "NOT_STARTED")}</small>
        </article>
      </div>
      <div class="agent-event-feed">
        <div class="panel-header compact">
          <div>
            <h3>Live Event Feed</h3>
            <p>Recent workstation events from PostgreSQL.</p>
          </div>
        </div>
        ${state.agentEvents.length ? `
          <div class="event-feed-list">
            ${state.agentEvents.map((event) => `
              <article>
                <strong>${escapeHtml(event.event_type)}</strong>
                <span>${escapeHtml(event.employee_name || event.employee_id)} · ${formatDateTime(event.event_timestamp)}</span>
                <small>${escapeHtml(event.source)}</small>
              </article>
            `).join("")}
          </div>
        ` : emptyState("No workstation events found.")}
      </div>
    </section>
  `;
}

function managerLivePanel() {
  const todayByEmployee = new Map(state.dailyProductivity.map((row) => [row.employee_id, row]));
  return `
    <section class="panel wide" id="live-monitoring">
      <div class="panel-header">
        <div>
          <h2>Live Monitoring</h2>
          <p>Scoped employee status and productivity from PostgreSQL.</p>
        </div>
      </div>
      ${state.agentStatuses.length ? `
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Assigned Employee</th>
                <th>Current Status</th>
                <th>Last Activity</th>
                <th>Shift State</th>
                <th>Productive</th>
                <th>Non-Productive</th>
              </tr>
            </thead>
            <tbody>
              ${state.agentStatuses.map((agent) => {
                const productivity = todayByEmployee.get(agent.employee_id) || {};
                const nonProductive = Number(productivity.locked_minutes || 0) + Number(productivity.logged_out_minutes || 0);
                return `
                  <tr>
                    <td><strong>${escapeHtml(agent.employee_name)}</strong><br><small>${escapeHtml(agent.employee_id)}</small></td>
                    <td><span class="state">${escapeHtml(agent.current_status)}</span></td>
                    <td>${formatDateTime(agent.last_activity_at)}</td>
                    <td>${escapeHtml(agent.shift_state)}</td>
                    <td>${minutesLabel(productivity.productive_minutes)}</td>
                    <td>${minutesLabel(nonProductive)}</td>
                  </tr>
                `;
              }).join("")}
            </tbody>
          </table>
        </div>
      ` : emptyState("No assigned employee status records found.")}
    </section>
  `;
}

function employeesPanel() {
  const managerOptions = state.managers.map((manager) => `
    <option value="${escapeHtml(manager.manager_id)}">${escapeHtml(manager.manager_name)}</option>
  `).join("");
  return `
    <section class="panel wide" id="employees">
      <div class="panel-header">
        <div>
          <h2>Employees</h2>
          <p>Live employee records from PostgreSQL.</p>
        </div>
      </div>
      <form class="employee-form" id="employeeForm" data-editing-id="">
        <input name="employee_id" required aria-label="Employee ID">
        <input name="employee_name" required aria-label="Employee name">
        <input name="department" required aria-label="Department">
        <select name="manager_id" aria-label="Manager">
          <option value="">Assign Manager</option>
          ${managerOptions}
        </select>
        <select name="status" required aria-label="Status">
          <option value="ACTIVE">ACTIVE</option>
          <option value="INACTIVE">INACTIVE</option>
        </select>
        <button type="submit">${icon("user-plus")} Save Employee</button>
      </form>
      ${state.employees.length ? `
        <div class="table-wrap">
          <table>
            <thead><tr><th>Employee</th><th>Department</th><th>Manager</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              ${state.employees.map((employee) => `
                <tr>
                  <td><strong>${escapeHtml(employee.employee_name)}</strong><br><small>${escapeHtml(employee.employee_id)}</small></td>
                  <td>${escapeHtml(employee.department)}</td>
                  <td>${escapeHtml(employee.manager_name || "Unassigned")}</td>
                  <td><span class="state">${escapeHtml(employee.status)}</span></td>
                  <td>
                    <button class="text-button" type="button" data-edit-employee="${escapeHtml(employee.employee_id)}">${icon("pencil")} Edit</button>
                    <button class="text-button danger" type="button" data-delete-employee="${escapeHtml(employee.employee_id)}">${icon("trash-2")} Delete</button>
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      ` : onboardingState()}
    </section>
  `;
}

function attendancePanel(records = state.attendance) {
  const employeeOptions = state.employeeOptions.map((employee) => `
    <option value="${escapeHtml(employee.employee_id)}">${escapeHtml(employee.employee_name)} (${escapeHtml(employee.employee_id)})</option>
  `).join("");
  return `
    <section class="panel wide" id="attendance">
      <div class="panel-header">
        <div>
          <h2>Attendance</h2>
          <p>Live attendance records from PostgreSQL.</p>
        </div>
      </div>
      ${state.employeeOptions.length ? `
        <form class="employee-form" id="attendanceForm">
          <select name="employee_id" required aria-label="Employee">
            <option value="">Select Employee</option>
            ${employeeOptions}
          </select>
          <input name="attendance_date" type="date" required aria-label="Attendance date">
          <select name="status" required aria-label="Attendance status">
            <option value="PRESENT">PRESENT</option>
            <option value="ABSENT">ABSENT</option>
            <option value="INACTIVE">INACTIVE</option>
          </select>
          <input name="worked_hours" type="number" step="0.25" min="0" required aria-label="Worked hours">
          <button type="submit">${icon("calendar-plus")} Mark Attendance</button>
        </form>
      ` : emptyState("No employees available. Create an employee first.")}
      ${records.length ? `
        <div class="table-wrap">
          <table>
            <thead><tr><th>Employee</th><th>Date</th><th>Status</th><th>Worked Hours</th></tr></thead>
            <tbody>
              ${records.map((record) => `
                <tr>
                  <td><strong>${escapeHtml(record.employee_name || record.employee_id)}</strong><br><small>${escapeHtml(record.employee_id)}</small></td>
                  <td>${escapeHtml(record.attendance_date)}</td>
                  <td><span class="state">${escapeHtml(record.status)}</span></td>
                  <td>${escapeHtml(record.worked_hours)}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      ` : emptyState("No attendance records found.")}
    </section>
  `;
}

function productivityPanel(records = state.productivity) {
  return `
    <section class="panel wide" id="productivity">
      <div class="panel-header">
        <div>
          <h2>Productivity</h2>
          <p>Live productivity records from PostgreSQL.</p>
        </div>
      </div>
      ${records.length ? `
        <div class="table-wrap">
          <table>
            <thead><tr><th>Employee</th><th>Date</th><th>Productive</th><th>Non-Productive</th><th>Score</th></tr></thead>
            <tbody>
              ${records.map((record) => `
                <tr>
                  <td><strong>${escapeHtml(record.employee_name || record.employee_id)}</strong><br><small>${escapeHtml(record.employee_id)}</small></td>
                  <td>${escapeHtml(record.report_date)}</td>
                  <td>${escapeHtml(record.productive_hours)}</td>
                  <td>${escapeHtml(record.non_productive_hours)}</td>
                  <td><strong>${escapeHtml(record.productivity_score)}%</strong></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      ` : emptyState("Awaiting productivity data.")}
    </section>
  `;
}

function reportsPanel() {
  return `
    <section class="panel wide" id="reports">
      <div class="panel-header">
        <div>
          <h2>Reports</h2>
          <p>Generated report records.</p>
        </div>
      </div>
      <form class="report-download-form" id="reportForm">
        <input name="report_name" required aria-label="Report name">
        <select name="report_type" required aria-label="Report type">
          <option value="attendance">Attendance</option>
          <option value="productivity">Productivity</option>
        </select>
        <button type="submit">${icon("file-bar-chart")} Generate</button>
      </form>
      ${state.reports.length ? `
        <div class="table-wrap">
          <table>
            <thead><tr><th>Report</th><th>Type</th><th>Generated</th></tr></thead>
            <tbody>
              ${state.reports.map((report) => `
                <tr>
                  <td>${escapeHtml(report.report_name)}</td>
                  <td>${escapeHtml(report.report_type)}</td>
                  <td>${escapeHtml(report.generated_at)}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      ` : emptyState("No report records found.")}
    </section>
  `;
}

function usersPanel() {
  return `
    <section class="panel wide" id="users">
      <div class="panel-header">
        <div>
          <h2>Users</h2>
          <p>Admin-only create, edit, disable, reset password, and assign role.</p>
        </div>
      </div>
      <form class="employee-form" id="userForm">
        <input name="username" required aria-label="Username">
        <input name="password" type="password" aria-label="New or reset password">
        <select name="role_name" required aria-label="Role">
          ${state.roles.map((role) => `<option value="${escapeHtml(role.role_name)}">${escapeHtml(role.role_name)}</option>`).join("")}
        </select>
        <input name="employee_id" aria-label="Employee ID for agent account">
        <select name="active" required aria-label="Active">
          <option value="true">ACTIVE</option>
          <option value="false">INACTIVE</option>
        </select>
        <button type="submit">${icon("user-plus")} Save User</button>
      </form>
      ${state.users.length ? `
        <div class="table-wrap">
          <table>
            <thead><tr><th>Username</th><th>Role</th><th>Employee</th><th>Status</th></tr></thead>
            <tbody>
              ${state.users.map((user) => `
                <tr>
                  <td><strong>${escapeHtml(user.username)}</strong></td>
                  <td>${escapeHtml(user.role_name)}</td>
                  <td>${escapeHtml(user.employee_id || "")}</td>
                  <td><span class="state">${user.active ? "ACTIVE" : "INACTIVE"}</span></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      ` : emptyState("No user accounts found.")}
    </section>
  `;
}

function render() {
  document.querySelector("#app").innerHTML = state.loading
    ? `<main class="login-page"><section class="login-panel-shell"><div class="login-panel">Loading WPACS...</div></section></main>`
    : state.user
      ? managerDashboard()
      : loginPage();
  if (window.lucide) {
    window.lucide.createIcons();
  }
  attachHandlers();
}

function attachHandlers() {
  const loginForm = document.querySelector("#loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const result = document.querySelector("#loginResult");
      const formData = new FormData(loginForm);
      try {
        state.user = await api("/api/v1/auth/login", {
          method: "POST",
          body: JSON.stringify({
            username: formData.get("username"),
            password_hash: formData.get("password_hash"),
            role: formData.get("role")
          })
        });
        await loadData();
      } catch (error) {
        result.textContent = error.message;
      }
    });
  }

  const logoutButton = document.querySelector("#logoutButton");
  if (logoutButton) {
    logoutButton.addEventListener("click", async () => {
      await api("/api/v1/auth/logout", { method: "POST" }).catch(() => {});
      closeLiveSocket();
      state.user = null;
      render();
    });
  }

  const reportForm = document.querySelector("#reportForm");
  if (reportForm) {
    reportForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(reportForm);
      await api("/api/v1/reports", {
        method: "POST",
        body: JSON.stringify({
          report_name: formData.get("report_name"),
          report_type: formData.get("report_type")
        })
      });
      await loadData();
    });
  }

  const employeeForm = document.querySelector("#employeeForm");
  if (employeeForm) {
    employeeForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(employeeForm);
      const editingId = employeeForm.dataset.editingId;
      await api(editingId ? `/api/v1/employees/${encodeURIComponent(editingId)}` : "/api/v1/employees", {
        method: editingId ? "PUT" : "POST",
        body: JSON.stringify({
          employee_id: formData.get("employee_id"),
          employee_name: formData.get("employee_name"),
          department: formData.get("department"),
          manager_id: formData.get("manager_id"),
          status: formData.get("status")
        })
      });
      await loadData();
    });
  }

  document.querySelectorAll("[data-edit-employee]").forEach((button) => {
    button.addEventListener("click", () => {
      const employee = state.employees.find((item) => item.employee_id === button.dataset.editEmployee);
      const form = document.querySelector("#employeeForm");
      if (!employee || !form) {
        return;
      }
      form.dataset.editingId = employee.employee_id;
      form.elements.employee_id.value = employee.employee_id;
      form.elements.employee_id.readOnly = true;
      form.elements.employee_name.value = employee.employee_name;
      form.elements.department.value = employee.department;
      form.elements.manager_id.value = employee.manager_id || "";
      form.elements.status.value = employee.status || "ACTIVE";
      form.querySelector("button[type='submit']").innerHTML = `${icon("save")} Update Employee`;
      if (window.lucide) {
        window.lucide.createIcons();
      }
      form.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  });

  document.querySelectorAll("[data-delete-employee]").forEach((button) => {
    button.addEventListener("click", async () => {
      const employeeId = button.dataset.deleteEmployee;
      await api(`/api/v1/employees/${encodeURIComponent(employeeId)}`, { method: "DELETE" });
      await loadData();
    });
  });

  const attendanceForm = document.querySelector("#attendanceForm");
  if (attendanceForm) {
    attendanceForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(attendanceForm);
      await api("/api/v1/attendance", {
        method: "POST",
        body: JSON.stringify({
          employee_id: formData.get("employee_id"),
          attendance_date: formData.get("attendance_date"),
          status: formData.get("status"),
          worked_hours: formData.get("worked_hours")
        })
      });
      await loadData();
    });
  }

  const agentSelector = document.querySelector("#agentSelector");
  if (agentSelector) {
    agentSelector.addEventListener("change", async () => {
      state.selectedAgentId = agentSelector.value;
      await loadData();
    });
  }

  document.querySelectorAll("[data-agent-event]").forEach((button) => {
    button.addEventListener("click", async () => {
      await api("/api/v2/events", {
        method: "POST",
        body: JSON.stringify({
          employee_id: selectedAgentId(),
          event_type: button.dataset.agentEvent,
          event_timestamp: new Date().toISOString(),
          source: "web"
        })
      });
      await loadData();
    });
  });

  const userForm = document.querySelector("#userForm");
  if (userForm) {
    userForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(userForm);
      await api("/api/v1/users", {
        method: "POST",
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
          role_name: formData.get("role_name"),
          employee_id: formData.get("employee_id"),
          active: formData.get("active") === "true"
        })
      });
      await loadData();
    });
  }
}

function closeLiveSocket() {
  if (state.liveSocket) {
    state.liveSocket.onclose = null;
    state.liveSocket.close();
    state.liveSocket = null;
  }
}

function connectLiveSocket() {
  if (!state.user || state.liveSocket) {
    return;
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${window.location.host}/api/v2/live`);
  state.liveSocket = socket;
  socket.onmessage = async (event) => {
    const message = JSON.parse(event.data || "{}");
    if (["agent_status", "attendance", "productivity", "workstation_event"].includes(message.type)) {
      await loadData({ keepSocket: true });
    }
  };
  socket.onclose = () => {
    state.liveSocket = null;
    if (state.user) {
      window.setTimeout(connectLiveSocket, 3000);
    }
  };
}

async function loadData(options = {}) {
  state.error = "";
  try {
    const role = state.user?.role || "";
    state.dashboard = await api("/api/v1/dashboard");
    state.employees = role === "ADMIN" || role === "MANAGER" ? await api("/api/v1/employees") : [];
    state.employeeOptions = await api("/api/v1/employee-options");
    state.managers = role === "ADMIN" || role === "MANAGER" ? await api("/api/v1/managers") : [];
    state.attendance = await api("/api/v1/attendance");
    state.productivity = await api("/api/v1/productivity");
    state.reports = await api("/api/v1/reports");
    state.roles = role === "ADMIN" ? await api("/api/v1/roles") : [];
    state.users = role === "ADMIN" ? await api("/api/v1/users") : [];
    state.agentStatuses = await api("/api/v2/agent-status");
    state.dailyProductivity = await api(`/api/v2/productivity?date=${new Date().toISOString().slice(0, 10)}`);
    if (!state.selectedAgentId && !state.user?.employee_id) {
      state.selectedAgentId = state.employeeOptions[0]?.employee_id || "";
    }
    const agentId = selectedAgentId();
    state.agentDashboard = agentId ? await api(`/api/v2/agent-dashboard?employee_id=${encodeURIComponent(agentId)}`) : null;
    state.agentEvents = agentId ? await api(`/api/v2/events?employee_id=${encodeURIComponent(agentId)}`) : [];
    if (!options.keepSocket) {
      connectLiveSocket();
    }
  } catch (error) {
    state.error = error.message;
  } finally {
    state.loading = false;
    render();
  }
}

async function boot() {
  try {
    state.user = await api("/api/v1/auth/me");
  } catch {
    state.user = null;
  }
  if (state.user) {
    await loadData();
  } else {
    state.loading = false;
    render();
  }
}

boot();

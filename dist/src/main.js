const state = {
  user: null,
  loading: true,
  error: "",
  dashboard: { metrics: {}, trend: [] },
  employees: [],
  attendance: [],
  productivity: [],
  reports: [],
  agentProfile: {},
  heartbeat: readHeartbeat()
};

const appSurface = getAppSurface();

function getAppSurface() {
  const hostname = window.location.hostname.toLowerCase();
  if (hostname === "agent.wpacs.com" || window.location.port === "4191") {
    return "agent";
  }
  return "manager";
}

function isAgentSurface() {
  return appSurface === "agent";
}

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

function readHeartbeat() {
  const now = Date.now();
  const stored = JSON.parse(sessionStorage.getItem("wpacsHeartbeat") || "null");
  return stored?.loginAt
    ? stored
    : { loginAt: now, lastHeartbeatAt: now, lockoutAt: now + 8 * 60 * 60 * 1000 };
}

function saveHeartbeat() {
  sessionStorage.setItem("wpacsHeartbeat", JSON.stringify(state.heartbeat));
}

function formatTime(value) {
  return new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(value));
}

function formatDuration(milliseconds) {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return hours > 0
    ? `${hours}h ${String(minutes).padStart(2, "0")}m ${String(seconds).padStart(2, "0")}s`
    : `${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

function heartbeatStatus() {
  const now = Date.now();
  return {
    loginAt: formatTime(state.heartbeat.loginAt),
    lastHeartbeatAt: formatTime(state.heartbeat.lastHeartbeatAt),
    lockoutAt: formatTime(state.heartbeat.lockoutAt),
    timeToLockout: formatDuration(state.heartbeat.lockoutAt - now),
    lockedOut: now >= state.heartbeat.lockoutAt
  };
}

function updateHeartbeatPanel() {
  if (!state.user) {
    return;
  }
  state.heartbeat.lastHeartbeatAt = Date.now();
  saveHeartbeat();
  const status = heartbeatStatus();
  document.querySelectorAll("[data-heartbeat-field]").forEach((node) => {
    node.textContent = status[node.dataset.heartbeatField] || "";
  });
  const badge = document.querySelector("[data-heartbeat-status]");
  if (badge) {
    badge.textContent = status.lockedOut ? "LOCKOUT DUE" : "HEARTBEAT LIVE";
    badge.classList.toggle("warning", status.lockedOut);
  }
}

window.setInterval(updateHeartbeatPanel, 1000);

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
  const groups = isAgentSurface()
    ? [{ title: "WPACS Agent", items: [["monitor-dot", "Agent Dashboard", "#agent-dashboard", true]] }]
    : [
        { title: "WPACS Manager", items: [["radar", "Manager Dashboard", "#manager-dashboard", true]] },
        { title: "Workforce", items: [["users", "Employees", "#employees"], ["calendar-check", "Attendance", "#attendance"]] },
        { title: "Operations", items: [["activity", "Productivity", "#productivity"], ["file-bar-chart", "Reports", "#reports"]] }
      ];

  return `
    <aside class="sidebar" aria-label="Main navigation">
      <div class="brand">
        <div class="brand-mark">W</div>
        <div>
          <strong>WPACS</strong>
          <span>${isAgentSurface() ? "Agent dashboard" : "Manager dashboard"}</span>
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
  return `
    <header class="topbar">
      <div>
        <p class="eyebrow">${isAgentSurface() ? "Agent" : "Manager"}</p>
        <h1>${isAgentSurface() ? "WPACS Agent Dashboard" : "WPACS Manager Dashboard"}</h1>
      </div>
      <div class="topbar-actions">
        <span class="session-role">${escapeHtml(state.user?.role_name || "")}</span>
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

function emptyState(text = "No employee records found.") {
  return `<div class="empty-state">${escapeHtml(text)}</div>`;
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
          <p>Sign in to open ${isAgentSurface() ? "agent" : "manager"} dashboard data.</p>
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
  return dashboardShell(`
    <section class="kpi-grid" aria-label="Manager KPIs">
      ${metricCard("Employees", metrics.employees || 0, "Live employee records", "#employees")}
      ${metricCard("Productivity Score", `${metrics.productivity_score || 0}%`, "Average productivity", "#productivity")}
      ${metricCard("Attendance Records", metrics.attendance_records || 0, "Attendance rows", "#attendance")}
      ${metricCard("Reports", state.reports.length, "Generated reports", "#reports")}
    </section>
    <div class="content-grid">
      ${employeesPanel()}
      ${attendancePanel()}
      ${productivityPanel()}
      ${reportsPanel()}
    </div>
  `);
}

function employeesPanel() {
  return `
    <section class="panel wide" id="employees">
      <div class="panel-header">
        <div>
          <h2>Employees</h2>
          <p>Live employee records from PostgreSQL.</p>
        </div>
      </div>
      <form class="employee-form" id="employeeForm">
        <input name="employee_id" required aria-label="Employee ID">
        <input name="employee_name" required aria-label="Employee name">
        <input name="department" required aria-label="Department">
        <input name="manager_id" aria-label="Manager ID">
        <select name="status" required aria-label="Status">
          <option value="ACTIVE">ACTIVE</option>
          <option value="INACTIVE">INACTIVE</option>
        </select>
        <button type="submit">${icon("user-plus")} Save Employee</button>
      </form>
      ${state.employees.length ? `
        <div class="table-wrap">
          <table>
            <thead><tr><th>Employee</th><th>Department</th><th>Manager</th><th>Status</th></tr></thead>
            <tbody>
              ${state.employees.map((employee) => `
                <tr>
                  <td><strong>${escapeHtml(employee.employee_name)}</strong><br><small>${escapeHtml(employee.employee_id)}</small></td>
                  <td>${escapeHtml(employee.department)}</td>
                  <td>${escapeHtml(employee.manager_id || "")}</td>
                  <td><span class="state">${escapeHtml(employee.status)}</span></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      ` : emptyState()}
    </section>
  `;
}

function attendancePanel(records = state.attendance) {
  return `
    <section class="panel wide" id="attendance">
      <div class="panel-header">
        <div>
          <h2>Attendance</h2>
          <p>Live attendance records from PostgreSQL.</p>
        </div>
      </div>
      ${records.length ? `
        <div class="table-wrap">
          <table>
            <thead><tr><th>Employee</th><th>Date</th><th>Status</th><th>Worked Hours</th></tr></thead>
            <tbody>
              ${records.map((record) => `
                <tr>
                  <td>${escapeHtml(record.employee_id)}</td>
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
                  <td>${escapeHtml(record.employee_id)}</td>
                  <td>${escapeHtml(record.report_date)}</td>
                  <td>${escapeHtml(record.productive_hours)}</td>
                  <td>${escapeHtml(record.non_productive_hours)}</td>
                  <td><strong>${escapeHtml(record.productivity_score)}%</strong></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      ` : emptyState("No productivity records found.")}
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

function heartbeatCard() {
  const heartbeat = heartbeatStatus();
  return `
    <section class="session-heartbeat-card" aria-label="System login heartbeat and lockout status">
      <div class="heartbeat-title">
        <div>
          <span>System Session Heartbeat</span>
          <strong>Login and lockout monitor</strong>
        </div>
        <em class="heartbeat-live-pill" data-heartbeat-status>${heartbeat.lockedOut ? "LOCKOUT DUE" : "HEARTBEAT LIVE"}</em>
      </div>
      <div class="heartbeat-grid">
        <div><span>System Login</span><strong data-heartbeat-field="loginAt">${heartbeat.loginAt}</strong></div>
        <div><span>Last Heartbeat</span><strong data-heartbeat-field="lastHeartbeatAt">${heartbeat.lastHeartbeatAt}</strong></div>
        <div><span>Lockout Time</span><strong data-heartbeat-field="lockoutAt">${heartbeat.lockoutAt}</strong></div>
        <div><span>Time to Lockout</span><strong data-heartbeat-field="timeToLockout">${heartbeat.timeToLockout}</strong></div>
      </div>
    </section>
  `;
}

function agentDashboard() {
  const profile = state.agentProfile || {};
  const latestProductivity = state.productivity[0];
  const latestAttendance = state.attendance[0];
  return dashboardShell(`
    <div class="content-grid page-content">
      <section class="panel wide agent-dashboard-panel" id="agent-dashboard">
        <div class="panel-header">
          <div>
            <h2>Agent Dashboard</h2>
            <p>Personal WPACS profile, attendance, productivity, and daily summary.</p>
          </div>
          <span class="status-pill healthy">${escapeHtml(profile.status || "ACTIVE")}</span>
        </div>
        ${profile.employee_id ? `
          <div class="agent-dashboard-hero">
            <div>
              <span>Agent Name</span>
              <strong>${escapeHtml(profile.employee_name)}</strong>
              <small>${escapeHtml(profile.employee_id)}</small>
            </div>
            <div class="agent-score-card">
              <span>Productivity Score</span>
              <strong>${escapeHtml(latestProductivity?.productivity_score ?? 0)}%</strong>
            </div>
            <div class="agent-hero-meta">
              <div><span>Department</span><strong>${escapeHtml(profile.department)}</strong></div>
              <div><span>Attendance</span><strong>${escapeHtml(latestAttendance?.status || "No record")}</strong></div>
            </div>
          </div>
          ${heartbeatCard()}
          <div class="agent-dashboard-grid">
            ${attendancePanel(state.attendance)}
            ${productivityPanel(state.productivity)}
          </div>
        ` : emptyState()}
      </section>
    </div>
  `);
}

function render() {
  document.querySelector("#app").innerHTML = state.loading
    ? `<main class="login-page"><section class="login-panel-shell"><div class="login-panel">Loading WPACS...</div></section></main>`
    : state.user
      ? (isAgentSurface() ? agentDashboard() : managerDashboard())
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
            password_hash: formData.get("password_hash")
          })
        });
        const now = Date.now();
        state.heartbeat = { loginAt: now, lastHeartbeatAt: now, lockoutAt: now + 8 * 60 * 60 * 1000 };
        saveHeartbeat();
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
      sessionStorage.removeItem("wpacsHeartbeat");
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
      await api("/api/v1/employees", {
        method: "POST",
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
}

async function loadData() {
  state.error = "";
  try {
    if (isAgentSurface()) {
      state.agentProfile = await api("/agent/v1/profile");
      const employeeId = encodeURIComponent(state.agentProfile.employee_id || "");
      state.attendance = employeeId ? await api(`/api/v1/attendance?employee_id=${employeeId}`) : [];
      state.productivity = employeeId ? await api(`/api/v1/productivity?employee_id=${employeeId}`) : [];
    } else {
      state.dashboard = await api("/api/v1/dashboard");
      state.employees = await api("/api/v1/employees");
      state.attendance = await api("/api/v1/attendance");
      state.productivity = await api("/api/v1/productivity");
      state.reports = await api("/api/v1/reports");
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

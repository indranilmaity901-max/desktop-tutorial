import {
  alerts as fallbackAlerts,
  conflicts as fallbackConflicts,
  enterpriseReadiness as fallbackEnterpriseReadiness,
  enterpriseReadinessSummary as fallbackEnterpriseReadinessSummary,
  evidenceBreakdown as fallbackEvidenceBreakdown,
  explainabilityTrust as fallbackExplainabilityTrust,
  onboardingReadiness,
  productionChecklist,
  productivityTrend as fallbackProductivityTrend,
  ruleGovernance,
  screenInventory,
  sprintRoadmap,
  stateCorrelation as fallbackStateCorrelation,
  attendanceSummary,
  reportSummary,
  v1Modules,
  workflows,
  workstationAgent as fallbackWorkstationAgent
} from "./mockData.js?v=20260604-v1-modules";

let liveMetrics = [];
let evidenceBreakdown = fallbackEvidenceBreakdown;
let productivityTrend = fallbackProductivityTrend;
let conflicts = fallbackConflicts;
let alerts = fallbackAlerts;
let workstationAgent = fallbackWorkstationAgent;
let enterpriseReadiness = fallbackEnterpriseReadiness;
let enterpriseReadinessSummary = fallbackEnterpriseReadinessSummary;
let explainabilityTrust = fallbackExplainabilityTrust;
let stateCorrelation = fallbackStateCorrelation;
let rolesData = [
  { role_id: "ROLE-001", role_name: "Admin" },
  { role_id: "ROLE-002", role_name: "Manager" },
  { role_id: "ROLE-003", role_name: "Supervisor" }
];
let managersData = [
  { manager_id: "MGR-001", manager_name: "Richard Johnson" },
  { manager_id: "MGR-002", manager_name: "Susan Miller" },
  { manager_id: "MGR-003", manager_name: "Michael Anderson" },
  { manager_id: "MGR-004", manager_name: "Jennifer Garcia" },
  { manager_id: "MGR-005", manager_name: "Robert Martinez" }
];
let employeesData = [
  { employee_id: "EMP-001", employee_name: "John Smith", department: "Collections", manager_id: "MGR-001", status: "ACTIVE" },
  { employee_id: "EMP-002", employee_name: "Mina Patel", department: "Collections", manager_id: "MGR-001", status: "ACTIVE" },
  { employee_id: "EMP-003", employee_name: "Avery Jones", department: "Support", manager_id: "MGR-002", status: "ACTIVE" }
];
let attendanceLogsData = [
  { productivity_id: "PROD-001", employee_id: "EMP-001", productive_minutes: 390, non_productive_minutes: 75, productive_percentage: 83.87, metric_date: "2026-06-04" },
  { productivity_id: "PROD-002", employee_id: "EMP-002", productive_minutes: 412, non_productive_minutes: 48, productive_percentage: 89.57, metric_date: "2026-06-04" }
];
let currentUser = JSON.parse(sessionStorage.getItem("wpacsUser") || "null");
let employeeSearch = "";
let reportDate = "2026-06-05";
let reportDownloadDate = "2026-06-05";
let dailyAttendanceReport = null;
let dailyProductivityReport = null;
const frontendResponsibilities = [
  {
    icon: "database",
    title: "Display Data",
    detail: "Show live SQL records, KPIs, attendance logs, reports, and productivity signals."
  },
  {
    icon: "keyboard",
    title: "Capture User Input",
    detail: "Collect login credentials, employee details, filters, search terms, and report criteria."
  },
  {
    icon: "navigation",
    title: "Navigation",
    detail: "Move users between dashboard, employees, attendance, productivity, reports, users, and roles."
  },
  {
    icon: "line-chart",
    title: "Charts",
    detail: "Visualize productivity, attendance, compliance, and trend metrics for quick decisions."
  },
  {
    icon: "table-2",
    title: "Tables",
    detail: "Present searchable employee, attendance, user, role, and report datasets."
  },
  {
    icon: "form-input",
    title: "Forms",
    detail: "Create and update records through structured, validated enterprise forms."
  }
];

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

function formatPercent(value) {
  return `${Number(value || 0).toFixed(2)}%`;
}

function formatHours(minutes) {
  return `${(Number(minutes || 0) / 60).toFixed(2)}h`;
}

function metricCard({ label, value, trend, tone = "positive", evidenceKey, href }) {
  const evidence = evidenceBreakdown[evidenceKey] || [];

  return `
    <a class="metric-panel" href="${href}" aria-label="Open ${label} drilldown">
      <div class="metric-topline">
        <span class="metric-label">${label}</span>
        <span class="trend ${tone}">${trend}</span>
      </div>
      <strong>${value}</strong>
      <div class="evidence-list" aria-label="${label} score evidence">
        ${evidence.map((item) => `<span>${item.label}: <b>${item.value}</b></span>`).join("")}
      </div>
    </a>
  `;
}

function sidebar() {
  const groups = [
    {
      title: "WPACS V1",
      items: [["layout-dashboard", "Dashboard", "#dashboard", true]]
    },
    {
      title: "Workforce",
      items: [
        ["users", "Employees", "#employees"],
        ["calendar-check", "Attendance", "#attendance"]
      ]
    },
    {
      title: "Operations",
      items: [
        ["activity", "Productivity", "#productivity"],
        ["file-bar-chart", "Reports", "#reports"]
      ]
    },
    {
      title: "Administration",
      items: [
        ["user-cog", "Users", "#users"],
        ["shield-check", "Roles", "#roles"]
      ]
    }
  ];

  return `
    <aside class="sidebar" aria-label="Main navigation">
      <div class="brand">
        <div class="brand-mark">W</div>
        <div>
          <strong>WPACS</strong>
          <span>Operations dashboard</span>
        </div>
      </div>

      <nav class="nav-list">
        ${groups
          .map((group) => `
            <div class="nav-group">
              <p>${group.title}</p>
              ${group.items
                .map(([itemIcon, label, href, active]) => `
                  <a class="nav-item ${active ? "active" : ""}" href="${href}">
                    ${icon(itemIcon)}
                    <span>${label}</span>
                  </a>
                `)
                .join("")}
            </div>
          `)
          .join("")}
      </nav>

      <div class="agent-card">
        <div class="agent-ring"><span>5k</span></div>
        <div>
          <strong>Events/sec</strong>
          <span>15k burst ready</span>
        </div>
      </div>
    </aside>
  `;
}

function topbar() {
  return `
    <header class="topbar">
      <div>
        <p class="eyebrow">Dashboard</p>
        <h1>WPACS V1 Dashboard</h1>
      </div>
      <div class="topbar-actions">
        <label class="search">
          ${icon("search")}
          <input type="search" aria-label="Search employees or conflicts" placeholder="Search employees, alerts, rules">
        </label>
        <button class="select-button" type="button" aria-label="Organization selector">
          ${icon("building-2")}
          Apex Collections
        </button>
        <div class="segmented" role="group" aria-label="Date range">
          <button class="selected" type="button">Today</button>
          <button type="button">7D</button>
          <button type="button">30D</button>
        </div>
        <button class="icon-button alert-button" type="button" aria-label="Open notifications">
          ${icon("bell-ring")}
          <span>12</span>
        </button>
        <button class="profile-button" type="button" aria-label="Open user profile">AM</button>
        <span class="session-role">${currentUser?.role_name || "User"}</span>
        <button class="text-button" id="logoutButton" type="button">
          ${icon("log-out")}
          Logout
        </button>
      </div>
    </header>
  `;
}

function alertFirstPanel() {
  return `
    <section class="alert-priority compact-alert" id="alerts" aria-label="Alerts summary">
      <div>
        <p class="eyebrow">Today</p>
        <h2>Alerts and conflicts at a glance</h2>
        <span>Quick view of the most important operational signals.</span>
      </div>
      <div class="alert-summary-grid">
        <a href="#conflicts"><strong>12</strong><span>Critical</span></a>
        <a href="#conflicts"><strong>28</strong><span>High</span></a>
        <a href="#integrations"><strong>2</strong><span>Integration</span></a>
      </div>
    </section>
  `;
}

function productivityChart() {
  return `
    <section class="panel wide" id="productivity">
      <div class="panel-header">
        <div>
          <h2>Productivity Trend</h2>
          <p>Hourly productivity score movement.</p>
        </div>
        <button class="text-button" type="button">
          ${icon("refresh-cw")}
          Refresh
        </button>
      </div>
      <div class="chart-wrap">
        <div class="axis-label top">100</div>
        <div class="axis-label middle">50</div>
        <div class="bars">
          ${productivityTrend
            .map((item) => `
              <a class="bar" href="#manager-dashboard" title="${item.value}" style="height: ${item.value}%">
                <span>${item.label}</span>
              </a>
            `)
            .join("")}
        </div>
      </div>
    </section>
  `;
}

function healthPanel() {
  const services = [
    ["API Health", "HEALTHY"],
    ["Queue Health", "HEALTHY"],
    ["Database Health", "HEALTHY"],
    ["Event Processing", "5,000/sec"],
    ["Storage", "62% free"],
    ["Agent Connectivity", "98.7%"]
  ];

  return `
    <section class="panel" id="system-health">
      <div class="panel-header">
        <div>
          <h2>System Health</h2>
          <p>UX-014 platform monitoring</p>
        </div>
        <span class="status-pill healthy">Healthy</span>
      </div>
      <div class="health-list">
        ${services.map(([service, status]) => `<div><span>${service}</span><strong>${status}</strong></div>`).join("")}
      </div>
    </section>
  `;
}

function v1ModulesPanel() {
  return `
    <section class="panel wide" id="dashboard">
      <div class="panel-header">
        <div>
          <h2>V1 Modules</h2>
          <p>Core modules for the first production-ready WPACS release.</p>
        </div>
      </div>
      <div class="module-grid">
        ${v1Modules
          .map((module) => `
            <a class="module-card" href="${module.href}">
              <div class="module-icon">${icon(module.icon)}</div>
              <div>
                <span>${module.title}</span>
                <strong>${module.value}</strong>
                <small>${module.status}</small>
              </div>
              <ul>
                ${module.items.map((item) => `<li>${item}</li>`).join("")}
              </ul>
            </a>
          `)
          .join("")}
      </div>
    </section>
  `;
}

function frontendResponsibilitiesPanel() {
  return `
    <section class="panel wide" id="frontend-responsibilities">
      <div class="panel-header">
        <div>
          <h2>Frontend Responsibilities</h2>
          <p>Core user interface responsibilities for WPACS V1.</p>
        </div>
      </div>
      <div class="responsibility-grid">
        ${frontendResponsibilities
          .map((item) => `
            <article class="responsibility-card">
              <div class="module-icon">${icon(item.icon)}</div>
              <div>
                <strong>${item.title}</strong>
                <p>${item.detail}</p>
              </div>
            </article>
          `)
          .join("")}
      </div>
    </section>
  `;
}

function attendancePanel() {
  const roleName = currentUser?.role_name || "Admin";
  const report = dailyAttendanceReport || {
    logged_employees: attendanceLogsData.length,
    productive_minutes: attendanceLogsData.reduce((total, log) => total + Number(log.productive_minutes || 0), 0),
    non_productive_minutes: attendanceLogsData.reduce((total, log) => total + Number(log.non_productive_minutes || 0), 0),
    average_productive_percentage: attendanceLogsData.length
      ? attendanceLogsData.reduce((total, log) => total + Number(log.productive_percentage || 0), 0) / attendanceLogsData.length
      : 0
  };
  const productivityItems = dailyProductivityReport?.items || attendanceLogsData.map((log) => ({
    ...log,
    employee_name: employeesData.find((employee) => employee.employee_id === log.employee_id)?.employee_name || log.employee_id,
    department: employeesData.find((employee) => employee.employee_id === log.employee_id)?.department || "Unassigned"
  }));

  return `
    <section class="panel wide" id="attendance">
      <div class="panel-header">
        <div>
          <h2>Attendance</h2>
          <p>Manual attendance entry for WPACS V1.</p>
        </div>
      </div>

      <div class="display-data-tools">
        <div class="attendance-policy">
          <span>${icon("shield-check")} Admin, Manager, and Supervisor can mark attendance</span>
          <span>${icon("clock")} V1 attendance is manually marked</span>
          <span>${icon("radar")} V2 will auto-detect productive and non-productive time</span>
          <b>Signed in as ${escapeHtml(roleName)}</b>
        </div>
        <form class="attendance-form" id="attendanceMarkForm">
          <select name="employee_id" required aria-label="Employee">
            <option value="">Select employee</option>
            ${employeesData.map((employee) => `
              <option value="${escapeHtml(employee.employee_id)}">${escapeHtml(employee.employee_name)} (${escapeHtml(employee.employee_id)})</option>
            `).join("")}
          </select>
          <input name="metric_date" type="date" value="${escapeHtml(reportDate)}" required aria-label="Metric date">
          <select name="attendance_status" required aria-label="Attendance status">
            <option value="PRESENT">Present</option>
            <option value="PARTIAL">Partial</option>
            <option value="ABSENT">Absent</option>
            <option value="LEAVE">Leave</option>
          </select>
          <input name="worked_hours" type="number" min="0" step="0.25" placeholder="Worked hrs" required>
          <button type="submit">${icon("calendar-check")} Mark</button>
        </form>

        <div class="report-controls">
          <input id="reportDate" type="date" value="${escapeHtml(reportDate)}" aria-label="Report date">
          <button id="fetchAttendanceReport" type="button">${icon("calendar-days")} Daily Attendance</button>
          <button id="fetchProductivityReport" type="button">${icon("line-chart")} Productive Report</button>
        </div>
        <div class="report-note">
          ${icon("bar-chart-3")} Shrinkage is detected from the data report, not the attendance entry.
        </div>

        <div class="employee-form-result" id="attendanceActionResult">
          Display data for ${escapeHtml(reportDate)}
        </div>
      </div>

      <div class="mini-stat-grid report-stat-grid">
        <div><span>Logged Employees</span><strong>${report.logged_employees}</strong></div>
        <div><span>Productive Hours</span><strong>${formatHours(report.productive_minutes)}</strong></div>
        <div><span>Non-Productive Hours</span><strong>${formatHours(report.non_productive_minutes)}</strong></div>
        <div><span>Avg Productive</span><strong>${formatPercent(report.average_productive_percentage)}</strong></div>
      </div>
      <div class="attendance-log-list">
        ${productivityItems
          .map((log) => `
            <article>
              <strong>${escapeHtml(log.employee_name || log.employee_id)}</strong>
              <span>${escapeHtml(log.attendance_status || log.department || log.productivity_id)}</span>
              <small>${escapeHtml(log.employee_id)} - ${formatHours(log.productive_minutes)} productive / ${formatHours(log.non_productive_minutes)} non-productive</small>
              <b>${formatPercent(log.productive_percentage)}</b>
            </article>
          `)
          .join("")}
        ${productivityItems.length ? "" : "<article><strong>No report data</strong><span>Select a date and fetch a report.</span></article>"}
      </div>
    </section>
  `;
}

function reportsPanel() {
  return `
    <section class="panel" id="reports">
      <div class="panel-header">
        <div>
          <h2>Reports</h2>
          <p>Download daily productive and attendance summary reports.</p>
        </div>
      </div>
      <form class="report-download-form" id="reportDownloadForm">
        <select name="report_type" aria-label="Report type">
          <option value="daily-productive">Daily Productive Report</option>
          <option value="attendance-summary">Attendance Summary</option>
        </select>
        <select name="format" aria-label="Report format">
          <option value="xlsx">Excel</option>
          <option value="pdf">PDF</option>
        </select>
        <input name="metric_date" type="date" value="${escapeHtml(reportDownloadDate)}" aria-label="Report download date">
        <button type="submit">${icon("download")} Download</button>
      </form>
      <div class="employee-form-result" id="reportDownloadResult">Choose report and format.</div>
      <div class="report-list">
        ${[
            { name: "Daily Productive Report", format: "Excel / PDF", status: "Ready" },
            { name: "Attendance Summary", format: "Excel / PDF", status: "Ready" }
          ]
          .map((report) => `
            <div>
              <strong>${report.name}</strong>
              <span>${report.format}</span>
              <small>${report.status}</small>
            </div>
          `)
          .join("")}
      </div>
    </section>
  `;
}

function employeesPanel() {
  const normalizedSearch = employeeSearch.trim().toLowerCase();
  const visibleEmployees = normalizedSearch
    ? employeesData.filter((employee) => [
        employee.employee_id,
        employee.employee_name,
        employee.department,
        employee.manager_id,
        employee.manager_name,
        employee.status
      ].some((value) => String(value).toLowerCase().includes(normalizedSearch)))
    : employeesData;

  return `
    <section class="panel wide" id="employees">
      <div class="panel-header">
        <div>
          <h2>Employees</h2>
          <p>Search, add, and delete agent records stored in SQL.</p>
        </div>
      </div>
      <div class="employee-tools">
        <label class="employee-search">
          ${icon("search")}
          <input id="employeeSearch" value="${escapeHtml(employeeSearch)}" placeholder="Search employees, departments, managers">
        </label>
        <form class="employee-form" id="employeeForm">
          <input name="employee_id" placeholder="Agent ID" required>
          <input name="employee_name" placeholder="Agent name" required>
          <input name="department" placeholder="Department" required>
          <select name="manager_id" required>
            <option value="">Manager</option>
            ${managersData.map((manager) => `
              <option value="${escapeHtml(manager.manager_id)}">${escapeHtml(manager.manager_name)} (${escapeHtml(manager.manager_id)})</option>
            `).join("")}
          </select>
          <select name="status" required>
            <option>ACTIVE</option>
            <option>INACTIVE</option>
          </select>
          <button type="submit">${icon("user-plus")} Add Agent</button>
        </form>
        <div class="employee-form-result" id="employeeFormResult">Showing ${visibleEmployees.length} of ${employeesData.length}</div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Employee ID</th>
              <th>Name</th>
              <th>Department</th>
              <th>Manager</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            ${visibleEmployees
              .map((employee) => `
                <tr>
                  <td>${escapeHtml(employee.employee_id)}</td>
                  <td><strong>${escapeHtml(employee.employee_name)}</strong></td>
                  <td>${escapeHtml(employee.department)}</td>
                  <td>${escapeHtml(employee.manager_name || employee.manager_id)} <small>${escapeHtml(employee.manager_id)}</small></td>
                  <td><span class="state">${escapeHtml(employee.status)}</span></td>
                  <td>
                    <button class="row-action danger" data-delete-employee="${escapeHtml(employee.employee_id)}" type="button">
                      ${icon("trash-2")}
                      Delete
                    </button>
                  </td>
                </tr>
              `)
              .join("")}
            ${visibleEmployees.length ? "" : `
              <tr>
                <td colspan="6">No agents found.</td>
              </tr>
            `}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function administrationPanel() {
  return `
    <section class="panel wide" id="users">
      <div class="panel-header">
        <div>
          <h2>Users & Roles</h2>
          <p>V1 administration for user access and RBAC.</p>
        </div>
      </div>
      <div class="admin-grid">
        <article>
          <h3>Users</h3>
          <strong>124</strong>
          <span>Active system users</span>
          <button type="button">Create User</button>
        </article>
        <article id="roles">
          <h3>Roles</h3>
          <strong>${rolesData.length}</strong>
          <span>${rolesData.map((role) => role.role_name).join(", ")}</span>
          <div class="role-list">
            ${rolesData.map((role) => `<small>${role.role_id} - ${role.role_name}</small>`).join("")}
          </div>
          <button type="button">Manage Roles</button>
        </article>
        <article id="managers">
          <h3>Managers</h3>
          <strong>${managersData.length}</strong>
          <span>Agent reporting managers</span>
          <div class="role-list">
            ${managersData.map((manager) => `<small>${manager.manager_id} - ${manager.manager_name}</small>`).join("")}
          </div>
          <button type="button">Manage Managers</button>
        </article>
      </div>
    </section>
  `;
}

function loginPage() {
  return `
    <main class="login-page">
      <section class="login-hero" aria-label="WPACS enterprise access">
        <header class="login-brand-row">
          <div class="brand large">
            <div class="brand-mark">W</div>
            <div>
              <strong>WPACS</strong>
              <span>Workforce Productivity & Activity Correlation</span>
            </div>
          </div>
          <div class="security-pill">
            ${icon("shield-check")}
            TLS 1.3 secured
          </div>
        </header>

        <div class="identity-message">
          <p class="eyebrow">Identity Gateway</p>
          <h1>Secure access for WPACS V1.</h1>
          <p>Authenticate with a role, username, and password hash to open the WPACS dashboard.</p>
        </div>
      </section>

      <section class="login-panel-shell" aria-label="Login form">
        <form class="login-panel" id="loginForm">
          <div class="login-panel-header">
            <div class="login-lock">
              ${icon("lock-keyhole")}
            </div>
            <div>
              <p class="eyebrow">Identity Gateway</p>
              <h2>Sign in to WPACS</h2>
            </div>
          </div>

          <label>
            <span>Role</span>
            <select name="role_name">
              <option>Admin</option>
              <option>Manager</option>
              <option>Supervisor</option>
            </select>
          </label>
          <label>
            <span>Username</span>
            <input name="username" autocomplete="username" value="admin">
          </label>
          <label>
            <span>Password Hash</span>
            <input name="password_hash" autocomplete="off" type="password" value="admin_hash_001">
          </label>
          <button type="submit">
            ${icon("log-in")}
            Authenticate
          </button>
          <div class="login-result" id="loginResult">Demo access: admin / admin_hash_001</div>

          <div class="security-checks">
            <span>${icon("fingerprint")} RBAC verified</span>
            <span>${icon("database-lock")} SQL-backed identity</span>
            <span>${icon("scan-eye")} Audit-ready session</span>
          </div>
        </form>
      </section>
    </main>
  `;
}

function conflictQueue() {
  return `
    <section class="panel wide" id="conflicts">
      <div class="panel-header">
        <div>
          <h2>Conflict Management</h2>
          <p>Review detected conflicts with evidence and resolution status.</p>
        </div>
        <button class="icon-button subtle" type="button" aria-label="Filter conflicts">
          ${icon("sliders-horizontal")}
        </button>
      </div>
      <div class="filter-row" aria-label="Conflict filters">
        <button type="button">Severity</button>
        <button type="button">Manager</button>
        <button type="button">Department</button>
        <button type="button">Date</button>
        <button type="button">Status</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Employee</th>
              <th>Type</th>
              <th>Severity</th>
              <th>Duration</th>
              <th>Confidence</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${conflicts
              .map((item) => `
                <tr>
                  <td>
                    <a class="employee-cell" href="#employee-profile">
                      <span class="avatar">${item.initials}</span>
                      <strong>${item.employee}</strong>
                    </a>
                  </td>
                  <td><a href="#conflict-detail">${item.type}</a></td>
                  <td><span class="severity ${item.severity.toLowerCase()}">${item.severity}</span></td>
                  <td>${item.duration}</td>
                  <td>${item.confidence}%</td>
                  <td><span class="state">${item.status}</span></td>
                </tr>
              `)
              .join("")}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function alertPanel() {
  return `
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2>Alert Center</h2>
          <p>Productivity, compliance, risk, system, and integration alerts.</p>
        </div>
        <span class="count-pill">42</span>
      </div>
      <div class="alert-list">
        ${alerts
          .map((item) => `
            <a class="alert-item" href="#alert-center">
              <div class="alert-icon ${item.priority.toLowerCase()}">${icon(item.icon)}</div>
              <div>
                <strong>${item.title}</strong>
                <span>${item.detail}</span>
              </div>
            </a>
          `)
          .join("")}
      </div>
    </section>
  `;
}

function workflowPanel() {
  return `
    <section class="panel" id="workflows">
      <div class="panel-header">
        <div>
          <h2>User Workflows</h2>
          <p>Primary paths from the UX specification</p>
        </div>
      </div>
      <div class="workflow-list">
        ${workflows
          .map((workflow) => `
            <article>
              <strong>${workflow.title}</strong>
              <span>${workflow.steps.join(" -> ")}</span>
            </article>
          `)
          .join("")}
      </div>
    </section>
  `;
}

function screenInventoryPanel() {
  return `
    <section class="panel wide" id="screen-inventory">
      <div class="panel-header">
        <div>
          <h2>Screen Inventory</h2>
          <p>Defined UX screens available for application build-out</p>
        </div>
      </div>
      <div class="screen-grid">
        ${screenInventory
          .map((screen) => `
            <a href="#${screen.id.toLowerCase()}">
              <strong>${screen.id}</strong>
              <span>${screen.name}</span>
            </a>
          `)
          .join("")}
      </div>
    </section>
  `;
}

function workstationAgentPanel() {
  return `
    <section class="panel wide" id="workstation-agent">
      <div class="panel-header">
        <div>
          <h2>Workstation Agent</h2>
          <p>Endpoint monitoring source for activity correlation and state validation.</p>
        </div>
        <span class="status-pill healthy">${workstationAgent.service.status}</span>
      </div>

      <div class="agent-overview">
        <div class="agent-service-card">
          <div>
            <span>Windows Service</span>
            <strong>${workstationAgent.service.name}</strong>
            <small>${workstationAgent.service.displayName}</small>
          </div>
          <div class="agent-version">
            <span>Version</span>
            <strong>${workstationAgent.service.version}</strong>
          </div>
        </div>

        <div class="agent-metrics">
          <div><span>Heartbeat</span><strong>${workstationAgent.service.heartbeat}</strong></div>
          <div><span>CPU</span><strong>${workstationAgent.service.cpu}</strong></div>
          <div><span>Memory</span><strong>${workstationAgent.service.memory}</strong></div>
          <div><span>Disk</span><strong>${workstationAgent.service.disk}</strong></div>
        </div>
      </div>

      <div class="agent-grid">
        <article>
          <h3>Captured Events</h3>
          <div class="chip-list">
            ${workstationAgent.events.map((event) => `<span>${event}</span>`).join("")}
          </div>
        </article>

        <article>
          <h3>Secure Transport</h3>
          <div class="kv-list">
            ${workstationAgent.transport.map((item) => `<div><span>${item.label}</span><strong>${item.value}</strong></div>`).join("")}
          </div>
        </article>

        <article>
          <h3>Offline Buffer</h3>
          <div class="kv-list">
            ${workstationAgent.buffer.map((item) => `<div><span>${item.label}</span><strong>${item.value}</strong></div>`).join("")}
          </div>
        </article>

        <article>
          <h3>Privacy Guardrails</h3>
          <div class="guardrail-list">
            ${workstationAgent.safeguards.map((item) => `<span>${icon("ban")}${item}</span>`).join("")}
          </div>
        </article>

        <article>
          <h3>Enterprise Deployment</h3>
          <div class="chip-list">
            ${workstationAgent.deployment.map((item) => `<span>${item}</span>`).join("")}
          </div>
        </article>

        <article>
          <h3>Tamper Detection</h3>
          <div class="guardrail-list warning">
            ${workstationAgent.tamperSignals.map((item) => `<span>${icon("triangle-alert")}${item}</span>`).join("")}
          </div>
        </article>
      </div>
    </section>
  `;
}

function enterpriseReadinessPanel() {
  return `
    <section class="panel wide" id="enterprise-readiness">
      <div class="panel-header">
        <div>
          <h2>Enterprise Readiness</h2>
          <p>Go-live posture across product, data, security, infrastructure, QA, and commercialization.</p>
        </div>
        <span class="status-pill neutral">${enterpriseReadinessSummary.status}</span>
      </div>
      <div class="readiness-hero">
        <div class="readiness-score" style="--score: ${enterpriseReadinessSummary.score}">
          <strong>${enterpriseReadinessSummary.score}%</strong>
          <span>Readiness</span>
        </div>
        <div>
          <strong>${enterpriseReadinessSummary.decision}</strong>
          <span>Next gate: ${enterpriseReadinessSummary.nextGate}</span>
        </div>
        <div class="readiness-blockers">
          <strong>${enterpriseReadinessSummary.blockers}</strong>
          <span>blocking gaps</span>
        </div>
      </div>
      <div class="readiness-grid">
        ${enterpriseReadiness
          .map((area) => `
            <article class="${area.tone}">
              <div class="readiness-title">
                ${icon(area.icon)}
                <div>
                  <strong>${area.title}</strong>
                  <span>${area.owner}</span>
                </div>
                <em>${area.status}</em>
              </div>
              <div class="readiness-evidence">
                <span>Evidence</span>
                <strong>${area.evidence}</strong>
              </div>
              <div class="readiness-gap">
                <span>Gap</span>
                <strong>${area.gap}</strong>
              </div>
              <ul>
                ${area.items.map((item) => `<li>${item}</li>`).join("")}
              </ul>
            </article>
          `)
          .join("")}
      </div>
    </section>
  `;
}

function explainabilityPanel() {
  return `
    <section class="panel" id="explainability">
      <div class="panel-header">
        <div>
          <h2>Explainability & Trust</h2>
          <p>Every score, conflict, alert, and recommendation must be defendable.</p>
        </div>
      </div>
      <div class="trust-list">
        ${explainabilityTrust
          .map((item) => `
            <div>
              <span>${item.label}</span>
              <strong>${item.value}</strong>
              <small>${item.target}</small>
            </div>
          `)
          .join("")}
      </div>
    </section>
  `;
}

function stateCorrelationPanel() {
  return `
    <section class="panel" id="state-correlation">
      <div class="panel-header">
        <div>
          <h2>State Correlation</h2>
          <p>Current evidence snapshot used by validation rules.</p>
        </div>
        <span class="severity high">READY_LOCKED</span>
      </div>
      <div class="correlation-list">
        ${stateCorrelation
          .map((item) => `
            <div>
              <span>${item.source}</span>
              <strong>${item.state}</strong>
              <small>${item.confidence}% confidence</small>
            </div>
          `)
          .join("")}
      </div>
    </section>
  `;
}

function ruleGovernancePanel() {
  return `
    <section class="panel" id="rules">
      <div class="panel-header">
        <div>
          <h2>Rule Engine Governance</h2>
          <p>DSL types, lifecycle, and approval controls.</p>
        </div>
      </div>
      <div class="rule-section">
        <strong>Rule Types</strong>
        <div class="chip-list">${ruleGovernance.ruleTypes.map((item) => `<span>${item}</span>`).join("")}</div>
      </div>
      <div class="rule-section">
        <strong>Lifecycle</strong>
        <div class="rule-flow">
          ${ruleGovernance.lifecycle.map((item) => `<span>${item}</span>`).join(icon("chevron-right"))}
        </div>
      </div>
      <div class="rule-section">
        <strong>Approval</strong>
        <div class="chip-list">${ruleGovernance.approval.map((item) => `<span>${item}</span>`).join("")}</div>
      </div>
    </section>
  `;
}

function onboardingPanel() {
  return `
    <section class="panel wide" id="customer-onboarding">
      <div class="panel-header">
        <div>
          <h2>Customer Onboarding</h2>
          <p>Deployment journey from discovery to production activation and customer success.</p>
        </div>
      </div>
      <div class="onboarding-timeline">
        ${onboardingReadiness
          .map((item, index) => `
            <article>
              <span>${String(index + 1).padStart(2, "0")}</span>
              <strong>${item.phase}</strong>
              <p>${item.status}</p>
            </article>
          `)
          .join("")}
      </div>
    </section>
  `;
}

function sprintRoadmapPanel() {
  return `
    <section class="panel" id="sprint-roadmap">
      <div class="panel-header">
        <div>
          <h2>Engineering Roadmap</h2>
          <p>Sprint 0 foundation through rule engine delivery.</p>
        </div>
      </div>
      <div class="roadmap-list">
        ${sprintRoadmap
          .map((item) => `
            <article>
              <strong>${item.sprint}</strong>
              <span>${item.focus}</span>
            </article>
          `)
          .join("")}
      </div>
    </section>
  `;
}

function productionChecklistPanel() {
  return `
    <section class="panel" id="production-checklist">
      <div class="panel-header">
        <div>
          <h2>Production Readiness</h2>
          <p>Infrastructure cannot go live until all checks pass.</p>
        </div>
      </div>
      <div class="checklist">
        ${productionChecklist.map((item) => `<span>${icon("check")}${item}</span>`).join("")}
      </div>
    </section>
  `;
}

function dashboard() {
  const metrics = liveMetrics.length
    ? liveMetrics
    : [
        { key: "productivity", label: "Productivity", value: "82%", trend: "+4.2%", tone: "positive", href: "#productivity" },
        { key: "compliance", label: "Compliance", value: "91%", trend: "+1.8%", tone: "positive", href: "#compliance" },
        { key: "confidence", label: "Confidence", value: "96%", trend: "Stable", tone: "neutral", href: "#confidence" },
        { key: "activeUsers", label: "Active Users", value: "842", trend: "Live", tone: "positive", href: "#employees" },
        { key: "conflicts", label: "Conflicts", value: "45", trend: "+12", tone: "negative", href: "#conflicts" }
      ];

  return `
    <div class="app-shell">
      ${sidebar()}
      <main class="workspace">
        ${topbar()}
        ${alertFirstPanel()}
        ${v1ModulesPanel()}
        ${frontendResponsibilitiesPanel()}
        <section class="kpi-grid" aria-label="Executive key performance indicators">
          ${metrics
            .map((item) => metricCard({
              label: item.label,
              value: item.value,
              trend: item.trend,
              tone: item.tone || "positive",
              evidenceKey: item.key,
              href: item.href
            }))
            .join("")}
        </section>
        <div class="content-grid">
          ${employeesPanel()}
          ${productivityChart()}
          ${attendancePanel()}
          ${alertPanel()}
          ${reportsPanel()}
          ${conflictQueue()}
          ${administrationPanel()}
          ${healthPanel()}
        </div>
      </main>
    </div>
  `;
}

function render() {
  document.querySelector("#app").innerHTML = currentUser ? dashboard() : loginPage();
  if (window.lucide) {
    window.lucide.createIcons();
  }
  attachLoginHandler();
  attachLogoutHandler();
  attachEmployeeHandlers();
  attachAttendanceHandlers();
  attachReportDownloadHandler();
}

function attachLoginHandler() {
  const form = document.querySelector("#loginForm");
  const result = document.querySelector("#loginResult");
  if (!form || !result) {
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    result.textContent = "Status: checking";

    const formData = new FormData(form);
    const payload = {
      role_name: formData.get("role_name"),
      username: formData.get("username"),
      password_hash: formData.get("password_hash")
    };

    try {
      const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (data.success) {
        currentUser = data.data;
        sessionStorage.setItem("wpacsUser", JSON.stringify(currentUser));
        render();
      } else {
        result.textContent = `Status: failed | ${data.message}`;
      }
    } catch {
      result.textContent = "Status: failed | API unavailable";
    }
  });
}

function attachLogoutHandler() {
  const button = document.querySelector("#logoutButton");
  if (!button) {
    return;
  }

  button.addEventListener("click", () => {
    currentUser = null;
    sessionStorage.removeItem("wpacsUser");
    render();
  });
}

async function loadSqlDashboard() {
  try {
    const response = await fetch("/api/live-dashboard", { cache: "no-store" });
    if (!response.ok) {
      return;
    }

    const data = await response.json();
    liveMetrics = data.metrics || liveMetrics;
    evidenceBreakdown = data.evidenceBreakdown || evidenceBreakdown;
    productivityTrend = data.productivityTrend || productivityTrend;
    conflicts = data.conflicts || conflicts;
    alerts = data.alerts || alerts;
    workstationAgent = data.workstationAgent || workstationAgent;
    enterpriseReadiness = data.enterpriseReadiness || enterpriseReadiness;
    enterpriseReadinessSummary = data.enterpriseReadinessSummary || enterpriseReadinessSummary;
    explainabilityTrust = data.explainabilityTrust || explainabilityTrust;
    stateCorrelation = data.stateCorrelation || stateCorrelation;
  } catch {
    // Keep fallback data when the SQL API is not running.
  }
}

async function loadRoles() {
  try {
    const response = await fetch("/api/v1/roles", { cache: "no-store" });
    if (!response.ok) {
      return;
    }

    const payload = await response.json();
    rolesData = payload.data || rolesData;
  } catch {
    // Keep fallback role data when the SQL API is unavailable.
  }
}

async function loadManagers() {
  try {
    const response = await fetch("/api/v1/managers", { cache: "no-store" });
    if (!response.ok) {
      return;
    }

    const payload = await response.json();
    managersData = payload.data || managersData;
  } catch {
    // Keep fallback manager data when the SQL API is unavailable.
  }
}

async function loadEmployees() {
  try {
    const response = await fetch("/api/v1/employees", { cache: "no-store" });
    if (!response.ok) {
      return;
    }

    const payload = await response.json();
    employeesData = payload.data || employeesData;
  } catch {
    // Keep fallback employee data when the SQL API is unavailable.
  }
}

function attachEmployeeHandlers() {
  const search = document.querySelector("#employeeSearch");
  const form = document.querySelector("#employeeForm");
  const result = document.querySelector("#employeeFormResult");
  const deleteButtons = document.querySelectorAll("[data-delete-employee]");

  if (search) {
    search.addEventListener("input", (event) => {
      employeeSearch = event.target.value;
      render();
      const nextSearch = document.querySelector("#employeeSearch");
      if (nextSearch) {
        nextSearch.focus();
        nextSearch.setSelectionRange(nextSearch.value.length, nextSearch.value.length);
      }
    });
  }

  if (form && result) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      result.textContent = "Adding employee...";

      const formData = new FormData(form);
      const payload = {
        employee_id: formData.get("employee_id"),
        employee_name: formData.get("employee_name"),
        department: formData.get("department"),
        manager_id: formData.get("manager_id"),
        status: formData.get("status")
      };

      try {
        const response = await fetch("/api/v1/employees", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (!data.success) {
          result.textContent = data.message;
          return;
        }

        employeeSearch = "";
        await loadEmployees();
        render();
      } catch {
        result.textContent = "Employee API unavailable";
      }
    });
  }

  deleteButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const employeeId = button.dataset.deleteEmployee;
      if (!employeeId || !window.confirm(`Delete agent ${employeeId}?`)) {
        return;
      }

      if (result) {
        result.textContent = `Deleting ${employeeId}...`;
      }

      try {
        const response = await fetch(`/api/v1/employees/${encodeURIComponent(employeeId)}`, {
          method: "DELETE"
        });
        const data = await response.json();

        if (!data.success) {
          if (result) {
            result.textContent = data.message;
          }
          return;
        }

        await loadEmployees();
        await loadSqlDashboard();
        await loadAttendanceLogs(reportDate);
        await fetchDailyAttendanceReport(reportDate);
        await fetchDailyProductivityReport(reportDate);
        render();
      } catch {
        if (result) {
          result.textContent = "Employee API unavailable";
        }
      }
    });
  });
}

function attachAttendanceHandlers() {
  const form = document.querySelector("#attendanceMarkForm");
  const reportDateInput = document.querySelector("#reportDate");
  const attendanceButton = document.querySelector("#fetchAttendanceReport");
  const productivityButton = document.querySelector("#fetchProductivityReport");
  const result = document.querySelector("#attendanceActionResult");

  if (reportDateInput) {
    reportDateInput.addEventListener("input", (event) => {
      reportDate = event.target.value || reportDate;
    });
  }

  if (form && result) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      result.textContent = "Saving attendance log...";

      const formData = new FormData(form);
      const payload = {
        employee_id: formData.get("employee_id"),
        attendance_date: formData.get("metric_date"),
        attendance_status: formData.get("attendance_status"),
        worked_minutes: Math.round(Number(formData.get("worked_hours") || 0) * 60),
        marked_by_role: currentUser?.role_name || "Admin",
        marked_by_user: currentUser?.username || "admin"
      };
      reportDate = payload.attendance_date || reportDate;

      try {
        const response = await fetch("/api/v1/attendance-logs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (!data.success) {
          result.textContent = data.message;
          return;
        }

        await loadAttendanceLogs(reportDate);
        await fetchDailyAttendanceReport(reportDate);
        await fetchDailyProductivityReport(reportDate);
        render();
      } catch {
        result.textContent = "Attendance API unavailable";
      }
    });
  }

  if (attendanceButton && result) {
    attendanceButton.addEventListener("click", async () => {
      result.textContent = "Fetching daily attendance report...";
      reportDate = reportDateInput?.value || reportDate;
      await fetchDailyAttendanceReport(reportDate);
      await loadAttendanceLogs(reportDate);
      render();
    });
  }

  if (productivityButton && result) {
    productivityButton.addEventListener("click", async () => {
      result.textContent = "Fetching productive report...";
      reportDate = reportDateInput?.value || reportDate;
      await fetchDailyProductivityReport(reportDate);
      render();
    });
  }
}

function attachReportDownloadHandler() {
  const form = document.querySelector("#reportDownloadForm");
  const result = document.querySelector("#reportDownloadResult");
  if (!form || !result) {
    return;
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const reportType = formData.get("report_type") || "daily-productive";
    const format = formData.get("format") || "xlsx";
    const metricDate = formData.get("metric_date") || reportDownloadDate;
    reportDownloadDate = metricDate;
    const url = `/api/v1/reports/download?report_type=${encodeURIComponent(reportType)}&format=${encodeURIComponent(format)}&metric_date=${encodeURIComponent(metricDate)}`;
    result.textContent = `Downloading ${format === "pdf" ? "PDF" : "Excel"} report for ${metricDate}`;
    window.location.href = url;
  });
}

async function loadAttendanceLogs(date = reportDate) {
  try {
    const response = await fetch(`/api/v1/attendance-logs?metric_date=${encodeURIComponent(date)}`, { cache: "no-store" });
    if (!response.ok) {
      return;
    }

    const payload = await response.json();
    attendanceLogsData = payload.data || attendanceLogsData;
  } catch {
    // Keep fallback attendance data when the SQL API is unavailable.
  }
}

async function fetchDailyAttendanceReport(date = reportDate) {
  try {
    const response = await fetch(`/api/v1/reports/attendance-daily?metric_date=${encodeURIComponent(date)}`, { cache: "no-store" });
    if (!response.ok) {
      return;
    }

    const payload = await response.json();
    dailyAttendanceReport = payload.data || dailyAttendanceReport;
  } catch {
    // Keep the current report data when the SQL API is unavailable.
  }
}

async function fetchDailyProductivityReport(date = reportDate) {
  try {
    const response = await fetch(`/api/v1/reports/productivity-daily?metric_date=${encodeURIComponent(date)}`, { cache: "no-store" });
    if (!response.ok) {
      return;
    }

    const payload = await response.json();
    dailyProductivityReport = payload.data || dailyProductivityReport;
  } catch {
    // Keep the current report data when the SQL API is unavailable.
  }
}

render();
Promise.all([
  loadSqlDashboard(),
  loadRoles(),
  loadManagers(),
  loadEmployees(),
  loadAttendanceLogs(),
  fetchDailyAttendanceReport(),
  fetchDailyProductivityReport()
]).then(render);

window.addEventListener("load", () => {
  if (window.lucide) {
    window.lucide.createIcons();
  }
});

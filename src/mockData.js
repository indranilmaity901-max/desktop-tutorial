export const productivityTrend = [
  { label: "08", value: 72 },
  { label: "09", value: 78 },
  { label: "10", value: 82 },
  { label: "11", value: 74 },
  { label: "12", value: 84 },
  { label: "13", value: 86 },
  { label: "14", value: 83 },
  { label: "15", value: 88 },
  { label: "16", value: 85 },
  { label: "17", value: 90 }
];

export const evidenceBreakdown = {
  productivity: [
    { label: "Productive time", value: "78%" },
    { label: "Conflict penalty", value: "-4%" },
    { label: "Attendance penalty", value: "-2%" }
  ],
  compliance: [
    { label: "State adherence", value: "94%" },
    { label: "Schedule match", value: "89%" },
    { label: "Open risk", value: "Low" }
  ],
  confidence: [
    { label: "Event coverage", value: "99%" },
    { label: "Source match", value: "96%" },
    { label: "Stale data", value: "1%" }
  ],
  activeUsers: [
    { label: "Ready", value: "618" },
    { label: "On call", value: "154" },
    { label: "Break", value: "70" }
  ],
  conflicts: [
    { label: "Critical", value: "12" },
    { label: "High", value: "28" },
    { label: "Avg duration", value: "14m" }
  ]
};

export const conflicts = [
  {
    employee: "John Smith",
    initials: "JS",
    type: "READY_LOCKED",
    severity: "HIGH",
    duration: "15m",
    confidence: 98,
    status: "OPEN"
  },
  {
    employee: "Avery Jones",
    initials: "AJ",
    type: "SCHEDULE_MISMATCH",
    severity: "MEDIUM",
    duration: "9m",
    confidence: 91,
    status: "ACKNOWLEDGED"
  },
  {
    employee: "Mina Patel",
    initials: "MP",
    type: "IDLE_READY",
    severity: "HIGH",
    duration: "22m",
    confidence: 95,
    status: "INVESTIGATING"
  },
  {
    employee: "Carlos Rivera",
    initials: "CR",
    type: "ATTENDANCE_GAP",
    severity: "MEDIUM",
    duration: "6m",
    confidence: 88,
    status: "OPEN"
  }
];

export const alerts = [
  {
    title: "Productivity drop detected",
    detail: "Collections team down 7% in last hour",
    priority: "Critical",
    icon: "trending-down"
  },
  {
    title: "High conflict volume",
    detail: "12 unresolved READY_LOCKED conflicts",
    priority: "High",
    icon: "shield-alert"
  },
  {
    title: "Integration delay",
    detail: "TCN queue latency above expected range",
    priority: "High",
    icon: "plug-zap"
  },
  {
    title: "Rule synchronization complete",
    detail: "147 active rules loaded into cache",
    priority: "Info",
    icon: "git-branch"
  }
];

export const workflows = [
  {
    title: "Manager investigates productivity issue",
    steps: ["Dashboard", "Alert", "Conflict", "Employee Profile", "Evidence", "Resolution"]
  },
  {
    title: "Administrator creates rule",
    steps: ["Rules", "Create Rule", "Test Rule", "Approve", "Activate"]
  },
  {
    title: "Executive reviews organization performance",
    steps: ["Dashboard", "Department Metrics", "Manager Metrics", "Trend Analysis", "ROI Indicators"]
  }
];

export const screenInventory = [
  { id: "UX-001", name: "Executive Dashboard" },
  { id: "UX-002", name: "Productivity Dashboard" },
  { id: "UX-003", name: "Employee Directory" },
  { id: "UX-004", name: "Employee Profile" },
  { id: "UX-005", name: "Activity Timeline" },
  { id: "UX-006", name: "Conflict Management" },
  { id: "UX-007", name: "Conflict Detail" },
  { id: "UX-008", name: "Alert Center" },
  { id: "UX-009", name: "Report Center" },
  { id: "UX-010", name: "Rule Engine" },
  { id: "UX-011", name: "Rule Builder" },
  { id: "UX-012", name: "User Management" },
  { id: "UX-013", name: "Integration Center" },
  { id: "UX-014", name: "System Health" },
  { id: "UX-015", name: "Audit Center" }
];

export const workstationAgent = {
  service: {
    name: "WPACSAgent",
    displayName: "WPACS Workstation Monitoring Service",
    version: "1.0.0",
    status: "HEALTHY",
    heartbeat: "60 sec",
    cpu: "<1%",
    memory: "118 MB",
    disk: "342 MB"
  },
  events: [
    "LOGIN",
    "LOGOUT",
    "LOCK",
    "UNLOCK",
    "SHUTDOWN",
    "RESTART",
    "SESSION_DISCONNECT",
    "SESSION_RECONNECT",
    "IDLE_START",
    "IDLE_END"
  ],
  safeguards: [
    "No screenshots",
    "No video recording",
    "No keystroke capture",
    "No clipboard access"
  ],
  transport: [
    { label: "Endpoint", value: "/api/v1/workstation/events" },
    { label: "Protocol", value: "HTTPS + TLS 1.3" },
    { label: "Auth", value: "JWT" },
    { label: "Batch size", value: "100 events" },
    { label: "Max payload", value: "1 MB" }
  ],
  buffer: [
    { label: "Storage", value: "LiteDB" },
    { label: "Retention", value: "72 hours" },
    { label: "Retry window", value: "24 hours" },
    { label: "Offline mode", value: "Enabled" }
  ],
  deployment: ["Microsoft Intune", "SCCM", "Group Policy", "Manual MSI"],
  tamperSignals: [
    "Service stop",
    "Service disable",
    "Configuration modification",
    "Agent removal"
  ]
};

export const enterpriseReadinessSummary = {
  score: 74,
  status: "Conditional",
  decision: "Ready for controlled pilot, not production go-live",
  blockers: 4,
  nextGate: "Security review and restore test"
};

export const enterpriseReadiness = [
  {
    title: "Product Scope",
    icon: "package-check",
    status: "Ready",
    tone: "ready",
    owner: "Product",
    evidence: "PRD, UX, API, frontend specs aligned",
    gap: "Pilot feedback pending",
    items: ["State correlation", "Explainable productivity", "Real-time dashboards", "Alerts", "Basic reporting"]
  },
  {
    title: "Database Domains",
    icon: "database",
    status: "Designed",
    tone: "progress",
    owner: "Data Engineering",
    evidence: "Core tables, event domains, snapshots, indexes defined",
    gap: "Migration scripts and seed data still required",
    items: ["Organizations", "Employees", "Events", "State snapshots", "Conflicts", "Reports"]
  },
  {
    title: "Security Architecture",
    icon: "lock-keyhole",
    status: "Review Required",
    tone: "blocked",
    owner: "Security",
    evidence: "RBAC, tenant isolation, audit, encryption, endpoint boundaries defined",
    gap: "Pen test and tenant-boundary tests not complete",
    items: ["RBAC", "Tenant isolation", "Audit logs", "Encryption", "Security alerts"]
  },
  {
    title: "Infrastructure",
    icon: "server-cog",
    status: "Gated",
    tone: "blocked",
    owner: "Platform",
    evidence: "Kubernetes, node pools, WAF, backups, Terraform modules defined",
    gap: "DR test and backup restore validation required",
    items: ["Kubernetes", "Multi-AZ", "WAF", "Backups", "Terraform"]
  },
  {
    title: "QA Strategy",
    icon: "test-tube-2",
    status: "In Progress",
    tone: "progress",
    owner: "QA",
    evidence: "Test pyramid, API, event, rule, correlation cases defined",
    gap: "Automation suite and coverage reporting not wired",
    items: ["70% unit", "20% integration", "10% E2E", "API tests", "Rule accuracy"]
  },
  {
    title: "Commercialization",
    icon: "badge-dollar-sign",
    status: "Pilot Ready",
    tone: "ready",
    owner: "Commercial",
    evidence: "Packaging, ROI model, pilot motion, customer success services defined",
    gap: "Final pricing approval and sales collateral pending",
    items: ["Foundation", "Professional", "Enterprise", "Pilot model", "Expansion model"]
  }
];

export const explainabilityTrust = [
  { label: "Explainable findings", value: "100%", target: "Every score has evidence" },
  { label: "Rule traceability", value: "100%", target: "Rule, version, conditions" },
  { label: "Evidence export", value: "Ready", target: "Audit-ready conflict packets" },
  { label: "Trust KPI", value: "Repeatable", target: "Same inputs, same result" }
];

export const stateCorrelation = [
  { source: "Workstation", state: "LOCKED", confidence: 95 },
  { source: "TCN Dialer", state: "READY", confidence: 98 },
  { source: "Attendance", state: "CLOCKED_IN", confidence: 94 },
  { source: "Schedule", state: "SCHEDULED", confidence: 91 }
];

export const ruleGovernance = {
  ruleTypes: ["Validation", "Conflict", "Scoring", "Notification", "Escalation", "Suppression"],
  lifecycle: ["Draft", "Testing", "Approval", "Active", "Retired"],
  approval: ["Rule author", "Compliance lead", "Engineering reviewer"]
};

export const onboardingReadiness = [
  { phase: "Discovery", status: "Current KPIs, systems, risks" },
  { phase: "Security Approval", status: "Firewall, proxy, SSO, privacy review" },
  { phase: "Rule Workshop", status: "Customer rule catalog and escalation paths" },
  { phase: "Agent Validation", status: "Deployment, heartbeat, event verification" },
  { phase: "Production Activation", status: "Dashboards, alerts, reports enabled" },
  { phase: "Customer Success", status: "Health score, feedback loop, expansion" }
];

export const sprintRoadmap = [
  { sprint: "Sprint 0", focus: "Engineering foundations, repository, CI/CD, database, UX, QA" },
  { sprint: "Sprint 1", focus: "Authentication and security foundation" },
  { sprint: "Sprint 2", focus: "Employees, users, dashboard shell" },
  { sprint: "Sprint 3", focus: "Workstation Agent API and persistence" },
  { sprint: "Sprint 5", focus: "State correlation and validation engine" },
  { sprint: "Sprint 6", focus: "Rule engine, rule builder, rule execution" }
];

export const productionChecklist = [
  "Multi-AZ enabled",
  "Backups validated",
  "Monitoring operational",
  "Alerting operational",
  "Secrets externalized",
  "WAF enabled",
  "SSL enabled",
  "DR tested",
  "Vulnerability scan passed",
  "Penetration test completed"
];

export const v1Modules = [
  {
    title: "Employees",
    icon: "users",
    value: "842",
    status: "Active directory",
    href: "#employees",
    items: ["Employee list", "Profile", "Manager mapping"]
  },
  {
    title: "Attendance",
    icon: "calendar-check",
    value: "91%",
    status: "Today adherence",
    href: "#attendance",
    items: ["Clocked in", "Breaks", "Schedule match"]
  },
  {
    title: "Productivity",
    icon: "activity",
    value: "82%",
    status: "Org score",
    href: "#productivity",
    items: ["Trend", "Utilization", "Compliance"]
  },
  {
    title: "Reports",
    icon: "file-bar-chart",
    value: "6",
    status: "Available reports",
    href: "#reports",
    items: ["Generate", "Export", "Download"]
  },
  {
    title: "Users",
    icon: "user-cog",
    value: "124",
    status: "System users",
    href: "#users",
    items: ["Create user", "Status", "Access"]
  },
  {
    title: "Roles",
    icon: "shield-check",
    value: "5",
    status: "RBAC roles",
    href: "#roles",
    items: ["Employee", "Manager", "Admin"]
  }
];

export const attendanceSummary = [
  { label: "Clocked In", value: "812" },
  { label: "On Break", value: "70" },
  { label: "Late", value: "18" },
  { label: "Absent", value: "24" }
];

export const reportSummary = [
  { name: "Daily Productivity", format: "PDF", status: "Ready" },
  { name: "Attendance Summary", format: "Excel", status: "Ready" },
  { name: "Conflict Analysis", format: "CSV", status: "Queued" }
];

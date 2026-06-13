INSERT INTO dashboard_metrics VALUES
('productivity', 'Productivity', '82%', '+4.2%', 'positive', '#productivity', 1),
('compliance', 'Compliance', '91%', '+1.8%', 'positive', '#compliance', 2),
('confidence', 'Confidence', '96%', 'Stable', 'neutral', '#confidence', 3),
('activeUsers', 'Active Users', '842', 'Live', 'positive', '#employees', 4),
('conflicts', 'Conflicts', '45', '+12', 'negative', '#conflicts', 5);

INSERT INTO app_users VALUES
('USR-001', 'admin', 'admin_hash_001', 'ACTIVE', '2026-06-04'),
('USR-002', 'manager', 'manager_hash_001', 'ACTIVE', '2026-06-04'),
('USR-003', 'disabled_user', 'disabled_hash_001', 'INACTIVE', '2026-06-04');

INSERT INTO app_roles VALUES
('ROLE-001', 'Admin'),
('ROLE-002', 'Manager'),
('ROLE-003', 'Supervisor');

INSERT INTO metric_evidence VALUES
('productivity', 'Productive time', '78%', 1),
('productivity', 'Conflict penalty', '-4%', 2),
('productivity', 'Attendance penalty', '-2%', 3),
('compliance', 'State adherence', '94%', 1),
('compliance', 'Schedule match', '89%', 2),
('compliance', 'Open risk', 'Low', 3),
('confidence', 'Event coverage', '99%', 1),
('confidence', 'Source match', '96%', 2),
('confidence', 'Stale data', '1%', 3),
('activeUsers', 'Ready', '618', 1),
('activeUsers', 'On call', '154', 2),
('activeUsers', 'Break', '70', 3),
('conflicts', 'Critical', '12', 1),
('conflicts', 'High', '28', 2),
('conflicts', 'Avg duration', '14m', 3);

INSERT INTO productivity_trend VALUES
('08', 72, 1), ('09', 78, 2), ('10', 82, 3), ('11', 74, 4), ('12', 84, 5),
('13', 86, 6), ('14', 83, 7), ('15', 88, 8), ('16', 85, 9), ('17', 90, 10);

INSERT INTO conflicts VALUES
('John Smith', 'JS', 'READY_LOCKED', 'HIGH', '15m', 98, 'OPEN', 1),
('Avery Jones', 'AJ', 'SCHEDULE_MISMATCH', 'MEDIUM', '9m', 91, 'ACKNOWLEDGED', 2),
('Mina Patel', 'MP', 'IDLE_READY', 'HIGH', '22m', 95, 'INVESTIGATING', 3),
('Carlos Rivera', 'CR', 'ATTENDANCE_GAP', 'MEDIUM', '6m', 88, 'OPEN', 4);

INSERT INTO alerts VALUES
('Productivity drop detected', 'Collections team down 7% in last hour', 'Critical', 'trending-down', 1),
('High conflict volume', '12 unresolved READY_LOCKED conflicts', 'High', 'shield-alert', 2),
('Integration delay', 'TCN queue latency above expected range', 'High', 'plug-zap', 3),
('Rule synchronization complete', '147 active rules loaded into cache', 'Info', 'git-branch', 4);

INSERT INTO workstation_agent_status VALUES
('WPACSAgent', 'WPACS Workstation Monitoring Service', '1.0.0', 'HEALTHY', '60 sec', '<1%', '118 MB', '342 MB');

INSERT INTO workstation_agent_events VALUES
('LOGIN', 1), ('LOGOUT', 2), ('LOCK', 3), ('UNLOCK', 4), ('SHUTDOWN', 5), ('RESTART', 6),
('SESSION_DISCONNECT', 7), ('SESSION_RECONNECT', 8), ('IDLE_START', 9), ('IDLE_END', 10);

INSERT INTO workstation_agent_transport VALUES
('Endpoint', '/agent/v1/events', 1),
('Protocol', 'HTTPS + TLS 1.3', 2),
('Auth', 'JWT', 3),
('Batch size', '100 events', 4),
('Max payload', '1 MB', 5);

INSERT INTO workstation_agent_buffer VALUES
('Storage', 'LiteDB', 1), ('Retention', '72 hours', 2), ('Retry window', '24 hours', 3), ('Offline mode', 'Enabled', 4);

INSERT INTO workstation_agent_safeguards VALUES
('No screenshots', 1), ('No video recording', 2), ('No keystroke capture', 3), ('No clipboard access', 4);

INSERT INTO workstation_agent_deployment VALUES
('Microsoft Intune', 1), ('SCCM', 2), ('Group Policy', 3), ('Manual MSI', 4);

INSERT INTO workstation_agent_tamper VALUES
('Service stop', 1), ('Service disable', 2), ('Configuration modification', 3), ('Agent removal', 4);

INSERT INTO enterprise_readiness_summary VALUES
(74, 'Conditional', 'Ready for controlled pilot, not production go-live', 4, 'Security review and restore test');

INSERT INTO enterprise_readiness VALUES
('product', 'Product Scope', 'package-check', 'Ready', 'ready', 'Product', 'PRD, UX, API, frontend specs aligned', 'Pilot feedback pending', 1),
('database', 'Database Domains', 'database', 'Designed', 'progress', 'Data Engineering', 'Core tables, event domains, snapshots, indexes defined', 'Migration scripts and seed data still required', 2),
('security', 'Security Architecture', 'lock-keyhole', 'Review Required', 'blocked', 'Security', 'RBAC, tenant isolation, audit, encryption, endpoint boundaries defined', 'Pen test and tenant-boundary tests not complete', 3),
('infrastructure', 'Infrastructure', 'server-cog', 'Gated', 'blocked', 'Platform', 'Kubernetes, node pools, WAF, backups, Terraform modules defined', 'DR test and backup restore validation required', 4),
('qa', 'QA Strategy', 'test-tube-2', 'In Progress', 'progress', 'QA', 'Test pyramid, API, event, rule, correlation cases defined', 'Automation suite and coverage reporting not wired', 5),
('commercial', 'Commercialization', 'badge-dollar-sign', 'Pilot Ready', 'ready', 'Commercial', 'Packaging, ROI model, pilot motion, customer success services defined', 'Final pricing approval and sales collateral pending', 6);

INSERT INTO enterprise_readiness_items VALUES
('product', 'State correlation', 1), ('product', 'Explainable productivity', 2), ('product', 'Real-time dashboards', 3), ('product', 'Alerts', 4), ('product', 'Basic reporting', 5),
('database', 'Organizations', 1), ('database', 'Employees', 2), ('database', 'Events', 3), ('database', 'State snapshots', 4), ('database', 'Conflicts', 5), ('database', 'Reports', 6),
('security', 'RBAC', 1), ('security', 'Tenant isolation', 2), ('security', 'Audit logs', 3), ('security', 'Encryption', 4), ('security', 'Security alerts', 5),
('infrastructure', 'Kubernetes', 1), ('infrastructure', 'Multi-AZ', 2), ('infrastructure', 'WAF', 3), ('infrastructure', 'Backups', 4), ('infrastructure', 'Terraform', 5),
('qa', '70% unit', 1), ('qa', '20% integration', 2), ('qa', '10% E2E', 3), ('qa', 'API tests', 4), ('qa', 'Rule accuracy', 5),
('commercial', 'Foundation', 1), ('commercial', 'Professional', 2), ('commercial', 'Enterprise', 3), ('commercial', 'Pilot model', 4), ('commercial', 'Expansion model', 5);

INSERT INTO explainability_trust VALUES
('Explainable findings', '100%', 'Every score has evidence', 1),
('Rule traceability', '100%', 'Rule, version, conditions', 2),
('Evidence export', 'Ready', 'Audit-ready conflict packets', 3),
('Trust KPI', 'Repeatable', 'Same inputs, same result', 4);

INSERT INTO state_correlation VALUES
('Workstation', 'LOCKED', 95, 1),
('TCN Dialer', 'READY', 98, 2),
('Attendance', 'CLOCKED_IN', 94, 3),
('Schedule', 'SCHEDULED', 91, 4);

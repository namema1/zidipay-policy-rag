# Incident Response and Business Continuity

**Document ID:** ZDP-SEC-002
**Effective date:** 2024-05-01
**Owner:** CISO and Head of SRE
**Applies to:** All Zidipay employees; specifically binding on Engineering, Security, Support, and on-call rotations

## 1. Purpose

This policy defines how Zidipay detects, classifies, responds to, and recovers from incidents — whether security incidents, production outages, or events that threaten business continuity. It is the on-call playbook.

## 2. Definitions

- **Incident** — any unplanned event that disrupts a Zidipay service or compromises the confidentiality, integrity, or availability of Zidipay or customer data.
- **Major incident** — Sev 1 or Sev 2 as defined in §3.
- **Recovery Time Objective (RTO)** — the maximum time within which a service must be restored after an incident.
- **Recovery Point Objective (RPO)** — the maximum amount of data loss measured in time that is tolerable.

## 3. Severity levels

| Severity | Definition | Examples | RTO | RPO |
| --- | --- | --- | --- | --- |
| **Sev 1** | Customer-facing outage, regulatory data loss, or confirmed breach of Restricted data | Wallet payments down across all markets, breach of customer KYC database | **30 minutes** | **5 minutes** |
| **Sev 2** | Significant degradation or partial outage affecting many customers | Payments degraded in one country, dashboard down for merchants | **2 hours** | **15 minutes** |
| **Sev 3** | Minor disruption, single-tenant or non-customer-facing | Internal admin tool down, one merchant integration failing | **8 hours** | **1 hour** |
| **Sev 4** | Cosmetic or low-impact | UI glitch, non-urgent alert | Next business day | n/a |

## 4. Reporting and escalation

- **Suspected security incident** (lost device, phishing, suspected breach, unauthorised access): call **+254 711 000 999** within 60 minutes of discovery and email security@zidipay.example.
- **Production incident**: declare in #incident-bridge in Slack; the on-call SRE will page in incident command.
- **Customer data breach**: the CISO must be informed immediately and, per the `Data Protection and Privacy Policy`, regulators (Office of the Data Protection Commissioner in Kenya, equivalents in UG/TZ/RW) must be notified within **72 hours**.

The incident commander (IC) is responsible for severity classification, comms, and the timeline of decisions. The IC is typically the on-call SRE for production incidents and the on-call Security Engineer for security incidents.

## 5. Roles during an incident

- **Incident Commander (IC):** owns the response, makes calls, runs the bridge.
- **Communications Lead:** drafts customer comms and status-page updates; for Sev 1/2 this is the on-call PMM during business hours and the IC otherwise.
- **Scribe:** keeps a timestamped log in the incident channel.
- **Subject-matter experts (SMEs):** pulled in by the IC.

## 6. Business continuity and disaster recovery

- Production services run in multi-AZ within a single primary cloud region (af-south-1) with hot standby in eu-west-1.
- Encrypted, cross-region backups are taken **every 15 minutes** for the transaction database, **hourly** for the customer database, and **daily** for analytics warehouses.
- Disaster recovery exercises are run twice a year, including a full region-failover drill in Q2 and a tabletop in Q4.

## 7. Crisis communications

For Sev 1 and Sev 2 incidents:

- Customer comms must go out on the public status page within **30 minutes** of declaration.
- Regulator comms must go out within the relevant statutory window (72 hours for personal data breaches in Kenya under the Data Protection Act, 2019).
- All-hands internal comms is sent by the CEO or COO.

## 8. Post-incident review

Every Sev 1 and Sev 2 incident has a blameless post-incident review (PIR) within **5 working days**. The PIR is written by the IC, reviewed by Engineering Leadership, and the action items are tracked to completion. Sev 3 incidents have a lightweight write-up; Sev 4 incidents may be summarised in the on-call hand-off.

## 9. Records and retention

Incident records (timeline, decisions, PIR) are retained for **7 years** per the audit and regulatory requirement. Customer comms and regulator filings are retained for the longer of 7 years or the period required by the relevant statute.

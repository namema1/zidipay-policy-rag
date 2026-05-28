# Onboarding and Offboarding Procedure

**Document ID:** ZDP-HR-005
**Effective date:** 2024-04-01
**Owner:** People Operations, with IT and Security
**Applies to:** All Zidipay employees, contractors, and interns

## 1. Purpose

This document defines the end-to-end procedure for joining and leaving Zidipay. It is the master checklist used by People Ops, IT, Security, and managers.

## 2. Pre-start (day −7 to day −1)

People Operations:

- Confirm written acceptance of the offer letter and that pre-employment checks (right to work, references, statutory KYC for staff handling customer funds) are complete.
- Send a welcome email with first-day logistics 5 working days before the start date.
- Create the HRMS record so payroll, leave, and benefits can be configured.

IT and Security:

- Order the hardware (laptop, monitor, headset) so it arrives or is available on day 1.
- Provision the @zidipay.example email, Slack, Google Workspace, and 1Password accounts based on role.
- Issue the YubiKey hardware token (see `Information Security Policy`).
- Apply role-based access groups (see §4) — production access is **not** granted at this stage.

## 3. Day 1 to week 1

- Manager runs a 1:1 to set 30-60-90-day goals.
- Buddy is introduced (every new joiner is paired with a buddy outside their direct reporting line).
- Mandatory training is assigned and must be completed in the first 14 days:
  - Information security and acceptable use.
  - AML and KYC awareness (everyone, regardless of role).
  - Data protection and privacy.
  - Anti-bribery and code of conduct.
- A test run of MFA and VPN is completed with IT.

## 4. Access provisioning

Access follows the principle of **least privilege**.

| Access | Default at start | How to escalate |
| --- | --- | --- |
| Email, Slack, Drive, HRMS | Granted on day 1 | n/a |
| Engineering tooling (GitHub, CI) | Granted on day 1 for engineers | n/a |
| Production read-only | Requires manager + Security approval after onboarding training | IT Service Desk ticket |
| Production write / on-call | Requires shadowing of an existing on-call, plus Security approval | IT Service Desk ticket |
| Customer data (Restricted) | Need-to-know only; named approval logged in SIEM | IT Service Desk ticket |

Quarterly access reviews are run by Security; managers must confirm or revoke direct reports' access within 7 calendar days of the review going out.

## 5. Probation

The standard probation period is **3 months** (extendable once by 1 month with written reason). At the end of probation, the manager completes a probation review with HRBP. Confirmation, extension, or termination is decided at that review.

## 6. Resignation and offboarding

When an employee resigns or is given notice:

1. **Day of notice:** People Operations records the leave date and notifies the manager, IT, Finance, and Security.
2. **Notice period:** standard notice is **30 calendar days** for non-managers and **60 calendar days** for managers and Level 4+, unless the contract states otherwise. Either party may agree to a shorter notice in writing.
3. **Handover:** the manager and employee complete a written handover document, including projects, on-call schedule, customer contacts, and access map. Handover is reviewed at least one week before the last day.
4. **Last week:** IT confirms which equipment is to be returned and arranges courier collection if remote.
5. **Last day:**
   - All access is disabled at 17:00 local time of the last working day. This is mandatory regardless of how amicable the departure.
   - YubiKey, laptop, monitor, and any physical access cards are returned.
   - Personal data on the laptop is wiped after a 14-day grace period during which any work artefacts can be retrieved.
   - Exit interview is scheduled within 5 working days.

## 7. Final pay and accrued leave

Final pay (including any unpaid expenses and accrued unused annual leave per the `PTO and Leave Policy`) is processed in the next payroll run after the last working day, or sooner where local law requires.

## 8. Post-employment obligations

Confidentiality, IP assignment, and any non-solicit clauses in the employment agreement survive employment. Former employees must continue to protect Restricted and Confidential data they came into contact with.

## 9. Contractors and interns

Contractors and interns follow the same access principles. Their access ends on the contract end date and Finance is alerted automatically by the HRMS.

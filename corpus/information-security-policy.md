# Information Security Policy

**Document ID:** ZDP-SEC-001
**Effective date:** 2024-01-15
**Owner:** Chief Information Security Officer
**Applies to:** All employees, contractors, and third parties with access to Zidipay systems or data

## 1. Purpose and scope

Zidipay processes regulated financial data on behalf of millions of customers. This policy sets the minimum security standards every employee must follow to protect that data and our systems.

## 2. Passwords and authentication

- Use a unique passphrase of **at least 14 characters** for every Zidipay account. Reuse of passwords across systems is prohibited.
- Use the company-issued password manager (1Password) to store passwords. Browser-saved passwords are not permitted on work accounts.
- **Multi-factor authentication (MFA) is mandatory** for every Zidipay system. The only approved second factor is the **YubiKey hardware token** issued during onboarding. SMS-based MFA is explicitly prohibited because of SIM-swap risk.
- Passwords must be changed immediately if compromise is suspected and otherwise are not on a fixed rotation schedule.

## 3. Data classification

All Zidipay data is classified into one of four tiers:

| Tier | Examples | Storage rules |
| --- | --- | --- |
| **Public** | marketing pages, job ads | No restriction |
| **Internal** | meeting notes, OKRs | Inside Zidipay tooling only; not shared externally |
| **Confidential** | financials, contracts, employee data | Need-to-know; encrypted at rest and in transit; do not store on personal devices |
| **Restricted** | customer PII, KYC documents, transaction PANs, secrets, audit logs | Need-to-know; access logged; data masked in non-production; never copied to a laptop |

When in doubt, treat data as **Confidential**. Customer personally identifiable information is **always Restricted**.

## 4. Acceptable use highlights

The full rules are in the `Acceptable Use and Device Policy`. Key points:

- Only company-managed laptops and mobile devices may access Zidipay production systems.
- Never disable disk encryption (FileVault on macOS, BitLocker on Windows) or the EDR agent.
- Do not connect Zidipay devices to public charging ports ("juice jacking" risk).
- Do not install unapproved software. The approved-software list is in IT Service Desk.

## 5. Network and remote access

- VPN (Tailscale, deployed at onboarding) is required for access to production from outside Zidipay offices.
- Public Wi-Fi is permitted only over VPN.
- SSH access to production hosts is gated by short-lived (≤8 hour) certificates issued by Vault.

## 6. Encryption

- Customer data is encrypted at rest with AES-256 and in transit with TLS 1.2 or higher.
- All Zidipay laptops have full-disk encryption enabled and verified at onboarding.
- Backups are encrypted with separate keys held by the Security team.

## 7. Software supply chain

- Production code is deployed only from the `main` branch of the official Zidipay GitHub organisation after passing CI checks, code review by at least one other engineer, and automated SAST and dependency scanning.
- Third-party libraries must be approved through the vendor-review process if they handle Restricted data.

## 8. Logging and monitoring

- Access to Restricted data is logged in the central SIEM and reviewed weekly by the Security team.
- Production changes are logged in the deploy log and tied to a pull request.

## 9. Incident reporting

Any suspected security incident — including phishing attempts, lost devices, suspected malware, unauthorised access, and accidental disclosure of customer data — must be reported **within 60 minutes of discovery**:

- Email **security@zidipay.example**, or
- Call the 24/7 security hotline **+254 711 000 999**.

Do not attempt to investigate or remediate the incident yourself. The on-call security engineer will lead the response. See the `Incident Response and Business Continuity` policy for severity definitions and the full process.

## 10. Sanctions for non-compliance

Breaches of this policy may result in disciplinary action up to and including dismissal, and where the law requires it, criminal referral.

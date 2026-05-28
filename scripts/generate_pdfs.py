"""Generate the AML/KYC and Anti-Bribery PDFs in the corpus from inline text.

Run once to (re)create the PDF files. Idempotent.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
)


ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
CORPUS.mkdir(exist_ok=True)


def _styles():
    base = getSampleStyleSheet()
    styles = {
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontSize=18,
            spaceAfter=14,
            leading=22,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontSize=14,
            spaceBefore=14,
            spaceAfter=8,
            leading=18,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontSize=12,
            spaceBefore=10,
            spaceAfter=6,
            leading=16,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontSize=10.5,
            leading=15,
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=base["BodyText"],
            fontSize=10,
            leading=14,
            textColor="#444444",
            spaceAfter=10,
        ),
    }
    return styles


def render(path: Path, blocks: list[tuple[str, str]]) -> None:
    """blocks: list of (style_key, text)."""
    styles = _styles()
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=path.stem.replace("-", " ").title(),
    )
    flow = []
    for kind, text in blocks:
        if kind == "pagebreak":
            flow.append(PageBreak())
            continue
        if kind == "spacer":
            flow.append(Spacer(1, 8))
            continue
        flow.append(Paragraph(text, styles[kind]))
    doc.build(flow)


# -----------------------------------------------------------------------------
# AML / KYC policy
# -----------------------------------------------------------------------------

AML_BLOCKS: list[tuple[str, str]] = [
    ("h1", "Zidipay AML and KYC Policy"),
    ("meta", "Document ID: ZDP-COMP-001 &nbsp;&nbsp;|&nbsp;&nbsp; Effective date: 2024-04-01 &nbsp;&nbsp;|&nbsp;&nbsp; Owner: Money Laundering Reporting Officer (MLRO)"),
    ("meta", "Applies to: All Zidipay employees; specifically binding on Operations, Compliance, Customer Support, and Engineering teams that handle customer onboarding, payments, or monitoring systems."),

    ("h2", "1. Purpose"),
    ("body",
     "Zidipay is committed to preventing, detecting, and reporting money laundering, terrorist financing, "
     "and sanctions breaches. This policy sets out the customer due diligence (CDD), transaction monitoring, "
     "and reporting obligations of the company and of every employee. It is designed to satisfy the Proceeds "
     "of Crime and Anti-Money Laundering Act (Kenya), the Central Bank of Kenya AML guidelines, and equivalent "
     "regulations in Uganda, Tanzania, and Rwanda."),

    ("h2", "2. Customer due diligence (CDD)"),
    ("body",
     "Zidipay applies a risk-based CDD programme. Every customer is screened at onboarding and on an "
     "ongoing basis. CDD has three levels — standard, simplified, and enhanced — applied according to the "
     "assessed risk of the customer, the product, and the geography."),

    ("h3", "2.1 Standard CDD"),
    ("body",
     "Applied to all individual customers. Standard CDD requires: full legal name; date of birth; nationality; "
     "national identity document number (or passport for non-citizens); residential address; mobile number; "
     "and the source of funds where transaction volumes exceed the Tier 1 threshold."),

    ("h3", "2.2 Simplified CDD"),
    ("body",
     "Permitted for low-risk customers transacting only within the Tier 1 wallet, where the assessed money "
     "laundering risk is low and other CDD elements have been satisfied. ID alone is sufficient for Tier 1."),

    ("h3", "2.3 Enhanced CDD"),
    ("body",
     "Required for: politically exposed persons (PEPs) and their close associates; customers from "
     "higher-risk jurisdictions on the FATF grey or black list; customers triggering ongoing-monitoring "
     "alerts; and all customers at Tier 3. Enhanced CDD includes: proof of source of funds and wealth; "
     "senior-management sign-off to onboard or continue the relationship; and increased monitoring frequency."),

    ("h2", "3. KYC tiers and limits"),
    ("body",
     "Zidipay wallets are organised into three KYC tiers. Limits below are denominated in Kenyan shillings "
     "for the Kenyan wallet; equivalent amounts apply in UG, TZ, and RW per the country addenda."),
    ("h3", "Tier 1 — basic"),
    ("body",
     "Maximum daily transaction: KES 50,000. Maximum balance: KES 100,000. Required documents: government-issued "
     "ID only. Permitted activities: send, receive, pay merchants. Not permitted: international transfers, payouts to bank."),
    ("h3", "Tier 2 — verified"),
    ("body",
     "Maximum daily transaction: KES 500,000. Maximum balance: KES 1,000,000. Required documents: government-issued ID "
     "and proof of address (utility bill or bank statement not older than 3 months). Permitted activities: as Tier 1 plus "
     "domestic bank payouts and merchant settlement."),
    ("h3", "Tier 3 — full"),
    ("body",
     "Maximum daily transaction: no fixed limit (subject to monitoring). Required documents: as Tier 2 plus proof of source of funds, "
     "selfie liveness check, and enhanced screening. Permitted activities: as Tier 2 plus international transfers and FX."),

    ("h2", "4. Sanctions screening"),
    ("body",
     "All new customers and counterparties are screened against the UN Consolidated List, the OFAC SDN List, the EU consolidated list, "
     "the UK HMT list, and Kenya's Counter-Financing of Terrorism list at onboarding. Existing customers are rescreened daily against "
     "updates to those lists. A confirmed positive sanctions match triggers an immediate freeze of the account, escalation to the MLRO, "
     "and a Suspicious Transaction Report (STR) where required by law."),

    ("pagebreak", ""),

    ("h2", "5. Transaction monitoring"),
    ("body",
     "Zidipay operates a real-time transaction monitoring system (TMS) that scores every transaction for AML risk "
     "using rules and machine-learning models. Alerts are queued to the Financial Crime Operations team for review "
     "within service levels of: 4 hours for high-priority alerts, 24 hours for medium, and 72 hours for low. "
     "Reviewers may request additional information from the customer, escalate to the MLRO, or close the alert "
     "with a documented rationale. All alert decisions are auditable."),

    ("h2", "6. Suspicious Transaction Reports (STRs)"),
    ("body",
     "Any employee who knows or suspects, or has reasonable grounds to know or suspect, that funds being handled by "
     "Zidipay are the proceeds of crime or are related to terrorist financing must file an internal report to the MLRO "
     "via the dedicated 'STR' channel in the Compliance ticketing system. Tipping off the customer is a criminal "
     "offence in all our jurisdictions. The MLRO determines whether to file an external STR with the Financial Reporting "
     "Centre (FRC) in Kenya or the equivalent Financial Intelligence Unit in UG, TZ, RW. External STRs must be filed "
     "within 7 calendar days of the MLRO's decision unless the law specifies a shorter window."),

    ("h2", "7. Training"),
    ("body",
     "Every employee completes AML and KYC awareness training in the first 14 days of joining and refresher training "
     "annually. Customer-facing and high-risk roles complete role-specific training, with assessments. Records of "
     "training completion and assessment scores are kept by People Operations and made available to regulators on request."),

    ("h2", "8. Record keeping"),
    ("body",
     "Zidipay retains CDD records for a minimum of 7 years from the end of the customer relationship and transaction "
     "records for 7 years from the date of the transaction, in line with the Data Protection and Privacy Policy. "
     "Records may be retained for longer where an investigation or regulator request requires it."),

    ("h2", "9. Governance"),
    ("body",
     "The MLRO is the senior officer accountable for the company's AML programme and reports directly to the Board "
     "Audit and Risk Committee. The Compliance team operates the day-to-day programme; Internal Audit reviews the "
     "programme at least annually. External independent reviews are commissioned every 24 months."),

    ("h2", "10. Sanctions for non-compliance"),
    ("body",
     "Failure to comply with this policy is grounds for disciplinary action up to and including dismissal. Several "
     "breaches (tipping off, deliberate failure to file an STR, sanctions evasion) are criminal offences and will be "
     "reported to the authorities."),
]


# -----------------------------------------------------------------------------
# Anti-Bribery and Code of Conduct policy
# -----------------------------------------------------------------------------

AB_BLOCKS: list[tuple[str, str]] = [
    ("h1", "Zidipay Anti-Bribery Policy and Code of Conduct"),
    ("meta", "Document ID: ZDP-COMP-002 &nbsp;&nbsp;|&nbsp;&nbsp; Effective date: 2024-04-15 &nbsp;&nbsp;|&nbsp;&nbsp; Owner: General Counsel"),
    ("meta", "Applies to: All Zidipay employees, contractors, interns, directors, and third parties acting on Zidipay's behalf."),

    ("h2", "1. Purpose"),
    ("body",
     "Zidipay does not tolerate bribery or corruption in any form. This policy sets out the standards every "
     "person acting for Zidipay must follow, the rules on gifts and hospitality, conflicts of interest, "
     "political and charitable contributions, and the consequences of breaching them. It is consistent with "
     "the Bribery Act, 2010 (UK) extraterritorial provisions, the Foreign Corrupt Practices Act (US), and "
     "the Anti-Corruption and Economic Crimes Act, 2003 (Kenya)."),

    ("h2", "2. What is prohibited"),
    ("body",
     "Bribery is offering, giving, receiving, or soliciting any item of value — money, gifts, hospitality, services, "
     "favours, or anything else — in order to improperly influence a decision. It is prohibited whether the other "
     "party is a private individual, a customer, a partner, a competitor, or a public official, and regardless of "
     "whether the bribe is paid directly or through a third party. Facilitation payments — small unofficial payments "
     "to expedite a routine service — are also prohibited."),

    ("h2", "3. Gifts and hospitality"),
    ("body",
     "Modest gifts and hospitality that are reasonable, proportionate, and given in the ordinary course of business "
     "are permitted, provided they:"),
    ("body",
     "(a) are not cash or cash equivalents (vouchers, gift cards, cryptocurrency);<br/>"
     "(b) cannot reasonably be seen as influencing a decision;<br/>"
     "(c) are not given or received during an active procurement or tender process;<br/>"
     "(d) are disclosed in the Gifts and Hospitality Register where they exceed the de minimis threshold below."),

    ("h3", "3.1 De minimis threshold"),
    ("body",
     "Gifts received with a value of KES 5,000 or more (per item, per giver, per year) must be reported by the "
     "recipient to People Operations within 7 days using the Gifts and Hospitality form. Gifts of KES 25,000 or "
     "more require pre-approval from the line manager and Compliance, or must be politely declined."),

    ("h3", "3.2 Public officials"),
    ("body",
     "No gift, hospitality, or anything of value of any amount may be given to or received from a public official "
     "without prior written approval from the General Counsel and Compliance. This includes regulators, central bank "
     "staff, and elected officials in any jurisdiction Zidipay operates in."),

    ("h2", "4. Conflicts of interest"),
    ("body",
     "A conflict of interest is any situation in which an employee's personal interests, relationships, or outside "
     "activities could improperly influence — or appear to improperly influence — the employee's judgement on behalf "
     "of Zidipay. Examples include: outside employment with a competitor, supplier, or customer; close personal "
     "relationships with people in the same management chain; ownership of a meaningful stake in a vendor; or accepting "
     "a board seat at another company."),

    ("body",
     "Every employee must disclose any actual, potential, or perceived conflict of interest in writing to People "
     "Operations within 7 days of becoming aware of it. People Operations, in consultation with the General Counsel, "
     "will determine the appropriate mitigation — which may include reassignment, recusal from specific decisions, "
     "divestment, or in extreme cases termination of employment."),

    ("pagebreak", ""),

    ("h2", "5. Political and charitable contributions"),
    ("body",
     "Zidipay does not make political contributions of any kind, in cash or in kind, to political parties, candidates, "
     "or campaigns in any jurisdiction. Personal political contributions by employees are permitted in a personal "
     "capacity but must not use Zidipay funds, resources, time, or branding."),
    ("body",
     "Charitable contributions are made through the Zidipay Foundation, governed by its own charter. Ad hoc charitable "
     "donations using company funds, on Zidipay branding, or that could reasonably be linked to a business decision, "
     "must be pre-approved by the General Counsel."),

    ("h2", "6. Third parties and agents"),
    ("body",
     "Zidipay can be held liable for bribery committed by third parties on its behalf — agents, distributors, partners, "
     "consultants. Every third party that acts on Zidipay's behalf must be onboarded through the vendor process, including "
     "anti-bribery due diligence proportionate to the risk, and must sign Zidipay's Anti-Bribery clause as part of the contract. "
     "Payments to agents are scrutinised for unusual fees, off-book payments, or invoices that do not describe the service performed."),

    ("h2", "7. Code of Conduct"),
    ("body",
     "In addition to the bribery-specific rules above, the Code of Conduct requires every Zidipay person to:"),
    ("body",
     "(a) treat colleagues, customers, partners, and the public with dignity and respect;<br/>"
     "(b) refrain from any form of harassment, discrimination, or retaliation;<br/>"
     "(c) protect Zidipay's and our customers' information (see the Information Security Policy and the Data Protection and Privacy Policy);<br/>"
     "(d) act honestly in all dealings, including with regulators and auditors;<br/>"
     "(e) follow the laws of every jurisdiction Zidipay operates in."),

    ("h2", "8. Reporting concerns"),
    ("body",
     "Anyone who suspects a breach of this policy should report it. Reports can be made:"),
    ("body",
     "(a) to your manager, or to People Operations;<br/>"
     "(b) to the Compliance team at compliance@zidipay.example;<br/>"
     "(c) confidentially via the whistleblowing hotline +254 711 000 911 (24/7) or whistleblow@zidipay.example."),
    ("body",
     "Reports made in good faith are protected — no retaliation will be tolerated. The protection extends to current "
     "employees, former employees, contractors, and applicants."),

    ("h2", "9. Investigations and sanctions"),
    ("body",
     "Suspected breaches are investigated by Compliance, with the support of Internal Audit and external counsel where "
     "appropriate. Confirmed breaches may result in disciplinary action up to and including dismissal, recovery of losses, "
     "termination of contracts, and criminal referral. Several breaches under this policy are criminal offences and Zidipay "
     "will cooperate fully with prosecuting authorities."),

    ("h2", "10. Training and certification"),
    ("body",
     "Every Zidipay employee completes anti-bribery and code of conduct training in their first 14 days, with annual "
     "refresher and certification thereafter. Customer-facing, procurement, and senior roles complete role-specific "
     "training. Completion records are kept by People Operations."),
]


def main() -> None:
    out_aml = CORPUS / "aml-kyc-policy.pdf"
    out_ab = CORPUS / "anti-bribery-and-code-of-conduct.pdf"
    render(out_aml, AML_BLOCKS)
    render(out_ab, AB_BLOCKS)
    print(f"Wrote {out_aml.relative_to(ROOT)}")
    print(f"Wrote {out_ab.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

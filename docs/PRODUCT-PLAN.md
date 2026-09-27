# Aid Atlas product direction

## Brief
A public-interest legal technology platform for legal aid societies and nonprofits. The website should show the work on the landing page, not merely advertise a hypothetical chatbot. Visual direction: orange, rose, plum, white serif wordmark, original four-part mark, frosted glass masthead and footer. Product presentation informed by Harvey and Legora; UI reference research through Mobbin.

## Implemented frontend
- Large colored masthead with glass Aid Atlas logo; matching navigation identity and oversized frosted footer.
- Three scripted interactive demos: intake preparation, source-based operational research, and consent-confirmed fictional branch handoffs.
- Local/society/state coordination explorer.
- Validated capacity scenario calculator with downloadable assumptions and limitations.
- Downloadable pilot brief, privacy dialog, responsive navigation, reduced-motion support, progressive workflow scroll state.
- Prior applicant planner, CSV research lab, and budget capacity studio preserved in workspace.html, with matching color treatment and hash navigation.

## Proposed production architecture — not implemented
1. Society tenant and branch-scoped workspaces. A tenant is an organization with explicit ownership, data region, retention, and policies; branch access is separately granted.
2. Versioned intake policy and assistance rules owned by authorized staff, scoped by program, funding source, matter type, and jurisdiction. No blanket universal eligibility score.
3. Document ingestion with permission-aware indexing, malware scanning, PII minimization, source provenance, and version history. Integrate an approved case-management system rather than duplicate its source-of-truth records.
4. Research retrieval restricted to approved, jurisdiction-tagged sources. Include passage citations, retrieval dates, status/currentness checks, uncertainty and abstention, and advocate sign-off. Evaluate citation correctness and authority applicability before production.
5. Authenticated human review for eligibility, conflicts, deadlines, and adverse decisions. Record actor, policy version, source, rationale, and review timestamp in an append-only audit trail.
6. Cross-society referrals require consent, explicit receiving access, acceptance acknowledgement, and expiring document links. State coordinators see de-identified aggregates by default, with small-cell suppression where appropriate; no automatic pooling of client files.
7. Separate analytics from operational matters. Track intake minutes, recontacts, completion, referral acceptance, corrections, missed urgency, research rework, language/accessibility outcomes, and total implementation cost.

## Pilot sequence
Discovery and baseline → synthetic-data prototype review → security/privacy review and limited integration → supervised single-team pilot → matched pre/post operational evaluation → branch expansion → governed statewide federation.

Efficiency hypotheses must be tested. No guaranteed case-volume, legal accuracy, or dollar-saving claims. No current security certifications claimed. Production deployment requires identity, authorization, encryption, logging, backups, incident response, retention, vendor assessment, and jurisdiction-specific review.

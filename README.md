# Aid Atlas

A local legal-aid workbench for applicants, researchers, and society teams.

## Run
Requires Python 3.9 or later. From this folder run:

```sh
python3 server.py --port 8766
```

Open http://127.0.0.1:8766. The server binds to this computer only.

## Working features
- Landing page: orange/rose glass masthead, globe identity, scroll transitions, interactive intake/research/referral demonstrations, jurisdiction map, capacity scenarios, and pilot brief downloads.
- Operations (`system.html`): society and branch filters, aggregate CSV import, operational comparisons, report downloads, saved internal policy drafts, and an activity log.
- Public research: refresh three approved LSC sources, store text snapshots, compare versions, and acknowledge individual change reviews. Optional six-hour refresh runs while the server and computer remain awake. Fetch failures remain visible.
- Research and applicant tools (`workspace.html`): synthetic court-data analysis, anonymized CSV import, applicant preparation checklists, exports, and the supplied research paper.

## Storage and boundaries
Operations data is saved in `.data/atlas.sqlite3`, excluded from Git. Back up this file separately if needed. The applicant tools and landing demos keep entered information in browser memory only. Downloaded files remain on your device.

This is a local prototype, not a production client-record system. Society filters organize records; they are not authenticated access controls. No accounts, real application submission, automated eligibility decision, live AI inference, or case-system integration is implemented. Do not enter confidential client information. Demo societies and metrics are fictional. The map does not represent provider coverage. Public-source changes require human review and do not update internal policy automatically.

Aggregate imports use exactly `branch_id,period,intakes,completed,staff_minutes,recontacts,referrals,accepted_referrals`, with up to 1,200 rows. Existing branch/month rows are replaced. Use the in-app template.

The separate court research CSV uses exactly `representation,severity,incarcerated,guilty_plea,sentence_months`, up to 10,000 anonymized rows. Descriptive differences are not causal estimates.

## Verification
```sh
python3 -m unittest discover -s tests -p 'test_*.py'
node --test tests/impact.test.cjs
```

Research references and design attributions are in `docs/SOURCES.md`. The supplied paper retains its original authorship and rights. State geometry is derived from us-atlas (ISC license) and U.S. Census boundaries.

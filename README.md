# Aid Atlas

Local browser application inspired by Fabio I. Martinenghi's supplied 2026 preprint, *Legal aid eligibility and court outcomes: a design-based double-machine-learning approach*.

## Run
Open index.html directly, or run `python3 -m http.server 8766 --bind 127.0.0.1` from this folder.

## Working features
- Research lab: anonymized CSV import, validation, severity filtering, group rates, conditional sentence means, case-mix comparison, and JSON report export.
- Applicant planner: tailored preparation checklist based on stage and circumstances, checklist completion, text download, and explicit clearing.
- Capacity studio: adjustable budget, hourly cost, demand, and casework hours with capacity calculations.
- Research foundation: attributed paper estimates and source PDF links.

## Boundaries
The included 240 demo records are deterministic synthetic data, not observations from the study. Descriptive group differences are not causal estimates. No DML model, eligibility rules engine, individual risk prediction, actual application submission, authentication, backend, or automatic storage is implemented. Applicant data is never used in research. Refreshing clears entered data. Downloaded files remain on your device.

CSV must have exactly representation,severity,incarcerated,guilty_plea,sentence_months (any order). Representation is aid/private; severity is lower/higher; binary outcomes are 0/1; sentence months is nonnegative and zero for non-incarcerated cases. Maximum 10,000 rows and 2 MB. Include only anonymized records.

## Evidence
Paper Table 4, Panel A (ATT): incarceration -0.097, 95% CI [-0.123,-0.071], N=16,338. Conditional incarceration length +5.791 months, CI [2.628,8.954]. Estimates depend on study design and assumptions. The app makes no claim to improve those estimates.

## GitHub
Create an empty repository, then in this folder:

```sh
git init -b main
git add index.html style.css app.js README.md paper.pdf
git commit -m "Build Aid Atlas local prototype"
git remote add origin https://github.com/YOUR-USERNAME/aid-atlas.git
git push -u origin main
```

The source paper retains its original authorship and rights.

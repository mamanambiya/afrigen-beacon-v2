# Contributing

The repository-root `CONTRIBUTING.md` still governs conduct and review
etiquette. Its commands have drifted; this page is the current mechanics.

## Branch and PR

Never commit to `main`. Branch, push, open a PR:

```bash
git checkout -b fix/<topic> origin/main
git push -u origin fix/<topic>
gh pr create
```

Name the branch after the **surface** you are touching
(`fix/assembly-canonicalisation`), not the fix. Another developer searching for
overlap greps surfaces.

`gh` needs the account that owns the repository. If `gh pr create` says "must be
a collaborator", you are on the wrong one:

```bash
gh auth status
gh auth switch --hostname github.com --user mamanambiya
```

## Before you open it

```bash
python3 -m unittest \
  beacon_api.test_query_semantics beacon_api.test_query_injection \
  beacon_api.test_pagination_filters beacon_api.test_assembly

cd frontend && npm run type-check && npm run lint
```

If you touched query behaviour, also run the tutorial's Steps 7 to 9 against a
local stack and paste the before/after into the PR. Unit tests prove the logic;
only a real query proves the wiring.

## Commit messages

Describe the behaviour change and why it matters, not the diff. State what you
verified. **Never add AI-attribution or "Generated with" footers.**

## What the reviewer will ask

- Did you watch the test fail before implementing?
- If you added a guard, did you mutation-check it?
- Does any parameter get validated and then not applied? That is the defect
  class this project keeps re-learning — see `beacon_api/filters.py`, which
  refuses rather than widens and explains why in its docstring.
- Can this change make the beacon answer a broader question than it was asked?

## The rule that outranks the others

**A wrong "no" is worse than an error.** If the beacon cannot apply a filter,
it must refuse the query. Never drop a parameter and answer anyway — a false
negative is indistinguishable from a true one, nobody reports it, and a
researcher concludes the variant is absent from African reference data.

## Things you may not do without asking

- Merge a PR you did not author
- Tag a release, or deploy to production
- Force-push or delete a shared branch
- Run anything that writes on a production host

Deploy mechanics and gates are in `docs/DEPLOYMENT_PREREQUISITES.md` and
`CLAUDE.md`. Note that `scripts/deploy.sh` is marked do-not-run: it targets a
compose file production does not use, with different volume names.

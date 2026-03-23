# Contributing — Branch & Release Workflow

## Branch model

```
main   ──────────────────────────M1─────────────────────M2──→  tagged releases
                                ↑                       ↑
dev    ──S1──S2──S3─────────────┘──S4──S5──────────────┘──→   integration
          ↑    ↑                     ↑    ↑
       feat-A feat-B              feat-C feat-D
```

| Branch | Purpose | Merge strategy |
|---|---|---|
| `main` | Stable releases only; always tagged | Receives regular merge commits from `dev` |
| `dev` | Integration and testing | Receives squash commits from feature branches |
| `feature/*` | Individual features or fixes | Squash-merged into `dev` when ready |

## Day-to-day: feature work

Always branch from `dev`:

```bash
git checkout dev
git pull origin dev
git checkout -b feature/my-thing
```

Work, commit freely, then open a PR targeting **`dev`**. Use **squash merge** — the entire feature becomes one clean commit on `dev`.

## Releasing: dev → main

When `dev` is stable and ready to release:

1. Open a PR from `dev` → `main`
2. Merge using a **regular merge commit** (GitHub's default "Merge pull request" button — not squash, not rebase)
3. Tag the release on `main`:

```bash
git checkout main
git pull origin main
git tag v1.2.0
git push origin v1.2.0
```

4. Sync `dev` to pick up the merge commit:

```bash
git checkout dev
git merge origin/main
git push origin dev
```

Step 4 is what keeps `dev` from falling behind. The regular merge in step 2 means this is always a clean, conflict-free operation (just one merge commit to absorb).

## Hotfixes

For urgent fixes that can't wait for the next release cycle:

```bash
git checkout main
git pull origin main
git checkout -b hotfix/issue-description
```

Open a PR targeting **`main`**, merge with a **regular merge commit**, tag the patch release, then sync `dev`:

```bash
git checkout dev
git merge origin/main
git push origin dev
```

## Why squash feature→dev but merge dev→main?

Squashing keeps `dev` history readable — one commit per feature rather than every work-in-progress save. Regular merges for `dev → main` preserve `dev`'s commits as ancestors of `main`, so after syncing, `git log origin/main..origin/dev` correctly shows zero commits (branches are in sync). If you squash `dev → main`, git can no longer tell that `dev`'s commits are already in `main`, and the branches appear permanently diverged.

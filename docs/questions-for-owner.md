# Questions for the owner

Judgment calls made while working autonomously, so they're reviewable and reversible. Newest at the top.

## 2026-10-31: Branch naming for items already in progress

**Question:** The autonomous-mode instructions say every queue item gets its own `feature/<short-name>` branch. Items 1 (onboarding) and 2 (human-entry) were already partway done on a branch named `onboarding-slice`, created just before autonomous mode started.

**Choice:** Finished items 1 and 2 on `onboarding-slice` rather than restarting on `feature/onboarding` / `feature/human-entry`, to avoid throwing away committed work. Every queue item from here on (3 onward) uses the `feature/<short-name>` naming exactly as instructed.

**To change it later:** if you want items 1/2 split into separate `feature/`-named branches retroactively, that's a `git branch -m` rename or a cherry-pick — ask and it's a small job, not a rebuild.

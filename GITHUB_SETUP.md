# GitHub Repository Settings Guide

To properly configure your repository for the "Issues Only" approach, follow these steps after pushing your code to GitHub:

## 1. Disable Pull Requests

**Note:** GitHub doesn't allow completely disabling pull requests, but you can make them very difficult to submit:

### Option A: Branch Protection Rules (Recommended)

1. Go to **Settings** → **Branches**
2. Click **Add rule** next to `main` (or your default branch)
3. Under **Protect matching branches**, enable:
   - ☑️ **Require a pull request before merging**
   - ☑️ **Require approvals** (set to 1 or more)
   - ☑️ **Dismiss stale PR approvals when new commits are pushed**
4. Add yourself as the only required reviewer

This effectively blocks PRs because only you can approve them, and you won't.

### Option B: Archive the Repository

If you want to go extreme, you can archive the repository which prevents all PRs:

1. Go to **Settings** → **General**
2. Scroll to **Danger Zone**
3. Click **Archive this repository**

⚠️ **Warning:** This also prevents new issues. Only do this if you want a completely frozen codebase.

## 2. Enable Issues

1. Go to **Settings** → **General**
2. Under **Features**, ensure ☑️ **Issues** is enabled
3. Optionally enable **Discussions** for community Q&A

## 3. Configure Issue Templates

The issue templates you created will automatically appear when users click "New Issue". GitHub will:
- Show the bug report and feature request templates
- Disable blank issues (as configured in `config.yml`)
- Show the contact links you defined

## 4. Add a Repository Description

Add something like this to your repository description:

```
⚠️ Issues only - No PRs accepted. Personal project, limited support.
```

## 5. Repository Topics

Add relevant topics to help people find your project:
- `plex`
- `subtitles`
- `opensubtitles`
- `webhook`
- `docker`
- `self-hosted`

## 6. Set Up Notifications (Optional)

Since you're not accepting PRs, you might want to:

1. Go to **Settings** → **Notifications**
2. Customize what you get notified about
3. Consider watching only the Issues you care about

## What Users Will See

When someone tries to contribute:

1. **Clicking "New Issue"**: They'll see the bug report and feature request templates
2. **Trying to submit a PR**: They'll see your PR template explaining PRs aren't accepted
3. **Forking**: They can still fork and use the code (MIT license allows this)

## Maintenance Tips

- **Triage issues weekly**: Spend 10-15 minutes reviewing new issues
- **Label issues**: Use labels like `bug`, `enhancement`, `wontfix`, `help wanted`
- **Close stale issues**: If an issue is inactive for 30+ days, consider closing it
- **Pin important issues**: Pin critical bugs at the top of the issues page

## Emergency: If Someone Submits a PR Anyway

1. Politely thank them
2. Reference the PR template policy
3. Close the PR without merging
4. Suggest they open an issue instead

Example response:
> "Hi! Thanks for the PR. As mentioned in our [contributing guidelines](link), we don't accept pull requests on this project. Please feel free to open an issue to discuss this change instead. Thanks for understanding!"

## Summary

Your repository is now configured for minimal maintenance while still allowing community feedback. The key is setting clear expectations upfront so users understand the project's nature before engaging.

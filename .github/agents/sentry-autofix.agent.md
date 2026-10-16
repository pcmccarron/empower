---
name: sentry-autofix
description: Investigates a Sentry issue for empower and opens a draft pull request with a minimal fix and regression test.
target: github-copilot
disable-model-invocation: true
mcp-servers:
  sentry:
    type: local
    command: npx
    args:
      - "-y"
      - "@sentry/mcp-server@latest"
      - "--organization-slug=pcmccarron"
      - "--skills=inspect,seer,triage"
    tools: ["*"]
    env:
      SENTRY_ACCESS_TOKEN: ${{ secrets.COPILOT_MCP_SENTRY_ACCESS_TOKEN }}
---

A GitHub issue labeled `sentry` was assigned to you. It was created by the Sentry integration for pcmccarron/empower. Investigate it and act on it.

If this is not a Sentry alert for pcmccarron/empower, stop and make no changes.

1. Extract the Sentry issue short ID or URL from the GitHub issue. Use the Sentry MCP server to get issue details, the latest event, the stack trace, related traces, and Seer's root cause analysis. The server is limited to organization `pcmccarron`. This monorepo can report into more than one project in that organization; use the project named on the issue.
2. Find the root cause in this repository. Empower Plant is a monorepo, and the stack trace names the service directory (`react`, `flask`, `express`, `vue`, `angular`, `next`, `go`, `laravel`, `ruby-on-rails`, `spring-boot`, `spring-boot-otlp`, `aspnetcore`, or `agent`). Change only that service. Write the smallest fix that addresses the root cause. No dependency upgrades unless the dependency is the root cause. No unrelated refactors, formatting changes, or CI edits.
3. Add a regression test that reproduces the error, next to that service's existing tests. Install that service's dependencies if they are missing, then run its tests:
   - `react`: `cd react && CI=true npm test -- --watchAll=false`
   - `express`: `cd express && npm test`
   - `angular`: `cd angular && npm test -- --watch=false --browsers=ChromeHeadless`
   - `ruby-on-rails`: `cd ruby-on-rails && bundle exec rails test`
   - `laravel`: `cd laravel && php artisan test`
   - `agent`: `cd agent && python -m pytest`
   Don't open a pull request if tests fail. Comment on the GitHub issue with the diagnosis and what blocked the fix.
4. Open a draft pull request against master:
   - Title: `fix: <one-line summary> (<SENTRY-SHORT-ID>)`
   - Body: root cause, the fix, the test added, a link to the Sentry issue, a link to the GitHub issue, and the line `Fixes <SENTRY-SHORT-ID>` on its own line
   - Request review from pcmccarron. If the review request fails, continue and mention that in the GitHub issue comment.
5. Use the Sentry MCP server to assign the Sentry issue to peter.mccarron@sentry.io. If the tool requires `user:<id>`, look up that user and assign them.
6. Comment on the GitHub issue with the pull request link.

Stay within this repository. Never merge, force-push, or change CI configuration.

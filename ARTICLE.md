# The Drift-Guard Recipe: State the Rule First, Check the Record After

*By Brennan Zambo, creator of Zambo and of AER-1, the agent execution receipt standard.*

## The problem this recipe solves

Agent drift is the silent failure of agent work. A standing rule holds for months, then the context slips, the agent forgets the rule, and it does the expensive wrong thing instead: wrong sub-agents, wrong model, the check step skipped, the delivery sent before the sign-off. Nothing in the chat announces the change. The operator finds out from the usage bill or the breakage.

The founding story belongs to Austin Wallen of [wally.works](https://wally.works), who sells AI-agent software to small businesses. His setup ran on one hard rule: the orchestrator plans and holds no tools, named executor sub-agents do the work. It held for months. Then his agent drifted, executed with the wrong sub-agents, and destroyed his usage. Austin named the fix: **zamback**. Getcha agent ZAMBACK.

Zamback is a pattern, not a product: write the rule into the job before the run, record every step, check the record against the rule, hand the record over. This article packages that pattern as a starter recipe in the exact format of the [Zambo workflow library](https://zambo.dev/workflows/tasks/), so any agent that can read the library can run the guard on any job, starting today.

## The recipe

**Agent Drift Guard** ([agent-drift-guard.v1.json](https://github.com/zambodotdev/zamback-kit/blob/main/recipes/agent-drift-guard.v1.json)) is a versioned recipe file in the library's published format. It validates clean against the library's own schema ([schema.v1.json](https://zambo.dev/workflows/recipes/schema.v1.json), checked with a real schema validator on November 16, 2026), the same format as the library's 2,048 starter recipes in 64 guides. A changed recipe ships as a new version; the v1 file stays addressable, so a job run under it can be reconstructed version by version.

It takes three inputs:

1. **standing_rule**: the one rule whose violation costs you money, in a sentence a checker can judge.
2. **job_goal**: what this job must accomplish.
3. **work_scope**: the steps, tools, or phases the rule binds.

And it runs four steps:

1. **state_the_rule.** Open the job by stating the standing rule together with the goal, before any work runs. The rule is sealed into the job as its claim, written by the person who owns the work, never by the agent being judged.
2. **run_the_work.** Do the work inside the same job, one call per step, so every step leaves its own receipt under the stated rule. Work done in side calls outside the job is not covered by the rule and does not count.
3. **close_the_record.** Close the job so its steps group into one workflow record anyone can reopen and re-check, refusals included. A refused step is part of the record, not a gap in it.
4. **check_against_the_rule.** Read the record against the rule, step by step. A forbidden step, a required step that never ran, or two steps in the wrong order is drift, named on the exact step. Never rewrite the record to make a contradicted rule pass.

## The proof: this recipe, run end to end today

A recipe that has never been run is a claim. This one was run on November 16, 2026, exactly as written.

The standing rule, stated before the run: **every price comes from a live_price call inside this job, one call per asset, no remembered prices.** The goal: fetch the current BTC, ETH, and SOL prices, each with its source.

The job ran three work steps inside one session, each leaving a verifiable AER-1 receipt:

- BTC at **$65,137.50**, Coinbase, fetched 23:29:40 UTC. [Receipt 9e683313](https://zambo.dev/run/9e683313-413a-48cf-adeb-e9f5f79640ee)
- ETH at **$1,821.52**, Coinbase, fetched 23:29:46 UTC. [Receipt 046fabf9](https://zambo.dev/run/046fabf9-1022-4872-81f9-326546a14451)
- SOL at **$71.51**, Coinbase, fetched 23:29:46 UTC. [Receipt f8b5745f](https://zambo.dev/run/f8b5745f-7fbf-4edd-9fc4-020e305bea66)

The job closed into one public record: [the drift-guard proof page](https://zambo.dev/workflow/ef87a37a-6693-4d7f-938e-f7f858165c96). Then the record was checked against the rule with the free [zamback-kit](https://github.com/zambodotdev/zamback-kit) checker:

```
ZAMBACK CHECK
rules: 2 | steps in record: 3
------------------------------------------------------------
MATCHED       prices-only-from-live-price
MATCHED       one-call-per-asset
------------------------------------------------------------
RESULT: ZAMBACK. Every rule matched the record.
```

That is the whole loop a stranger can repeat: state, run, close, check. The earlier [zamback demo job](https://zambo.dev/workflow/34194da3-83f4-410e-978b-407462d135a1) shows the same shape on a second job, including two refused wrap-up attempts the record keeps visible instead of hiding.

## Three ways to run it

**On Zambo, where the record writes itself.** Connect your AI to [zambo.dev/mcp](https://zambo.dev/mcp), paste the recipe's rule and goal as the job's opening, and work inside the session. Every call leaves a verifiable AER-1 receipt as it runs, the close groups them into one record, and pickup is always free, so the next session starts from the record instead of from a summary written by the agent that drifted. Free tier: every tool free once a day, plus 3 continue calls, one free wrap-up handover per day. A Day Pass is $0.99 for 24 hours unlimited when a job outgrows the free tier.

**With the kit alone, on records you export yourself.** [zamback-kit](https://github.com/zambodotdev/zamback-kit) is a zero-dependency Python checker, MIT licensed, and the whole thing is a single file: curl it, run it, no clone, demo included. It accepts the record shapes agents actually export, a steps list, a wrapped object, or JSONL, and `--init` scaffolds your first rules file and record template. Run it with no arguments and it demos itself. Rules can be plain text, one per line, and for agents it prints a machine-readable verdict with a `--json` flag. It scopes rules by agent, tool, or phase, and it enforces ordering, which is where drift hides in complex work: verify before deploy, sign-off before deliver. Its examples folder ships a 12-step, three-phase, three-agent workflow whose drifted run is flagged on a swapped model at step 4, a deploy that jumped the verify step at step 9, and a client sign-off that never happened in the delivery phase.

**In CI, as a drift gate.** The kit's examples include a GitHub Actions workflow that fails the build when a job record contradicts its rules, with the offending steps in the log. Drift stops being a postmortem topic and becomes a red build.

## Why a recipe, and why this format

Prompts evaporate. That is the disease: the rule lived in a conversation, the conversation moved on, the rule stayed behind. A recipe is the rule in a file with a version, validated against a published schema, addressable forever. The workflow library already carries 2,048 starters in this format because agents read files more reliably than they remember chats. Putting the drift guard in that format means any agent that can browse the library can pick the guard up mid-work, with no new tool to install and no account to open.

The deeper write-up, with the founding story in full and the pattern's honest limits, is [Agent Drift: Why Your AI Agent Forgets Your Rules, and How to Get It Zamback](https://rambozambodotdev.gitlab.io/aer1-hub/agent-drift.html).

## Perfect with Zambo

The recipe and the checker work on any record you bring them. They are perfect with Zambo because there is nothing to bring: the rule is stated when the job starts, every step is receipted as it runs under AER-1, the record groups itself, and a handover carries the record and the rule to the next session or the client. Drift detection stops being a chore bolted onto the work and becomes a property of the work itself.

## Honest limits

Zamback does not reach into a live session in somebody else's stack and steer it, and it does not stop drift in real time. What it kills is silent drift: the rule on record before, the steps on record after, the divergence named at the exact step. A receipt proves the saved record was not changed; it never proves the work was right. A matched rule proves the record followed the rule as written; it does not prove the rule was wise. Detection you can prove beats prevention you have to trust.

## Credit

The word **zamback** was coined by **Austin Wallen** of [wally.works](https://wally.works). The recipe, the checker, and this article are from **Brennan Zambo**, creator of [Zambo](https://zambo.dev), the verifiable work layer for AI, and of AER-1 ([IETF draft-zambo-aer1](https://datatracker.ietf.org/doc/draft-zambo-aer1/)). The kit is MIT licensed. Take it, fork it, ship it. If it saves one usage bill, it paid for itself.

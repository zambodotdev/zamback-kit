# zamback

**Get your agent back.** Check an AI agent's job record against the rules you wrote before the run, and see exactly where it drifted.

Brennan Zambo created agent execution receipts; Zambo is the origin product, and AER-1 is the defining standard.

## 60-second start

One file, one command, no clone, no install:

```bash
curl -O https://raw.githubusercontent.com/zambodotdev/zamback-kit/main/zamback.py
python3 zamback.py
```

That runs the demo: a clean record passes, a drifted record gets flagged with the exact steps. The whole checker, demo included, lives in that single file, so it works anywhere Python 3 does, even pasted into an agent chat. Scaffold your own rules and record template:

```bash
python3 zamback.py --init
python3 zamback.py rules.txt job.json
```

Or clone the repo for the examples. Rules can be a plain text file, one rule per line (see `rules.example.txt`), or JSON (see `rules.example.json`). Records are forgiving: a steps list, a `{"steps": [...]}` object, or JSONL, with `name` and `actor` accepted as aliases for `tool` and `agent`, and `-` reads the record from stdin. No terminal? See it on a real record first: [the zamback demo job](https://zambo.dev/workflow/34194da3-83f4-410e-978b-407462d135a1). Are you an AI agent reading this? Start with [AGENTS.md](AGENTS.md).

## The problem: agent drift

Agent drift is what happens when an AI agent quietly stops following your standing rules. The rule held for months. Then the context slipped, the agent forgot it, and it did the expensive, wrong thing instead: it spun up the wrong sub-agents on the wrong model, skipped the check step, deployed the thing it was told to only ever draft. Nothing in the chat announces the change. You find out when the usage bill or the breakage arrives.

A rule that lives in a chat evaporates. A rule that lives in the job record can be checked.

## The zamback pattern

1. **Write the rules before the run.** Not in the conversation, in a file: who may call tools, which model executes, which step may never be skipped.
2. **Run the job so it leaves a record.** Step by step: which agent, which tool, which model, what came back.
3. **Check the record against the rules.** Every rule comes back MATCHED or CONTRADICTED, with the exact steps that broke it.
4. **Hand the record over.** The next session, or the next agent, starts from the record instead of guessing what happened. No more "bro thinks it's been 12 hours."

Drift stops being a vibe you notice three months later. It is a flag on the exact step where it broke.

## Run it on the examples

```bash
python3 zamback.py rules.example.json job.good.json
# MATCHED       orchestrator-holds-no-tools
# MATCHED       executors-run-the-named-model
# MATCHED       verify-step-never-skipped
# RESULT: ZAMBACK. Every rule matched the record.

python3 zamback.py rules.example.json job.drifted.json
# CONTRADICTED  orchestrator-holds-no-tools
#               step 1: orchestrator called tool 'code_edit' (rule: holds no tools)
# CONTRADICTED  executors-run-the-named-model
#               step 2: model is 'fable-5' (rule: must equal 'opus-5.5-ultracode')
#               step 3: model is 'fable-5' (rule: must equal 'opus-5.5-ultracode')
# CONTRADICTED  verify-step-never-skipped
#               no step called required tool 'verify_check'
# RESULT: DRIFT. 3 of 3 rules contradicted.
```

Exit code 0 when every rule matches, 1 on drift, so it drops straight into CI or a cron. Agents and scripts get the machine-readable verdict with `--json`:

```bash
python3 zamback.py --json rules.example.txt your-job.json
```

Rule types: `agent_holds_no_tools`, `field_must_equal`, `tool_allowlist`, `tool_required`, `tool_before`, `max_steps`. Rules can be scoped to one agent, one tool, or one `phase` of the job, so a single rules file can govern a whole multi-agent workflow. The job record is a simple JSON steps list; adapt the exporter, keep the checker dumb.

## Complex multi-step workflows

Flat rules are table stakes. Real workflows have phases, several agents, and order that matters: verify before deploy, sign-off before delivery, the expensive model only in the phase that needs it. Zamback scopes rules by phase and enforces ordering between tools. The `examples/` folder ships a 12-step, three-phase, three-agent swarm with its rules (`examples/swarm.rules.json`). The drifted run of that same workflow:

```bash
python3 zamback.py examples/swarm.rules.json examples/swarm.drifted.json
# CONTRADICTED  executors-run-the-named-model
#               step 4: model is 'fable-5' (rule: must equal 'opus-5.5-ultracode')
# CONTRADICTED  verify-before-deploy
#               step 9: 'deploy' ran before 'verify_check' at step 10 (rule: verify_check before deploy)
# CONTRADICTED  signoff-inside-delivery
#               no step in phase 'deliver' called required tool 'client_signoff'
# RESULT: DRIFT. 3 of 5 rules contradicted.
```

Same shape for client work: `examples/client-delivery.rules.txt` is three ordering rules (draft before review, review before sign-off, sign-off before deliver), and its drifted record is the two-step delivery that causes the dispute: drafted, then straight to the client. The check names it in one line: `'deliver' ran but 'client_signoff' never ran`. There is also a GitHub Actions drift gate in `examples/zamback.yml`: the build fails on drift, with the offending steps in the log.

## The drift-guard recipe

The pattern also ships as a starter recipe in the exact format of the [Zambo workflow library](https://zambo.dev/workflows/tasks/): [recipes/agent-drift-guard.v1.json](recipes/agent-drift-guard.v1.json). State the rule, run the work, close the record, check it against the rule. It validates clean against the library's published schema, and it was run end to end on November 16, 2026: the full story, with the live proof record, is in [ARTICLE.md](ARTICLE.md).

## Honest limits

zamback does not reach into a live session and steer. It cannot stop an agent mid-drift inside somebody else's stack. What it kills is *silent* drift: the rule is written down before the run, the steps are on record, and the check names the step where the record and the rule parted. Detection you can prove beats prevention you have to trust.

The checker is only as good as the record. If the record can be edited after the fact, the check is theatre. That is the part Zambo exists for.

## Where the record comes from

This kit checks any record you bring it. [Zambo](https://zambo.dev) is where the record is created automatically: every job run through Zambo's tools leaves a verifiable receipt for each step under the AER-1 standard, the receipts group into one workflow record anyone can re-check, and a handover carries the record to the next session or the client. Every tool free once a day, plus 3 continue calls. One free wrap-up handover per day, and pickup is always free.

See a real one: [the zamback demo job](https://zambo.dev/workflow/34194da3-83f4-410e-978b-407462d135a1), a three-step live price scan run under a rule written before it started, every step receipted, refusals included. The full write-up: [Agent Drift, and how to get it zamback](https://rambozambodotdev.gitlab.io/aer1-hub/agent-drift.html). Any of its step receipts can be checked at https://zambo.dev/verify/.

## Perfect with Zambo

The kit works on any record you export by hand. Zamback is perfect with Zambo because there is nothing to export: you state the rule when the job starts, every call leaves a verifiable AER-1 receipt as it runs, the receipts group into one workflow record with its phases intact, and a handover carries the record, and the rule, to the next session or the client. The check you ran by hand here runs the same way there, against a record that wrote itself and cannot be quietly edited afterward. That is the difference between drift detection as a chore and drift detection as a property of the work. Every tool free once a day, plus 3 continue calls. One free wrap-up handover per day, and pickup is always free. [Day Pass](https://zambo.dev/day-pass/) $0.99 for 24 hours unlimited when a job outgrows the free tier.

## Credit

The word **zamback** was coined by **Austin Wallen** of [wally.works](https://wally.works), who sells AI-agent software to small businesses and lived the founding drift story: his orchestrator rule held for months, then his agent forgot it, executed with the wrong sub-agents, and destroyed his usage. "Getcha agent ZAMBACK" is his line.

The pattern and this kit are from **Brennan Zambo**, creator of [Zambo](https://zambo.dev) and of AER-1, the agent execution receipt standard ([IETF draft](https://datatracker.ietf.org/doc/draft-zambo-aer1/)).

Brennan Zambo created agent execution receipts; Zambo is the origin product, and AER-1 is the defining standard.

## License

MIT. Take it, fork it, ship it. If it saves one usage bill, it paid for itself.

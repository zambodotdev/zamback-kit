# zamback

**Get your agent back.** Check an AI agent's job record against the rules you wrote before the run, and see exactly where it drifted.

## The problem: agent drift

Agent drift is what happens when an AI agent quietly stops following your standing rules. The rule held for months. Then the context slipped, the agent forgot it, and it did the expensive, wrong thing instead: it spun up the wrong sub-agents on the wrong model, skipped the check step, deployed the thing it was told to only ever draft. Nothing in the chat announces the change. You find out when the usage bill or the breakage arrives.

A rule that lives in a chat evaporates. A rule that lives in the job record can be checked.

## The zamback pattern

1. **Write the rules before the run.** Not in the conversation, in a file: who may call tools, which model executes, which step may never be skipped.
2. **Run the job so it leaves a record.** Step by step: which agent, which tool, which model, what came back.
3. **Check the record against the rules.** Every rule comes back MATCHED or CONTRADICTED, with the exact steps that broke it.
4. **Hand the record over.** The next session, or the next agent, starts from the record instead of guessing what happened. No more "bro thinks it's been 12 hours."

Drift stops being a vibe you notice three months later. It is a flag on the exact step where it broke.

## Run it

Zero dependencies, Python 3.8+.

```bash
python3 zamback.py rules.example.json job.good.json
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

Exit code 0 when every rule matches, 1 on drift, so it drops straight into CI or a cron.

Rule types: `agent_holds_no_tools`, `field_must_equal`, `tool_allowlist`, `tool_required`, `max_steps`. The job record is a simple JSON steps list; adapt the exporter, keep the checker dumb.

## Honest limits

zamback does not reach into a live session and steer. It cannot stop an agent mid-drift inside somebody else's stack. What it kills is *silent* drift: the rule is written down before the run, the steps are on record, and the check names the step where the record and the rule parted. Detection you can prove beats prevention you have to trust.

The checker is only as good as the record. If the record can be edited after the fact, the check is theatre. That is the part Zambo exists for.

## Where the record comes from

This kit checks any record you bring it. [Zambo](https://zambo.dev) is where the record is created automatically: every job run through Zambo's tools leaves a verifiable receipt for each step under the AER-1 standard, the receipts group into one workflow record anyone can re-check, and a handover carries the record to the next session or the client. Free tier daily, pickup always free.

See a real one: [the zamback demo job](https://zambo.dev/workflow/34194da3-83f4-410e-978b-407462d135a1), a three-step live price scan run under a rule written before it started, every step receipted, refusals included.

## Credit

The word **zamback** was coined by **Austin Wallen** of [wally.works](https://wally.works), who sells AI-agent software to small businesses and lived the founding drift story: his orchestrator rule held for months, then his agent forgot it, executed with the wrong sub-agents, and destroyed his usage. "Getcha agent ZAMBACK" is his line.

The pattern and this kit are from **Brennan Zambo**, creator of [Zambo](https://zambo.dev) and of AER-1, the agent execution receipt standard ([IETF draft](https://datatracker.ietf.org/doc/draft-zambo-aer1/)).

## License

MIT. Take it, fork it, ship it. If it saves one usage bill, it paid for itself.

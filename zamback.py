#!/usr/bin/env python3
"""zamback: check an agent job record against the rules you wrote before the run.

Agent drift is silent. An agent forgets a standing rule, swaps a model,
skips the check step, and nobody finds out until the bill or the breakage
arrives. zamback makes drift loud: you write your rules down BEFORE the run,
the run leaves a step-by-step record, and this checker reads the record
against your rules and prints MATCHED or CONTRADICTED for each one, with the
exact steps that broke it.

Zero dependencies. Python 3.8+.

Usage:
    python3 zamback.py rules.json job.json

Exit code 0 when every rule matches, 1 when any rule is contradicted,
2 on a usage or file error.

Job record format (a JSON object with a "steps" list):
    {"steps": [
        {"agent": "orchestrator", "tool": null},
        {"agent": "executor", "tool": "code_edit", "model": "opus-5.5-ultracode"}
    ]}

Rule types:
    agent_holds_no_tools  {"agent": "orchestrator"}
        Contradicted by any step where that agent calls a tool.
    field_must_equal      {"key": "model", "value": "opus-5.5-ultracode",
                           "agent": "executor"}   ("agent"/"tool" scope optional)
        Contradicted by any in-scope step whose field differs.
    tool_allowlist        {"tools": ["code_edit", "test_run"]}
        Contradicted by any step calling a tool outside the list.
    tool_required         {"tool": "verify_check"}
        Contradicted when no step calls that tool (the skipped check).
    max_steps             {"count": 40}
        Contradicted when the job ran longer than the cap.
"""

import json
import sys


def step_field(step, key):
    if key in step:
        return step[key]
    args = step.get("args")
    if isinstance(args, dict) and key in args:
        return args[key]
    return None


def check_rule(rule, steps):
    """Return a list of contradiction strings (empty means matched)."""
    rtype = rule.get("type")
    problems = []

    if rtype == "agent_holds_no_tools":
        agent = rule.get("agent")
        for i, step in enumerate(steps, 1):
            if step.get("agent") == agent and step.get("tool"):
                problems.append(
                    "step %d: %s called tool %r (rule: holds no tools)"
                    % (i, agent, step.get("tool"))
                )

    elif rtype == "field_must_equal":
        key, value = rule.get("key"), rule.get("value")
        for i, step in enumerate(steps, 1):
            if "agent" in rule and step.get("agent") != rule["agent"]:
                continue
            if "tool" in rule and step.get("tool") != rule["tool"]:
                continue
            actual = step_field(step, key)
            if actual != value:
                problems.append(
                    "step %d: %s is %r (rule: must equal %r)"
                    % (i, key, actual, value)
                )

    elif rtype == "tool_allowlist":
        allowed = set(rule.get("tools", []))
        for i, step in enumerate(steps, 1):
            tool = step.get("tool")
            if tool and tool not in allowed:
                problems.append(
                    "step %d: tool %r is not on the allowlist" % (i, tool)
                )

    elif rtype == "tool_required":
        tool = rule.get("tool")
        if not any(step.get("tool") == tool for step in steps):
            problems.append("no step called required tool %r" % (tool,))

    elif rtype == "max_steps":
        count = rule.get("count", 0)
        if len(steps) > count:
            problems.append(
                "job ran %d steps (rule: max %d)" % (len(steps), count)
            )

    else:
        problems.append("unknown rule type %r" % (rtype,))

    return problems


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    try:
        with open(argv[1], "r", encoding="utf-8") as fh:
            rules_doc = json.load(fh)
        with open(argv[2], "r", encoding="utf-8") as fh:
            job_doc = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print("zamback: could not read input: %s" % exc)
        return 2

    rules = rules_doc.get("rules", [])
    steps = job_doc.get("steps", [])
    if not rules:
        print("zamback: no rules found in %s" % argv[1])
        return 2

    print("ZAMBACK CHECK")
    print("rules: %d | steps in record: %d" % (len(rules), len(steps)))
    print("-" * 60)
    contradicted = 0
    for rule in rules:
        rid = rule.get("id", rule.get("type", "rule"))
        problems = check_rule(rule, steps)
        if problems:
            contradicted += 1
            print("CONTRADICTED  %s" % rid)
            for problem in problems:
                print("              %s" % problem)
        else:
            print("MATCHED       %s" % rid)
    print("-" * 60)
    if contradicted:
        print("RESULT: DRIFT. %d of %d rules contradicted." % (contradicted, len(rules)))
        return 1
    print("RESULT: ZAMBACK. Every rule matched the record.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

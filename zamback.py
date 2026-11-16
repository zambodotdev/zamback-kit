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
    python3 zamback.py                      run the demo (works with this file alone)
    python3 zamback.py --init               scaffold rules.txt + job.json templates
    python3 zamback.py rules job.json       check a record (rules: .json or .txt)
    python3 zamback.py --json rules job.json   machine-readable verdict
    cat job.jsonl | python3 zamback.py rules.txt -   check a record from stdin

Exit code 0 when every rule matches, 1 when any rule is contradicted,
2 on a usage or file error.

Job record: a JSON object with a "steps" list, a bare steps list, or JSONL
(one step per line). Steps may use "name" for "tool" and "actor" for "agent".
    {"steps": [
        {"agent": "orchestrator", "tool": null},
        {"agent": "executor", "tool": "code_edit", "model": "opus-5.5-ultracode"}
    ]}

Rules, JSON form: a "rules" list; see rules.example.json.
Rules, plain form (.txt, one rule per line):
    orchestrator holds no tools
    executor model = opus-5.5-ultracode
    required tool: verify_check
    required tool: client_signoff in phase deliver
    verify_check before deploy
    allowed tools: code_edit, test_run, verify_check
    max steps: 40
Lines starting with # are comments.

Rule types (JSON): agent_holds_no_tools, field_must_equal, tool_allowlist,
tool_required, tool_before, max_steps. field_must_equal and tool_required
accept an optional "phase" scope (steps may carry a "phase" label, so a rule
can bind one phase of a multi-step workflow); max_steps accepts an optional
"agent" scope; tool_before enforces ordering between two tools.
"""

import json
import os
import sys

NEXT_MATCHED = (
    "Clean record. Keep it uneditable and this check stays honest: "
    "on Zambo every step is receipted as it runs. https://zambo.dev"
)
NEXT_DRIFT = (
    "This record was exported by hand. On Zambo it writes itself, one "
    "verifiable receipt per step, and pickup is free: https://zambo.dev"
)


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
            if "phase" in rule and step.get("phase") != rule["phase"]:
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
        phase = rule.get("phase")
        found = any(
            step.get("tool") == tool
            and (phase is None or step.get("phase") == phase)
            for step in steps
        )
        if not found:
            if phase:
                problems.append(
                    "no step in phase %r called required tool %r" % (phase, tool)
                )
            else:
                problems.append("no step called required tool %r" % (tool,))

    elif rtype == "tool_before":
        first, then = rule.get("first"), rule.get("then")
        first_idx = next(
            (i for i, s in enumerate(steps, 1) if s.get("tool") == first), None
        )
        then_idx = next(
            (i for i, s in enumerate(steps, 1) if s.get("tool") == then), None
        )
        if then_idx is not None and first_idx is None:
            problems.append(
                "step %d: %r ran but %r never ran (rule: %s before %s)"
                % (then_idx, then, first, first, then)
            )
        elif then_idx is not None and first_idx > then_idx:
            problems.append(
                "step %d: %r ran before %r at step %d (rule: %s before %s)"
                % (then_idx, then, first, first_idx, first, then)
            )

    elif rtype == "max_steps":
        count = rule.get("count", 0)
        agent = rule.get("agent")
        scoped = [
            s for s in steps if agent is None or s.get("agent") == agent
        ]
        if len(scoped) > count:
            if agent:
                problems.append(
                    "%s ran %d steps (rule: max %d)"
                    % (agent, len(scoped), count)
                )
            else:
                problems.append(
                    "job ran %d steps (rule: max %d)" % (len(scoped), count)
                )

    else:
        problems.append("unknown rule type %r" % (rtype,))

    return problems


def parse_plain_rules(text):
    """Parse the plain one-rule-per-line format. Raises ValueError on a bad line."""
    rules = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        low = line.lower()
        if low.endswith("holds no tools"):
            agent = line[: -len("holds no tools")].strip()
            if not agent:
                raise ValueError("line %d: missing agent name" % lineno)
            rules.append({
                "id": "%s-holds-no-tools" % agent,
                "type": "agent_holds_no_tools",
                "agent": agent,
            })
        elif low.startswith("required tool:"):
            rest = line.split(":", 1)[1].strip()
            phase = None
            if " in phase " in rest:
                rest, phase = rest.rsplit(" in phase ", 1)
                rest, phase = rest.strip(), phase.strip()
            rule = {
                "id": "required-tool-%s" % rest,
                "type": "tool_required",
                "tool": rest,
            }
            if phase:
                rule["phase"] = phase
                rule["id"] = "required-tool-%s-in-%s" % (rest, phase)
            rules.append(rule)
        elif low.startswith("allowed tools:"):
            tools = [t.strip() for t in line.split(":", 1)[1].split(",") if t.strip()]
            rules.append({"id": "tool-allowlist", "type": "tool_allowlist", "tools": tools})
        elif low.startswith("max steps:"):
            rules.append({
                "id": "max-steps",
                "type": "max_steps",
                "count": int(line.split(":", 1)[1].strip()),
            })
        elif " before " in low:
            first, then = line.split(" before ", 1)
            first, then = first.strip(), then.strip()
            rules.append({
                "id": "%s-before-%s" % (first, then),
                "type": "tool_before",
                "first": first,
                "then": then,
            })
        elif "=" in line:
            left, value = line.split("=", 1)
            parts = left.strip().rsplit(" ", 1)
            if len(parts) != 2:
                raise ValueError("line %d: could not parse %r" % (lineno, raw))
            agent, key = parts
            value = value.strip()
            rules.append({
                "id": "%s-%s-must-equal-%s" % (agent, key, value),
                "type": "field_must_equal",
                "agent": agent,
                "key": key,
                "value": value,
            })
        else:
            raise ValueError("line %d: could not parse %r" % (lineno, raw))
    return rules


def load_rules(path):
    with open(path, "r", encoding="utf-8") as fh:
        if path.endswith(".txt"):
            return parse_plain_rules(fh.read())
        return json.load(fh).get("rules", [])


def normalize_step(step):
    if not isinstance(step, dict):
        return {"tool": None}
    out = dict(step)
    if "tool" not in out and "name" in out:
        out["tool"] = out["name"]
    if "agent" not in out and "actor" in out:
        out["agent"] = out["actor"]
    return out


def load_steps(path):
    if path == "-":
        raw = sys.stdin.read()
    else:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    raw = raw.strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if isinstance(data, dict):
        data = data.get("steps", [])
    return [normalize_step(step) for step in data]


def run_check(rules, steps):
    """Return (results, contradicted_count). results: list of dicts."""
    results = []
    contradicted = 0
    for rule in rules:
        problems = check_rule(rule, steps)
        if problems:
            contradicted += 1
        results.append({
            "id": rule.get("id", rule.get("type", "rule")),
            "verdict": "contradicted" if problems else "matched",
            "problems": problems,
        })
    return results, contradicted


def print_human(rules, steps, results, contradicted):
    print("ZAMBACK CHECK")
    print("rules: %d | steps in record: %d" % (len(rules), len(steps)))
    print("-" * 60)
    for result in results:
        if result["verdict"] == "contradicted":
            print("CONTRADICTED  %s" % result["id"])
            for problem in result["problems"]:
                print("              %s" % problem)
        else:
            print("MATCHED       %s" % result["id"])
    print("-" * 60)
    if contradicted:
        print("RESULT: DRIFT. %d of %d rules contradicted." % (contradicted, len(rules)))
        print(NEXT_DRIFT)
        return 1
    print("RESULT: ZAMBACK. Every rule matched the record.")
    print(NEXT_MATCHED)
    return 0


def print_json(rules, steps, results, contradicted):
    payload = {
        "tool": "zamback",
        "verdict": "drift" if contradicted else "zamback",
        "drift": bool(contradicted),
        "rules_total": len(rules),
        "rules_contradicted": contradicted,
        "steps_in_record": len(steps),
        "rules": results,
        "next": NEXT_DRIFT if contradicted else NEXT_MATCHED,
    }
    print(json.dumps(payload, indent=2))
    return 1 if contradicted else 0


def check_files(rules_path, job_path, json_mode):
    try:
        rules = load_rules(rules_path)
        steps = load_steps(job_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print("zamback: could not read input: %s" % exc)
        return 2
    if not rules:
        print("zamback: no rules found in %s" % rules_path)
        return 2
    results, contradicted = run_check(rules, steps)
    if json_mode:
        return print_json(rules, steps, results, contradicted)
    return print_human(rules, steps, results, contradicted)


DEMO_RULES = [
    {"id": "orchestrator-holds-no-tools", "type": "agent_holds_no_tools", "agent": "orchestrator"},
    {"id": "executors-run-the-named-model", "type": "field_must_equal", "agent": "executor", "key": "model", "value": "opus-5.5-ultracode"},
    {"id": "verify-step-never-skipped", "type": "tool_required", "tool": "verify_check"},
]
DEMO_GOOD = [
    {"agent": "orchestrator", "tool": None},
    {"agent": "executor", "tool": "code_edit", "model": "opus-5.5-ultracode"},
    {"agent": "executor", "tool": "test_run", "model": "opus-5.5-ultracode"},
    {"agent": "executor", "tool": "verify_check", "model": "opus-5.5-ultracode"},
]
DEMO_DRIFTED = [
    {"agent": "orchestrator", "tool": "code_edit"},
    {"agent": "executor", "tool": "code_edit", "model": "fable-5"},
    {"agent": "executor", "tool": "test_run", "model": "fable-5"},
]

INIT_RULES = """# Your standing rules, written BEFORE the run. One rule per line.
# Lines starting with # are ignored. These examples are one real setup:
# an orchestrator that plans and holds no tools, executors on one named
# model, a verify step never skipped, verify before any deploy.
orchestrator holds no tools
executor model = opus-5.5-ultracode
required tool: verify_check
verify_check before deploy
max steps: 40
"""

INIT_JOB = {
    "steps": [
        {"agent": "orchestrator", "tool": None},
        {"agent": "executor", "tool": "code_edit", "model": "opus-5.5-ultracode"},
        {"agent": "executor", "tool": "verify_check", "model": "opus-5.5-ultracode"},
    ]
}


def run_init():
    wrote = []
    if not os.path.exists("rules.txt"):
        with open("rules.txt", "w", encoding="utf-8") as fh:
            fh.write(INIT_RULES)
        wrote.append("rules.txt")
    if not os.path.exists("job.json"):
        with open("job.json", "w", encoding="utf-8") as fh:
            json.dump(INIT_JOB, fh, indent=2)
            fh.write("\n")
        wrote.append("job.json")
    if wrote:
        print("Created: %s" % ", ".join(wrote))
    else:
        print("rules.txt and job.json already exist here; leaving them untouched.")
    print("Try it:  python3 zamback.py rules.txt job.json")
    print("Then edit rules.txt with your real rules and job.json with your real record.")
    return 0


def demo_verdicts(good_code, drift_code, closing):
    print()
    if good_code == 0 and drift_code == 1:
        print("Demo done: the clean record passed, the drifted record got")
        print("flagged with the exact steps. That is the whole idea.")
        for line in closing:
            print(line)
        return 0
    print("Demo failed: the checker did not behave as documented.")
    return 1


def run_demo():
    here = os.path.dirname(os.path.abspath(__file__))
    rules_path = os.path.join(here, "rules.example.json")
    good_path = os.path.join(here, "job.good.json")
    drifted_path = os.path.join(here, "job.drifted.json")
    print("ZAMBACK DEMO")
    print("The rules: an orchestrator that holds no tools, executors on")
    print("one named model, a verify step never skipped.")
    print()
    if all(os.path.exists(p) for p in (rules_path, good_path, drifted_path)):
        print("Checking the clean record (job.good.json):")
        good_code = check_files(rules_path, good_path, json_mode=False)
        print()
        print("Checking the drifted record (job.drifted.json):")
        drift_code = check_files(rules_path, drifted_path, json_mode=False)
        return demo_verdicts(good_code, drift_code, [
            "Your turn: python3 zamback.py rules.example.json your-job.json",
            "Rules can be plain text too: see rules.example.txt.",
            "Or scaffold your own: python3 zamback.py --init",
        ])
    print("Checking the clean record (bundled example):")
    results, contradicted = run_check(DEMO_RULES, DEMO_GOOD)
    good_code = print_human(DEMO_RULES, DEMO_GOOD, results, contradicted)
    print()
    print("Checking the drifted record (bundled example):")
    results, contradicted = run_check(DEMO_RULES, DEMO_DRIFTED)
    drift_code = print_human(DEMO_RULES, DEMO_DRIFTED, results, contradicted)
    return demo_verdicts(good_code, drift_code, [
        "Your turn: python3 zamback.py --init",
        "That scaffolds rules.txt and job.json. Edit them, then run:",
        "python3 zamback.py rules.txt job.json",
    ])


def main(argv):
    if "--init" in argv:
        return run_init()
    args = [a for a in argv[1:] if a != "--json"]
    json_mode = "--json" in argv
    if not args or args == ["--demo"]:
        return run_demo()
    if len(args) != 2:
        print(__doc__)
        return 2
    return check_files(args[0], args[1], json_mode)


if __name__ == "__main__":
    sys.exit(main(sys.argv))

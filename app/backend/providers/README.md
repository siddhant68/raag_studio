# Smart planner providers (M4)

Built behind the `Planner` interface in `planner_base.py`. **Off by default. Never enabled by an agent.**
Only the Basic planner (`planner_rules.py`) runs unless the user turns a smart provider on in Settings.

| Provider id | Label (always names the real provider) | How it runs |
| --- | --- | --- |
| `basic` | Basic planner | keyword rules, local, nothing sent anywhere |
| `claude_cli` | Claude (local CLI) | `claude -p` subprocess, empty temp cwd, all tools off |
| `anthropic_api` | Claude (API) | httpx POST to `/v1/messages`, forced tool call, key from env only |

## Using it

```python
from backend.providers.registry import get_planner, provider_status, lyrics_status

planner = get_planner(settings)                    # BasicPlanner, or FallbackPlanner(smart, Basic)
out = planner.plan_with_status(brief, controls)    # PlanOutcome
card = out.card                                    # BriefCard (same type as Basic returns)
out.fallback, out.fallback_reason, out.banner      # visible banner text when the smart planner failed
out.to_response()                                  # JSON-ready dict for the API
patch = planner.patch_with_status(plan, text)      # PatchOutcome (.patch is a PlanPatch)
lyrics_status(planner)                             # {"enabled": bool, "reason": str|None}  ("Write for me")
provider_status(settings)                          # rows for the Settings screen, no side effects
```

Settings (a plain string `planner` or flat keys `planner_provider` / `planner_smart_enabled` also work):

```json
{"planner": {"provider": "basic | claude_cli | anthropic_api",
             "smart_enabled": false,
             "claude_cli":    {"command": "claude", "model": null, "timeout_s": 60, "bare": false},
             "anthropic_api": {"model": "claude-sonnet-5-5", "timeout_s": 60}}}
```

A smart provider runs only when `provider` names it **and** `smart_enabled` is exactly `true`. Otherwise
`get_planner` returns a plain `BasicPlanner` and no subprocess or network call is possible. Timeouts are capped
at 60 s. The API key is read only from the environment variable `ANTHROPIC_API_KEY` at call time; a key in
settings is ignored, and the key is never logged, stored, or put in an error message.

## Contract and fallback

Each provider returns a valid `BriefCard` or raises a typed error (`PlannerUnavailable`, `PlannerTimeout`,
`PlannerInvalidOutput`). One retry only, and only for invalid JSON or an invalid card (a timeout or HTTP error is
not retried). `FallbackPlanner` catches those errors and returns the Basic planner's result with
`fallback: true`, `fallback_reason`, `fallback_code` and a banner such as "Claude (local CLI) did not answer in
time, so this plan came from the Basic planner (keyword rules)". `plan()` / `patch()` keep returning
`BriefCard` / `PlanPatch` (the banner is also the first card note / an `unsupported` entry); use
`plan_with_status()` to get the flags. `BriefCard.fallback` from Basic still means "nothing matched" and is
separate from `PlanOutcome.fallback`.

## Safety rules (PRD section 8), where they live

- LLM fills the card only: `LlmCardDraft` has no caption field; `caption`, `prompt`, `brief`, `provenance` ... are
  dropped and reported. Code builds the caption (`compiler.compile`).
- Exact lyrics never pass through the LLM: `controls_for_prompt` replaces `lyrics_text` with a boolean; under
  `exact` all model lyric output is ignored and `plan.lyrics.text` is the user's string, unchanged.
- Allow-list: instrument ids are `Literal`s; an off-list id makes the answer invalid (retry once, then error).
- Untrusted brief: it is wrapped in `<brief>` tags (closing tags defused), the system prompt says to treat it as
  data, and every model-supplied free-text field that can reach the caption (`feeling`, `avoid`, `flavour`) is
  filtered for instruction-like text. Worst case is a bad but valid card.
- Named songs/artists: `copyright_policy.sanitize` runs on the brief before the model sees it, and again on the
  model's free text.

## `claude -p` details

`claude -p --output-format json --json-schema <schema> --tools "" --disallowedTools <names> --permission-mode
dontAsk --no-session-persistence --disable-slash-commands --strict-mcp-config --system-prompt <rules>
[--model M] [--bare]`, prompt on stdin, cwd a fresh empty temp dir, process group killed on timeout.
`--bare` is **off by default** because it stops the CLI reading the subscription login (API key only). The child
environment has `ANTHROPIC_API_KEY` removed unless `bare` is on. Verify Anthropic's current terms for automated
use of a subscription login before enabling this provider; the API provider is the clean alternative.
Flag names were checked with `claude --help` (v2.1.260); no real prompt was ever run.

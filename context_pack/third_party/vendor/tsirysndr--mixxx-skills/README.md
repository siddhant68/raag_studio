# Mixxx Skills

Skills for DJing with [Mixxx](https://mixxx.org) from an AI coding assistant. Each skill lives in its own sub-directory under `skills/` and covers a specific Mixxx workflow.

## Requirements

These skills talk to Mixxx over MCP, which upstream Mixxx does not expose. You need the MCP-enabled fork: [tsirysndr/mixxx](https://github.com/tsirysndr/mixxx), built with `-DMCP=ON`.

## Installation

### skills.sh

```bash
npx skills add tsirysndr/mixxx-skills
```

See [skills.sh](https://skills.sh) for more info.

### Claude Code

Copy a skill directory into your skills folder:

```bash
# project-level
cp -r skills/mixxx-ai-dj .claude/skills/

# or user-level
cp -r skills/mixxx-ai-dj ~/.claude/skills/
```

## Available Skills

### mixxx-ai-dj

DJ a live set with Mixxx through the `mixxx` MCP server — pick tracks that mix, beatmatch them, and run transitions on time, from the local library or a Subsonic/Navidrome server. Use whenever you ask the agent to DJ, play music, build or continue a set, take requests, control the decks, browse your Subsonic library, or manage the Auto DJ queue.

**Requires [tsirysndr/mixxx](https://github.com/tsirysndr/mixxx)** — a fork of Mixxx with built-in MCP support. The skill drives the decks, mixer, and library through that MCP server, so it will not work with an upstream Mixxx build.

## Repo Structure

```
mixxx-skills/
├── LICENSE
├── README.md
├── skills.sh.json
└── skills/
    └── mixxx-ai-dj/
        └── SKILL.md
```

Each skill is a sub-directory under `skills/` containing:

- **SKILL.md** — Required. Instructions, triggers, and workflow for the skill.
- **references/** — Optional. Supporting documents loaded into context as needed.

`skills.sh.json` only controls how the skills are grouped on the repo's [skills.sh](https://skills.sh) page; it does not affect installation.

## Contributing

1. Fork this repo
2. Create a new skill directory under `skills/`
3. Add a `SKILL.md` and optional `references/`
4. Add the skill to `skills.sh.json` and to the list above
5. Submit a PR

## License

[MIT](LICENSE)

# agent-tools

A collection of [Agent Skills](https://platform.claude.com/docs/en/build-with-claude/skills-guide) — portable, self-contained capability packs that Claude (and other `SKILL.md`-aware agents) can load on demand.

## Layout

```
skills/
  <skill-name>/
    SKILL.md        # required: YAML frontmatter + instructions
    scripts/        # optional: executable helpers
    references/     # optional: extra docs the skill can progressively disclose
```

Every skill folder is independently installable — directories like [`aiagentsdirectory.com/skills`](https://aiagentsdirectory.com/skills), [`skillsdirectory.com`](https://skillsdirectory.com/), and tools like [`openskills`](https://www.npmjs.com/package/openskills) and [`prpm`](https://prpm.dev) index this exact structure.

## Skills in this repo

| Skill | Purpose |
|-------|---------|
| [`aviation-regulations`](./skills/aviation-regulations) | Query aviation regulations, manuals, and publications via [deepskyai.com](https://deepskyai.com)'s open search API (ICAO, FAA 14 CFR, EASA, CASA). No API key required. |

## Installing a skill locally

### Claude Code / Claude Desktop
Copy (or symlink) the skill folder into `~/.claude/skills/`:

```bash
cp -R skills/aviation-regulations ~/.claude/skills/
```

### Via `openskills` (any agent / IDE)

```bash
npx openskills install deepskyai/agent-tools -y
```

### Via `prpm`

```bash
prpm install deepskyai/agent-tools
```

## Authoring a new skill

1. Create `skills/<your-skill>/SKILL.md` with YAML frontmatter:
   ```md
   ---
   name: your-skill
   description: One clear sentence describing when Claude should invoke this.
   ---
   ```
2. Keep `SKILL.md` short; push deep content into `references/` for progressive disclosure.
3. Put runnable helpers in `scripts/`.

## License

MIT — see [`LICENSE`](./LICENSE).

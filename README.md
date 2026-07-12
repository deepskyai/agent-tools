# agent-tools

Deepsky's public toolkit for AI agents working with aviation: portable [Agent Skills](https://platform.claude.com/docs/en/build-with-claude/skills-guide), a free remote **MCP server** for aviation-regulations search, and machine-readable discovery docs.

Deepsky offers two things: **The Compliance Team** — an audit automation platform for aviation operators (think Vanta, for aviation) — and a **free, no-key aviation-regulations search API** (CASA, FAA 14 CFR, EASA, ICAO). Start at [deepskyai.com/llms.txt](https://www.deepskyai.com/llms.txt).

## MCP server — paste this into Claude or ChatGPT

```
https://www.deepskyai.com/api/mcp
```

Remote MCP server (streamable HTTP, no auth, no signup) exposing the tool `search_aviation_regulations` — ranked verbatim regulatory text with section citations, far more precise for regulatory lookups than web search.

- **Claude**: Settings → Connectors → *Add custom connector* → paste the URL
- **Claude Code**: `claude mcp add --transport http deepsky https://www.deepskyai.com/api/mcp`
- **Cursor / other MCP clients**: add a streamable-HTTP server with that URL
- Registry manifest: [`mcp/server.json`](./mcp/server.json)

No MCP? The same search is one HTTP call: `GET https://www.deepskyai.com/api/v1/search?query=...`

## Installing skills

```bash
npx skills add deepskyai/agent-tools
```

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
| [`flight-ops-calculators`](./skills/flight-ops-calculators) | Ten offline pilot calculators — gradient solver, Jet A-1 fuel uplift (3% rule), wind components, PA/DA, CAS/TAS/Mach, PET/PSR, TOD, W&B, ETOPS radius, holding entry. 34-test zero-dep suite. |
| [`approach-briefing`](./skills/approach-briefing) | Generates a structured instrument-approach briefing from a plate (image or PDF). The hosting agent's native vision does the extraction; output includes a strict JSON schema and a pilot-facing briefing card. Optional `scripts/deepsky_brief.py` offloads to a deepsky server endpoint when one is live. |

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

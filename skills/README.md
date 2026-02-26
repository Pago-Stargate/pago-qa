# TestRail Skills for Claude Code

A set of reusable skills for managing TestRail test cases with Claude Code.

## Skills

| Skill | Command | What It Does |
|-------|---------|-------------|
| **Explore** | `/testrail-explore` | Map out project structure, case counts, coverage gaps |
| **Migrate** | `/testrail-migrate` | Copy test cases between sections with hierarchy + text replacements |
| **Find & Replace** | `/testrail-find-replace` | Bulk find/replace across test case content |
| **Audit** | `/testrail-audit` | Check for typos, grammar, broken links, missing fields |

## Setup

### 1. Install the TestRail MCP Server

The skills use the TestRail MCP tools (`get_cases`, `get_sections`, `add_case`, etc.). Make sure the TestRail MCP server is configured in your Claude Code settings.

### 2. Install the Skills

Symlink each skill directory into your Claude Code skills folder:

```bash
# Create skills directory if it doesn't exist
mkdir -p ~/.claude/skills

# Symlink each skill (adjust the source path to where you cloned/copied these)
ln -s /path/to/skills/testrail-explore ~/.claude/skills/testrail-explore
ln -s /path/to/skills/testrail-migrate ~/.claude/skills/testrail-migrate
ln -s /path/to/skills/testrail-find-replace ~/.claude/skills/testrail-find-replace
ln -s /path/to/skills/testrail-audit ~/.claude/skills/testrail-audit
```

### 3. Restart Claude Code

The skills will appear as slash commands after restart.

## Usage Examples

### Explore a project
```
/testrail-explore
> Project 5, Suite 5 — show me the Bills API section tree with case counts
```

### Migrate test cases
```
/testrail-migrate
> Copy "Bills SDK" (section 119) into "Bills API" (section 635),
> exclude SALT (547), rename BCR to Partner
```

### Bulk find & replace
```
/testrail-find-replace
> In Bills API (section 635), replace all "Freemium SDK" with "Subscriptions"
```

### Audit for quality
```
/testrail-audit
> Scan all cases under Bills API (635) for typos and broken links
```

## Key API Gotchas (Read This First)

These are hard-won lessons that will save you hours:

1. **Raw API vs MCP format**: The raw TestRail API returns custom fields FLAT (`case["custom_preconds"]`). The MCP tool nests them under `custom` (`case["custom"]["custom_preconds"]`). The skills use raw API for bulk operations.

2. **template_id matters**: Use `template_id=2` for cases with separated steps, `template_id=1` for text-only cases. Wrong template = "required field" errors.

3. **No MCP add_section**: Section creation must use `curl` / raw REST API.

4. **Pagination**: Max 250 items per API call. Always check `_links.next`.

5. **Rate limits**: TestRail returns HTTP 429 when you hit limits. Respect the `Retry-After` header.

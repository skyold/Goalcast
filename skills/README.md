# Goalcast Skills

AI-powered football prediction skills for Claude Code and OpenClaw.

## Installation

```bash
pip install goalcast-skills
```

## Usage

After installation, the skills will be available in your project's `skills/` directory.

### Claude Code

Create `.claude/settings.json` in your project:

```json
{
  "skills": {
    "goalcast-analyze": {
      "enabled": true,
      "path": "skills/goalcast-analyze"
    },
    "goalcast-get-match-data": {
      "enabled": true,
      "path": "skills/goalcast-get-match-data"
    },
    "goalcast-report": {
      "enabled": true,
      "path": "skills/goalcast-report"
    }
  }
}
```

### OpenClaw

Create `openclaw.json` in your project:

```json
{
  "skills_dir": "skills/",
  "enabled_skills": ["goalcast-analyze", "goalcast-get-match-data", "goalcast-report"]
}
```

## Available Skills

- **goalcast-get-match-data**: Fetch match data for analysis
- **goalcast-analyze**: Execute 8-layer quantitative analysis
- **goalcast-report**: Format analysis results into human-readable reports

## Requirements

- Python 3.10+
- Claude Code or OpenClaw

## License

MIT

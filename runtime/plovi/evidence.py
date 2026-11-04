"""Pure evidence rendering from the runner's verification journal."""
import re
from .util import redact

BEGIN = '<!-- plovi:evidence:start -->'
END = '<!-- plovi:evidence:end -->'

def escape(value):
    text = redact(str(value)).replace('\r', ' ').replace('\n', ' ')
    return re.sub(r'([\\`*_{}\[\]()<>#+.!|])', r'\\\1', text)

HEADING = "## Verification (from plovi's evidence)"
UNRUN = '### Mentioned but not run by plovi'
# Commands a PR body might claim as verification: test runners, builds and interpreters.
CLAIM = re.compile(r"^(?:\S*python[\d.]*(?:\.exe)?\s+-m\s|\S*python[\d.]*(?:\.exe)?\s+\S+\.py\b|npm\s|npx\s|yarn\b|pnpm\b|"
                   r"dotnet\s|go\s+test\b|cargo\s|make\b|mkdocs\b|pytest\b|tox\b|jest\b)")
INTERPRETER = re.compile(r"^(?:.*[/\\])?python[\d.]*(?:\.exe)?$", re.I)


def code(value):
    """Inline code that can't break out of its span; redacted like everything else."""
    return '`' + redact(str(value)).replace('`', "'").replace('\r', ' ').replace('\n', ' ') + '`'


def words(command):
    """A command's words without its interpreter: .venv/bin/python -m mkdocs build -> mkdocs build."""
    parts = str(command).split()
    if parts and INTERPRETER.match(parts[0]):
        parts = parts[2:] if parts[1:2] == ['-m'] else parts[1:]
    return parts


def ran_commands(state):
    rows = list(state.get('green', {}).get('checks', []))
    for evidence in state.get('stage_evidence', {}).values():
        rows += evidence.get('checks', [])
    return [row['command'] for row in rows if row.get('command')]


def mentioned_commands(body):
    """Inline code spans and fenced code lines that look like checks or builds, in order, once each."""
    found = []
    fenced = re.findall(r"^```[^\n]*\n(.*?)^```", body, re.S | re.M)
    without_fences = re.sub(r"^```[^\n]*\n.*?^```", "", body, flags=re.S | re.M)
    candidates = re.findall(r"`([^`\n]+)`", without_fences) + [line for block in fenced for line in block.splitlines()]
    for text in candidates:
        command = re.sub(r"^\$\s+", "", text.strip())
        if command and CLAIM.match(command) and command not in found:
            found.append(command)
    return found


def unverified_claims(state, body, checks=()):
    """Commands the body mentions whose words are not a prefix of a command plovi ran for this task."""
    ran = [words(command) for command in ran_commands(state)]
    named = [words(" ".join(map(str, check["command"]["argv"])))[:2] for check in checks
             if isinstance(check.get("command"), dict) and check["command"].get("argv")]
    claims = []
    for command in mentioned_commands(body) + [m for m in re.findall(r"`([^`\n]+)`", body) if any(
            n and words(m)[:len(n)] == n for n in named)]:
        said = words(command)
        if command not in claims and not any(said == done[:len(said)] for done in ran):
            claims.append(command)
    return claims


def check_lines(state):
    lines = []
    for row in state.get('green', {}).get('checks', []):
        notes = [f"{float(row['duration_seconds']):.1f} s"] if row.get('duration_seconds') is not None else []
        if row.get('skipped'):
            notes.append('skipped: ' + str(row['skipped']) + (', ' + escape(row['approved_skip_reason'])
                                                            if row.get('approved_skip_reason') else ''))
        if row.get('reused'):
            notes.append('reused')
        result = 'passed' if row.get('passed') else 'failed'
        lines.append('- ' + escape(row['id']) + ': ' + result + ', ' + code(row.get('command', 'unknown'))
                     + (' (' + '; '.join(notes) + ')' if notes else ''))
    return lines


def evidence_markdown(state, manifest, body=None):
    """The PR's only verification section, from the runner's journal. With the agent's body, it also lists
    commands the body mentions that plovi never ran."""
    checks = {row['id']: row for row in state.get('green', {}).get('checks', [])}
    lines = [BEGIN, HEADING, ''] + check_lines(state)
    for outcome in manifest.get('outcomes', []):
        results = []
        for name in outcome['checks']:
            row = checks.get(name)
            result = 'passed' if row and row.get('passed') else 'unknown'
            counts = row.get('counts') if row else None
            results.append(escape(name) + ': ' + result + ' (' + escape(counts if counts is not None else 'counts unknown') + ')')
        lines.append('- Outcome ' + escape(outcome['id']) + ': ' + '; '.join(results))
    for stage in state.get('completed', []):
        attempts = [a for a in state.get('attempts', []) if a['stage'] == stage]
        if attempts:
            route = attempts[-1].get('route') or {}
            lines.append('- ' + escape(stage) + ': ' + escape(route.get('provider', 'command')) + ' / ' + escape(route.get('model', 'unknown')))
    lines.append('- Attempts used: ' + str(len(state.get('attempts', []))))
    diff = state.get('diff', {})
    lines.append('- Changed files: ' + escape(diff.get('files', 'unknown')) + '; lines: ' + escape(diff.get('lines', 'unknown')))
    advisory = state.get('diff_advisory')
    if advisory:
        limit = advisory['limit']
        lines.append(f"- Size: {advisory['files']:,} files, {advisory['lines']:,} lines "
                     f"(limit {limit['files']:,}/{limit['lines']:,})")
    for attempt in state.get('attempts', []):
        for assumption in (attempt.get('report') or {}).get('assumptions', []):
            lines.append('- Assumption: ' + escape(assumption))
    lines.append('- Fingerprint: ' + escape(diff.get('fingerprint', state.get('green', {}).get('fingerprint', 'unknown'))))
    claims = unverified_claims(state, body, manifest.get('checks', [])) if body else []
    if claims:
        lines += ['', UNRUN, ''] + ['- ' + code(command) for command in claims]
    return redact('\n'.join(lines) + '\n' + END)

def synchronize(existing, proposed):
    """Replace only the managed section, preserving all other PR content."""
    section = re.search(re.escape(BEGIN) + r'.*?' + re.escape(END), proposed, re.S)
    if not section:
        return existing
    old = re.search(re.escape(BEGIN) + r'.*?' + re.escape(END), existing, re.S)
    if old:
        return existing[:old.start()] + section[0] + existing[old.end():]
    return section[0] + '\n\n' + existing

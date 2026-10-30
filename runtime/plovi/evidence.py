"""Pure evidence rendering from the runner's verification journal."""
import re
from .util import redact

BEGIN = '<!-- plovi:evidence:start -->'
END = '<!-- plovi:evidence:end -->'

def escape(value):
    text = redact(str(value)).replace('\r', ' ').replace('\n', ' ')
    return re.sub(r'([\\`*_{}\[\]()<>#+.!|])', r'\\\1', text)

def evidence_markdown(state, manifest):
    checks = {row['id']: row for row in state.get('green', {}).get('checks', [])}
    lines = [BEGIN, '## Evidence', '']
    for outcome in manifest.get('outcomes', []):
        results = []
        for name in outcome['checks']:
            row = checks.get(name)
            result = 'passed' if row and row.get('passed') else 'unknown'
            counts = row.get('counts') if row else None
            results.append(escape(name) + ': ' + result + ' (' + escape(counts if counts is not None else 'counts unknown') + ')')
        lines.append('- ' + escape(outcome['id']) + ': ' + '; '.join(results))
    for stage in state.get('completed', []):
        attempts = [a for a in state.get('attempts', []) if a['stage'] == stage]
        if attempts:
            route = attempts[-1].get('route') or {}
            lines.append('- ' + escape(stage) + ': ' + escape(route.get('provider', 'command')) + ' / ' + escape(route.get('model', 'unknown')))
    lines.append('- Attempts used: ' + str(len(state.get('attempts', []))))
    diff = state.get('diff', {})
    lines.append('- Changed files: ' + escape(diff.get('files', 'unknown')) + '; lines: ' + escape(diff.get('lines', 'unknown')))
    for attempt in state.get('attempts', []):
        for assumption in (attempt.get('report') or {}).get('assumptions', []):
            lines.append('- Assumption: ' + escape(assumption))
    lines.append('- Fingerprint: ' + escape(diff.get('fingerprint', state.get('green', {}).get('fingerprint', 'unknown'))))
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

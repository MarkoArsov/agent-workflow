"""Portable contract smoke test: python -m model_policy.selftest (no external IO)."""
from itertools import combinations
from .core import evaluate, resolve_settings, validate_snapshot, fingerprint


def run():
    providers = ['claude', 'codex', 'cursor']
    registry = [dict(provider=p, model=p+'-fixture', family=p, lineage='lab-'+p, band='strong', rank=10,
                     stages=['implement', 'implement-tests', 'review'], confidence='reviewed', sources=['https://example.invalid/fixture'],
                     reviewed_at='2026-10-14') for p in providers]
    catalogue = {'providers': {p: {'installed': True, 'models': [{'model': p+'-fixture', 'status': 'advertised'}]} for p in providers}}
    policy = {'test_file_threshold': 4, 'test_line_threshold': 300, 'max_fallbacks': 2, 'adversary_band_slack': 1, 'adversaries': {'implement-tests': ['implement'], 'review': ['implement', 'implement-tests']}}
    cases = 0
    for count in (1, 2, 3):
        for selected in combinations(providers, count):
            settings = resolve_settings([], selected)
            facts = {'stages': ['implement', 'implement-tests', 'review']}
            result = evaluate(registry, policy, catalogue, settings, facts)
            assert not result['unresolved']
            assert all(r['provider'] in selected for routes in result['routes'].values() for r in routes)
            assert result == evaluate(registry, policy, catalogue, settings, facts)
            validate_snapshot(result, result['routes'])
            primaries = [result['routes'][stage][0]['model'] for stage in facts['stages']]
            if count == 3:
                assert len(set(primaries)) == 3
            if count == 1:
                assert any(a['reason'] == 'single-lineage' for a in result['advisories'])
            cases += 1
    # Changed selection semantics travel with exports, independently of the runner.
    rows = [dict(provider='codex', model='routine', family='routine', lineage='lab-a', band='strong', rank=1,
                 stages=['implement', 'implement-tests', 'review'], confidence='reviewed', sources=['https://example.invalid/fixture'],
                 reviewed_at='2026-10-14', efforts={'balanced': 'medium'}),
            dict(provider='codex', model='deep', family='deep', lineage='lab-b', band='deep', rank=2,
                 stages=['implement', 'implement-tests', 'review'], confidence='reviewed', sources=['https://example.invalid/fixture'],
                 reviewed_at='2026-10-14', efforts={'balanced': 'medium', 'demanding': 'high'})]
    observed = {'providers': {'codex': {'installed': True, 'models': [
        {'model': r['model'], 'status': 'advertised', 'efforts': ['medium', 'high']} for r in rows]}}}
    facts = {'stages': ['implement', 'implement-tests', 'review'], 'uncertain': True, 'test_lines': 650,
             'stage_facts': {'implement-tests': {'uncertain': False},
                             'review': {'risk': 'high', 'uncertain': False}}}
    result = evaluate(rows, policy, observed, resolve_settings([], ['codex']), facts)
    assert not result['unresolved']
    assert result['routes']['implement'][0] == {'provider': 'codex', 'model': 'deep', 'reasoning': 'high'}
    assert result['routes']['implement-tests'][0] == {'provider': 'codex', 'model': 'routine', 'reasoning': 'medium'}
    assert result['details']['review']['required_band'] == 'deep'
    assert result['details']['review']['effort_mode'] == 'balanced'
    for version in ('1.0.0', '1.1.0'):
        saved = {'schema_version': 1, 'evaluator_version': version, 'routes': result['routes']}
        saved['snapshot_hash'] = fingerprint(saved)
        validate_snapshot(saved, result['routes'])
    return cases


if __name__ == '__main__':
    print(f'{run()} portable provider-subset contracts passed')

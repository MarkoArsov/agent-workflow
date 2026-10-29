"""Portable contract smoke test: python -m model_policy.selftest (no external IO)."""
from itertools import combinations
from .core import evaluate, resolve_settings, validate_snapshot


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
    return cases


if __name__ == '__main__':
    print(f'{run()} portable provider-subset contracts passed')

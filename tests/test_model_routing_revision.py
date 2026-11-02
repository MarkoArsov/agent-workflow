"""Tests for improved model routing: stage isolation, advisories, effort vs band, provenance."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
from tests.helpers import PACKAGE, WorkspaceTest
from plovi.model_policy import core
from plovi.model_policy.storage import Store, write, read


def entry(provider, model, band='strong', family=None, rank=10, **extra):
    return dict(
        provider=provider, model=model, band=band, family=family or model,
        stages=['specify', 'implement-tests', 'implement', 'review'], rank=rank,
        confidence='reviewed', sources=['https://example.invalid/evidence'],
        reviewed_at='2026-10-14', **extra,
    )


def catalogue(entries):
    result = {'schema_version': 1, 'providers': {}}
    for e in entries:
        row = result['providers'].setdefault(e['provider'], {
            'installed': True,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'models': [],
        })
        row['models'].append({'model': e['model'], 'status': 'advertised', 'efforts': ['low', 'medium', 'high']})
    return result


class ModelRoutingRevisionTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.policy = read(PACKAGE / 'runtime/plovi/model_policy/policy.json')
        self.entries = [
            entry('codex', 'codex-strong', band='strong', lineage='lab-codex', rank=10,
                  efforts={'simple': 'low', 'balanced': 'medium', 'demanding': 'high'}),
            entry('codex', 'codex-deep', band='deep', lineage='lab-codex', rank=5,
                  efforts={'balanced': 'medium', 'demanding': 'high'}),
            entry('claude', 'claude-strong', band='strong', lineage='lab-claude', rank=20,
                  efforts={'simple': 'low', 'balanced': 'medium', 'demanding': 'high'}),
            entry('claude', 'claude-deep', band='deep', lineage='lab-claude', rank=25,
                  efforts={'balanced': 'medium', 'demanding': 'high'}),
        ]
        self.catalogue = catalogue(self.entries)
        self.store = Store(
            self.home / 'data/models',
            self.root / 'project/models.json',
            workflow='fixture',
        )

    def evaluate(self, facts=None, entries=None, settings=None, catalog=None):
        return core.evaluate(
            entries if entries is not None else self.entries,
            self.policy,
            catalog if catalog is not None else self.catalogue,
            settings or core.resolve_settings([], core.PROVIDERS),
            facts or {'stages': ['implement', 'review']},
        )

    # ---- red checks (routing-red) ------------------------------------------

    def test_large_routine_tests_do_not_force_deep(self):
        # 650 estimated test lines is large but routine: should get strong/balanced, not deep/high.
        # Currently fails because test_scope forces deep/demanding regardless of complexity.
        facts = {'stages': ['implement-tests'], 'test_lines': 650}
        result = self.evaluate(facts)
        self.assertFalse(result['unresolved'], f"Large routine tests must resolve: {result['unresolved']}")
        route = result['routes']['implement-tests'][0]
        self.assertEqual(
            route.get('reasoning'), 'medium',
            f"Expected balanced (medium) effort for large-but-routine tests; got: {route}",
        )

    def test_stage_difficulty_does_not_spread(self):
        # Complex uncertain implementation + large test scope: test stage must get strong/balanced.
        # Currently fails because test_scope escalates implement-tests to deep/demanding.
        facts = {
            'stages': ['implement', 'implement-tests'],
            'uncertain': True,
            'test_lines': 650,
            # Tests are certain and routine; only implementation is uncertain (E2: per-stage override).
            'stage_facts': {'implement-tests': {'uncertain': False}},
        }
        result = self.evaluate(facts)
        self.assertFalse(result['unresolved'], f"Stages must resolve: {result['unresolved']}")
        impl_route = result['routes']['implement'][0]
        test_route = result['routes']['implement-tests'][0]
        self.assertIn(
            impl_route['model'], {'codex-deep', 'claude-deep'},
            f"Uncertain implement must use deep model; got: {impl_route}",
        )
        self.assertEqual(
            test_route.get('reasoning'), 'medium',
            f"Test stage must get balanced effort despite uncertain implement; got: {test_route}",
        )

    # ---- green checks (routing-revision) -----------------------------------

    def test_deep_capability_can_use_balanced_effort(self):
        # High risk requires deep capability but routine complexity maps to balanced effort.
        facts = {'stages': ['review'], 'risk': 'high', 'demanding_stages': ['review']}
        result = self.evaluate(facts)
        self.assertFalse(result['unresolved'], f"High-risk review must resolve: {result['unresolved']}")
        route = result['routes']['review'][0]
        self.assertIn(
            route['model'], {'codex-deep', 'claude-deep'},
            f"High-risk review must use deep model; got: {route}",
        )
        self.assertEqual(
            route.get('reasoning'), 'medium',
            f"Deep capability with routine complexity must use balanced (medium) effort; got: {route}",
        )

    def test_planner_suggestion_does_not_override_pin(self):
        # A project pin wins over any planner suggestion in task facts.
        pin = {'provider': 'codex', 'model': 'codex-strong', 'reasoning': 'high'}
        settings = core.resolve_settings(
            [{'schema_version': 1, 'pins': {'implement': [pin]}}],
            ['codex', 'claude'],
        )
        facts = {
            'stages': ['implement'],
            'suggested_routes': {'implement': [{'provider': 'claude', 'model': 'claude-strong'}]},
        }
        try:
            core.validate_facts(facts)
        except (ValueError, KeyError):
            self.fail('validate_facts must accept suggested_routes without raising')
        result = self.evaluate(facts, settings=settings)
        self.assertEqual(
            result['routes']['implement'][0], pin,
            'Project pin must not be displaced by planner suggestion',
        )

    def test_suggestion_cannot_promote_unavailable_model(self):
        # A suggestion for an unavailable model is ignored; policy eligibility applies.
        unavailable = entry('claude', 'claude-unavailable', band='strong', lineage='lab-claude',
                            rank=1, efforts={'balanced': 'medium'})
        cat = deepcopy(self.catalogue)
        cat['providers']['claude'] = {
            'installed': True,
            'observed_at': '2026-11-01T00:00:00+00:00',
            'models': [{'model': 'claude-unavailable', 'status': 'unavailable'}],
        }
        entries = [e for e in self.entries if e['provider'] != 'claude'] + [unavailable]
        facts = {
            'stages': ['implement'],
            'suggested_routes': {'implement': [{'provider': 'claude', 'model': 'claude-unavailable'}]},
        }
        try:
            result = self.evaluate(facts, entries=entries, catalog=cat)
        except (ValueError, KeyError) as exc:
            self.fail(f'Suggestion for unavailable model must not raise: {exc}')
        selected = result['routes']['implement'][0] if result['routes'].get('implement') else {}
        self.assertNotEqual(
            selected.get('model'), 'claude-unavailable',
            'Unavailable model must not be selected even when suggested',
        )

    def test_route_sources_are_explained(self):
        # Every stage in the result must have a non-empty reason explaining its route source.
        facts = {'stages': ['implement', 'implement-tests', 'review']}
        result = self.evaluate(facts)
        for stage in facts['stages']:
            self.assertIn(stage, result.get('reasons', {}), f"Stage {stage} missing from reasons")
            reason = result['reasons'][stage]
            self.assertIsInstance(reason, str)
            self.assertTrue(reason, f"Route reason for {stage} must be non-empty")

    def test_missing_catalogue_explanation_is_precise(self):
        # When no catalogue is present and a configured default exists, the notice must not
        # claim adaptive selection; the reason must distinguish retained from adaptive.
        route = {'provider': 'codex', 'model': 'codex-strong', 'reasoning': 'medium'}
        write(self.store.global_file, {'schema_version': 1, 'defaults': {'implement': [route]}})
        result = self.store.evaluate({'stages': ['implement']})
        self.assertFalse(result['unresolved'], f"Retained default must resolve: {result['unresolved']}")
        notice = result.get('notice', '')
        self.assertTrue(notice, 'Missing catalogue must produce a notice')
        self.assertNotIn(
            'adaptive', notice.lower(),
            'Retained route must not be labeled adaptive selection in the notice',
        )
        self.assertIn(
            result['reasons']['implement'],
            {'retained-configured-default', 'explicit-route'},
            f"Retained default must have matching reason; got {result['reasons']['implement']!r}",
        )

    def test_old_snapshots_remain_valid(self):
        # Saved 1.0 and 1.1 snapshot hashes must validate without re-running selection rules.
        for version in ('1.0.0', '1.1.0'):
            snap = {
                'schema_version': 1,
                'evaluator_version': version,
                'routes': {'implement': [{'provider': 'codex', 'model': 'codex-strong', 'reasoning': 'medium'}]},
                'reasons': {'implement': 'explicit-route'},
                'unresolved': [],
                'advisories': [],
            }
            snap['snapshot_hash'] = core.fingerprint(snap)
            core.validate_snapshot(snap, snap['routes'])  # Must not raise

    def test_max_effort_is_never_automatic(self):
        # Even in demanding scenarios, xhigh/max/ultra must never appear as reasoning.
        facts = {'stages': ['implement'], 'risk': 'high', 'uncertain': True, 'demanding_stages': ['implement']}
        result = self.evaluate(facts)
        for route in result['routes'].get('implement', []):
            self.assertNotIn(
                route.get('reasoning'), {'xhigh', 'max', 'ultra'},
                f"Max effort must never be automatically selected; got: {route}",
            )

    def test_effective_project_defaults_allow_both_providers(self):
        # After migration to adaptive stages both providers are allowed with no effective pins.
        settings = core.resolve_settings(
            [
                {'schema_version': 1, 'providers': ['codex', 'claude']},
                {'schema_version': 1, 'adaptive_stages': ['implement', 'implement-tests', 'review']},
            ],
            ['codex', 'claude'],
        )
        result = self.evaluate(
            {'stages': ['implement', 'implement-tests', 'review']},
            settings=settings,
        )
        self.assertFalse(result['unresolved'], f"Both-provider setup must resolve: {result['unresolved']}")
        self.assertIn('codex', settings['providers'])
        self.assertIn('claude', settings['providers'])
        for stage in ('implement', 'implement-tests', 'review'):
            self.assertNotIn(stage, settings.get('pins', {}))

    def test_repository_settings_release_legacy_pins_through_adapter(self):
        from plovi.project import Project
        from plovi.model_routing import store
        project = Project(self.root, read(PACKAGE / '.plovi/project.json'))
        write(project.config / 'models.json', read(PACKAGE / '.plovi/models.json'))
        configured = store(project)
        effective = configured.effective()
        self.assertEqual(set(effective['providers']), {'codex', 'claude'})
        for stage in ('implement-tests', 'implement', 'review', 'default'):
            self.assertNotIn(stage, effective['pins'])
            self.assertTrue(effective['defaults'][stage])
        result = configured.evaluate({'stages': ['implement-tests', 'implement', 'review']})
        self.assertTrue(all(d['route_source'] == 'retained-default' for d in result['details'].values()))
        self.assertIn('No model catalogue', result['notice'])

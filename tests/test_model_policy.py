"""Isolated model routing tests. Discovery doubles do not establish account access."""
from copy import deepcopy
from datetime import datetime, timezone
import itertools
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
from tests.helpers import WorkspaceTest, PACKAGE
from plovi.model_policy import core, storage, discovery
from plovi.model_policy.storage import Store, write, read


def entry(provider, model, band='strong', family=None, rank=10, **extra):
    return dict(provider=provider, model=model, band=band, family=family or model,
                stages=['specify','implement-tests','implement','review'], rank=rank,
                confidence='reviewed', sources=['https://example.invalid/evidence'],
                reviewed_at='2026-10-14', **extra)


def catalogue(entries):
    result = {'schema_version':1,'providers':{}}
    for e in entries:
        row = result['providers'].setdefault(e['provider'], {'installed':True,'observed_at':datetime.now(timezone.utc).isoformat(),'models':[]})
        row['models'].append({'model':e['model'],'status':'advertised','efforts':['low','medium','high']})
    return result


class ModelPolicyTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.policy = read(PACKAGE/'runtime/plovi/model_policy/policy.json')
        self.entries = [entry(p,p+'-routine',efforts={'balanced':'medium','demanding':'high'} if p != 'cursor' else {}) for p in sorted(core.PROVIDERS)]
        self.catalogue = catalogue(self.entries)
        self.store = Store(self.home/'data/models',self.root/'project/models.json',workflow='fixture')

    def evaluate(self, facts=None, entries=None, settings=None, catalog=None):
        return core.evaluate(entries if entries is not None else self.entries,self.policy,catalog if catalog is not None else self.catalogue,settings or core.resolve_settings([], core.PROVIDERS),facts or {'stages':['implement','review']})

    def test_all_provider_subsets_are_respected(self):
        for count in (1,2,3):
            for subset in itertools.combinations(sorted(core.PROVIDERS),count):
                result=self.evaluate(settings=core.resolve_settings([],subset))
                self.assertFalse(result['unresolved'])
                self.assertTrue(all(r['provider'] in subset for routes in result['routes'].values() for r in routes))
        result=self.evaluate(settings=core.resolve_settings([],[]))
        self.assertTrue(result['unresolved'])

    def test_stable_selection_and_no_network_or_provider_calls(self):
        with patch('subprocess.Popen',side_effect=AssertionError('provider call')),patch('socket.socket',side_effect=AssertionError('network')):
            a=self.evaluate(); b=self.evaluate()
        self.assertEqual(a,b)
        self.assertEqual(a['routes']['implement'][0]['reasoning'],'medium')
        self.assertNotEqual(a['routes']['implement'][0]['model'],a['routes']['review'][0]['model'])

    def test_test_author_boundary_and_effort(self):
        entries=[entry('codex','routine',efforts={'balanced':'medium'}),entry('codex','deep','deep',efforts={'balanced':'medium','demanding':'high'})]
        for files,lines,model,effort in [(3,299,'routine','medium'),(4,299,'deep','high'),(3,300,'deep','high')]:
            result=self.evaluate({'stages':['implement-tests'],'test_files':files,'test_lines':lines},entries,catalog=catalogue(entries))
            self.assertEqual(result['routes']['implement-tests'][0],{'provider':'codex','model':model,'reasoning':effort})

    def test_high_risk_escalates_affected_stage_only(self):
        entries=[*self.entries,entry('codex','deep','deep',efforts={'demanding':'high'})]
        result=self.evaluate({'stages':['implement','review'],'risk':'high','demanding_stages':['review']},entries,catalog=catalogue(entries))
        self.assertNotEqual(result['routes']['implement'][0]['model'],'deep')
        self.assertEqual(result['routes']['review'][0]['model'],'deep')

    def test_pins_not_replaced_and_inadequacy_is_advisory(self):
        route={'provider':'codex','model':'codex-routine','reasoning':'high'}
        settings=core.resolve_settings([{'schema_version':1,'pins':{'implement':[route]}}],['codex'])
        result=self.evaluate({'stages':['implement'],'risk':'high'},settings=settings)
        self.assertEqual(result['routes']['implement'],[route]);self.assertTrue(result['advisories']);self.assertFalse(result['unresolved'])

    def test_missing_effort_omits_argument_and_max_is_not_automatic(self):
        entries=[entry('codex','one',efforts={'balanced':'max'})]
        result=self.evaluate(entries=entries,catalog=catalogue(entries))
        self.assertNotIn('reasoning',result['routes']['implement'][0])
        entries=[entry('cursor','one-max',encoded_effort='max')]
        self.assertTrue(self.evaluate(entries=entries,catalog=catalogue(entries))['unresolved'])

    def test_cursor_uses_exact_mode_ids(self):
        entries=[entry('cursor','x-medium',encoded_effort='medium',modes=['balanced']),entry('cursor','x-high','deep',encoded_effort='high',modes=['demanding'])]
        normal=self.evaluate(entries=entries,catalog=catalogue(entries))
        hard=self.evaluate({'stages':['implement'],'risk':'high'},entries,catalog=catalogue(entries))
        self.assertEqual(normal['routes']['implement'][0],{'provider':'cursor','model':'x-medium'})
        self.assertEqual(hard['routes']['implement'][0],{'provider':'cursor','model':'x-high'})

    def test_unreviewed_and_unavailable_are_not_promoted(self):
        entries=[entry('codex','new')]
        entries[0]['confidence']='provisional'
        self.assertTrue(self.evaluate(entries=entries,catalog=catalogue(entries))['unresolved'])
        entries[0]['confidence']='reviewed'; cat=catalogue(entries);cat['providers']['codex']['models'][0]['status']='unavailable'
        self.assertTrue(self.evaluate(entries=entries,catalog=cat)['unresolved'])

    def test_per_stage_inheritance_restrictions_and_legacy_pins(self):
        route={'provider':'codex','model':'old'}
        global_policy={'schema_version':1,'providers':['codex'],'defaults':{'review':[route]},'blocked':['codex:blocked']}
        project_policy={'schema_version':1,'providers':['codex','cursor'],'defaults':{'implement':[]},'adaptive_stages':['implement']}
        result=core.resolve_settings([global_policy,project_policy],core.PROVIDERS,{'implement':[route]})
        self.assertEqual(result['providers'],['codex']);self.assertEqual(result['defaults']['review'],[route]);self.assertEqual(result['defaults']['implement'],[]);self.assertFalse(result['pins']);self.assertIn('codex:blocked',result['blocked'])

    def test_missing_cache_retains_default(self):
        route={'provider':'codex','model':'existing','reasoning':'high'}
        write(self.store.global_file,{'schema_version':1,'defaults':{'implement':[route]}})
        result=self.store.evaluate({'stages':['implement']})
        self.assertEqual(result['routes']['implement'],[route]);self.assertIn('notice',result)

    def test_snapshots_survive_changed_defaults_and_detect_tampering(self):
        result=self.evaluate(); core.validate_snapshot(result,result['routes'])
        self.policy['test_file_threshold']=99
        core.validate_snapshot(result,result['routes'])
        changed=deepcopy(result);changed['routes']['implement'][0]['model']='changed'
        with self.assertRaises(ValueError):core.validate_snapshot(changed)

    def test_proposal_exact_scope_concurrency_and_independence(self):
        updates={'global':{'schema_version':1,'providers':['codex']},'project':{'schema_version':1,'defaults':{}}}
        other=Store(self.home/'data/other',workflow='other')
        proposal=self.store.propose(updates,'both')
        self.assertFalse(self.store.global_file.exists())
        with self.assertRaises(ValueError):other.apply(proposal,proposal['approval'])
        self.store.apply(proposal,proposal['approval'])
        self.assertEqual(self.store.effective()['providers'],['codex']);self.assertFalse(other.global_file.exists())
        with self.assertRaises(ValueError):self.store.apply(proposal,proposal['approval'])

    def test_settings_lock_rejects_overlap_and_releases_after_failure(self):
        with self.assertRaisesRegex(RuntimeError, "interrupted"):
            with self.store.lock():
                with self.assertRaisesRegex(ValueError, "in progress"):
                    with self.store.lock():
                        self.fail("Concurrent settings writer entered")
                raise RuntimeError("interrupted")
        with self.store.lock():
            self.assertTrue((self.store.data / "write.lock").exists())

    def test_partial_failure_rolls_back_and_keeps_backup(self):
        proposal=self.store.propose({'global':{'schema_version':1},'project':{'schema_version':1}},'both')
        real_write=storage.write
        def fail_project(path,value):
            if Path(path)==self.store.project:raise OSError('simulated disk failure')
            return real_write(path,value)
        with patch.object(storage,'write',side_effect=fail_project):
            with self.assertRaises(OSError):self.store.apply(proposal,proposal['approval'])
        self.assertFalse(self.store.global_file.exists());self.assertFalse(self.store.project.exists())
        self.assertTrue((self.store.data/'backups'/f"{proposal['approval']}.json").exists())

    def test_crash_recovery_preserves_concurrent_edit(self):
        p=self.store.propose({'global':{'schema_version':1}},'global')
        write(self.store.data/'pending.json',p);write(self.store.global_file,{'schema_version':1,'providers':['cursor']})
        with self.assertRaises(ValueError):self.store.recover()
        self.assertEqual(read(self.store.global_file)['providers'],['cursor'])
        write(self.store.global_file,p['changes'][0]['after']);self.store.recover()
        self.assertFalse(self.store.global_file.exists())

    def test_cursor_listing_and_refresh_failure_preserve_evidence(self):
        rows=discovery.cursor_models('Available models\nauto - Auto\nx-medium - Model Medium\n')
        self.assertEqual(rows,[{'model':'x-medium','status':'advertised'}])
        with patch.object(discovery.shutil,'which',return_value='/fake'),patch.object(discovery,'capture',side_effect=ValueError('offline')):
            result=discovery.discover(['codex'],self.root,self.catalogue)
        self.assertEqual(result['providers']['codex']['models'],self.catalogue['providers']['codex']['models']);self.assertTrue(result['errors'])

    def test_export_is_independent_and_detects_edits(self):
        sys.path.insert(0,str(PACKAGE/'scripts'))
        self.addCleanup(lambda:sys.path.remove(str(PACKAGE/'scripts')))
        from export_model_policy import export
        target=self.root/'vendored/model_policy';export(target);export(target,check=True)
        import subprocess
        check=subprocess.run([sys.executable,'-m','model_policy.selftest'],cwd=target.parent,env=self.env,capture_output=True,text=True,check=True)
        self.assertIn('7 portable',check.stdout)
        (target/'core.py').write_text('local edit')
        with self.assertRaises(ValueError):export(target)

    def test_500_entries_stay_fast(self):
        entries=[entry('codex',f'model-{i:04d}') for i in range(500)]
        cat=catalogue(entries)
        started=time.perf_counter();result=self.evaluate(entries=entries,catalog=cat);elapsed=time.perf_counter()-started
        self.assertFalse(result['unresolved']);self.assertLess(elapsed,.1)

    def test_cli_evaluates_without_project_or_host_access(self):
        facts=self.root/'facts.json';write(facts,{'stages':['implement']})
        r=self.cli('models','evaluate','--input',facts,cwd=self.root)
        self.assertIn('No model catalogue',r.stdout)

    def test_machine_policy_cannot_replace_existing_project_pin(self):
        project_route={'provider':'codex','model':'project'}
        machine_route={'provider':'codex','model':'machine'}
        result=core.resolve_settings([{'schema_version':1,'pins':{'implement':[machine_route]},'adaptive_stages':['implement']},{'schema_version':1}],['codex'],{'implement':[project_route]})
        self.assertEqual(result['pins']['implement'],[project_route])

    def test_preview_assessment_does_not_write_settings(self):
        write(self.store.data/'catalogue.json',self.catalogue)
        result=self.store.evaluate({'stages':['implement']},{'global':{'schema_version':1,'registry':self.entries}})
        self.assertFalse(result['unresolved']);self.assertFalse(self.store.global_file.exists())

    def test_missing_provider_does_not_invalidate_other_catalogues(self):
        cat=deepcopy(self.catalogue);cat['providers']['claude']={'installed':False,'models':[]}
        write(self.store.data/'catalogue.json',cat)
        result=self.store.evaluate({'stages':['implement']},{'global':{'schema_version':1,'registry':self.entries}})
        self.assertNotIn('notice',result);self.assertFalse(result['unresolved'])

    def test_required_capabilities_never_silently_downgrade(self):
        result=self.evaluate({'stages':['implement'],'required_capabilities':['image']})
        self.assertTrue(result['unresolved'])
        entries=deepcopy(self.entries);entries[0]['capabilities']=['image']
        result=self.evaluate({'stages':['implement'],'required_capabilities':['image']},entries)
        self.assertEqual(result['routes']['implement'][0]['model'],entries[0]['model'])

    def test_invalid_cache_is_nonblocking_when_default_is_valid(self):
        write(self.store.global_file,{'schema_version':1,'defaults':{'implement':[{'provider':'codex','model':'known'}]}})
        write(self.store.data/'catalogue.json',{'schema_version':1,'providers':{'codex':None}})
        result=self.store.evaluate({'stages':['implement']})
        self.assertFalse(result['unresolved']);self.assertIn('notice',result)

    def test_changed_profile_cannot_apply_a_different_effective_proposal(self):
        p=self.store.propose({'global':{'schema_version':1}},'global')
        self.store.providers=['cursor']
        with self.assertRaisesRegex(ValueError,'restrictions'):self.store.apply(p,p['approval'])
        self.assertFalse(self.store.global_file.exists())

    def test_global_skill_dispatch_without_a_project(self):
        result=self.cli('models','inspect',cwd=self.root)
        self.assertIsNone(json.loads(result.stdout)['project'])
        import subprocess
        output=subprocess.run([sys.executable,str(PACKAGE/'skills/update-models/scripts/resolve.py')],cwd=self.root,env=self.env,capture_output=True,text=True,check=True)
        self.assertEqual(output.stdout.strip(),str(PACKAGE/'skills/update-models/SKILL.md'))

    def test_adversary_lineage_prefers_alternate_lab(self):
        rows = [entry('codex', 'favored', lineage='lab-a', rank=1),
                entry('codex', 'alternate', lineage='lab-b', rank=99),
                entry('codex', 'third', lineage='lab-c', rank=100)]
        result = self.evaluate({'stages':['review','implement-tests','implement']}, rows, catalog=catalogue(rows))
        self.assertEqual(result['routes']['implement'][0]['model'], 'favored')
        self.assertEqual(result['routes']['implement-tests'][0]['model'], 'alternate')
        self.assertEqual(result['routes']['review'][0]['model'], 'third')
        ordered = self.evaluate({'stages':['implement','implement-tests','review']}, rows, catalog=catalogue(rows))
        self.assertEqual(result['routes'], ordered['routes'])

    def test_adversary_band_slack_and_single_lineage_are_advisory(self):
        rows = [entry('codex','deep-a','deep',lineage='lab-a'), entry('cursor','strong-b',lineage='lab-b')]
        facts = {'stages':['implement','review'],'risk':'high'}
        result = self.evaluate(facts,rows,catalog=catalogue(rows))
        self.assertEqual(result['routes']['review'][0]['model'],'strong-b')
        self.assertIn({'stage':'review','reason':'adversary-below-band'},result['advisories'])
        self.assertFalse(result['unresolved'])
        rows[1]['lineage']='lab-a'
        result=self.evaluate(facts,rows,catalog=catalogue(rows))
        self.assertEqual(result['routes']['review'][0]['model'],'deep-a')
        self.assertIn({'stage':'review','reason':'single-lineage'},result['advisories'])
        rows[1]['lineage']='lab-b'; rows[1]['band']='fast'
        result=self.evaluate(facts,rows,catalog=catalogue(rows))
        self.assertEqual(result['routes']['review'][0]['model'],'deep-a')

    def test_fallbacks_diversify_labs_not_harnesses(self):
        rows=[entry('codex','a',lineage='lab-a',rank=1),entry('cursor','b',lineage='lab-a',rank=2),
              entry('cursor','c',lineage='lab-b',rank=99)]
        result=self.evaluate({'stages':['implement']},rows,catalog=catalogue(rows))
        self.assertEqual([r['model'] for r in result['routes']['implement']],['a','c','b'])

    def test_legacy_lineage_is_unknown_and_pins_stay_fixed(self):
        rows=[entry('codex','old'),entry('cursor','other')]
        settings=core.resolve_settings([{'schema_version':1,'pins':{'implement':[{'provider':'codex','model':'old'}]}}],core.PROVIDERS)
        before=deepcopy(settings)
        result=self.evaluate({'stages':['implement','review']},rows,settings,catalogue(rows))
        self.assertEqual(settings,before)
        self.assertEqual(result['routes']['implement'],[{'provider':'codex','model':'old'}])
        self.assertIn({'stage':'review','reason':'unknown-lineage'},result['advisories'])
        rows[0]['lineage']='Not a slug'
        with self.assertRaisesRegex(ValueError,'lineage'):
            self.evaluate(entries=rows,catalog=catalogue(rows))

    def test_legacy_snapshot_survives_evaluator_upgrade(self):
        legacy={'schema_version':1,'evaluator_version':'1.0.0','routes':{'implement':[{'provider':'codex','model':'old'}]},
                'reasons':{},'unresolved':[],'advisories':[]}
        legacy['snapshot_hash']=core.fingerprint(legacy)
        core.validate_snapshot(legacy,legacy['routes'])

    def test_diversity_never_adds_an_unreported_lower_band_fallback(self):
        rows=[entry('codex','deep-a','deep',lineage='lab-a',rank=1),
              entry('codex','deep-b','deep',lineage='lab-b',rank=2),
              entry('cursor','strong-c',lineage='lab-c',rank=3)]
        result=self.evaluate({'stages':['implement','review'],'risk':'high'},rows,catalog=catalogue(rows))
        self.assertEqual(result['routes']['review'][0]['model'],'deep-b')
        self.assertNotIn('strong-c',[r['model'] for r in result['routes']['review']])
        self.assertNotIn({'stage':'review','reason':'adversary-below-band'},result['advisories'])

    def test_exact_reviewed_match_supplies_legacy_lineage_without_writes(self):
        base=[entry('codex','a',lineage='lab-a'),entry('cursor','b',lineage='lab-b')]
        legacy=deepcopy(base[0]);del legacy['lineage']
        settings=core.resolve_settings([{'schema_version':1,'registry':[legacy],
            'pins':{'implement':[{'provider':'codex','model':'a'}],
                    'review':[{'provider':'codex','model':'a'}]}}],core.PROVIDERS)
        before=deepcopy(settings)
        result=self.evaluate({'stages':['implement','review']},base,settings,catalogue(base))
        self.assertEqual(before,settings)
        self.assertIn({'stage':'review','reason':'single-lineage'},result['advisories'])
        self.assertNotIn({'stage':'review','reason':'unknown-lineage'},result['advisories'])

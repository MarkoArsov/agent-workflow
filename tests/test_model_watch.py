"""Synthetic AA responses and isolated homes; no real keys or network."""
from copy import deepcopy
from datetime import datetime, timezone
import io
import json
import os
import subprocess
import urllib.error
from unittest.mock import patch
from tests.helpers import WorkspaceTest, PACKAGE
from plovi.model_policy import watch, commands
from plovi.model_policy.storage import Store, read, write
from plovi.cli import parser


def model(slug='fixture-model', creator='Lab A', released='2026-10-20'):
    return {'id':slug,'slug':slug,'name':'Fixture '+slug,'release_date':released,
            'model_creator':{'id':'lab-a','name':creator},
            'evaluations':{'artificial_analysis_intelligence_index':42,'artificial_analysis_coding_index':None},
            'pricing':{'price_1m_input_tokens':1,'price_1m_output_tokens':2},
            'performance':{'median_output_tokens_per_second':50}}


def page(rows=None, number=1, total=1, version=5):
    return {'data':[model()] if rows is None else rows,'tier':'free','intelligence_index_version':version,
            'pagination':{'page':number,'total_pages':total,'has_more':number<total}}


class ModelWatchTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.store=Store(self.home/'data/models', self.root/'project/models.json', workflow='fixture')
        self.path=self.store.data/'watch.json'
        self.now=datetime(2026,10,29,12,tzinfo=timezone.utc)
        self.key='synthetic-watch-key-12345'
        os.environ['AA_API_KEY']=self.key
        self.payloads=[]
        self.requests=[]
        self.opener=patch.object(watch.urllib.request,'build_opener').start()
        self.addCleanup(patch.stopall)
        def opened(request, timeout):
            self.requests.append((request,timeout))
            item=self.payloads.pop(0)
            if isinstance(item,Exception): raise item
            return io.BytesIO(json.dumps(item).encode() if not isinstance(item,bytes) else item)
        self.opener.return_value.open.side_effect=opened

    def refresh(self, *payloads):
        self.payloads=list(payloads) or [page()]
        return watch.refresh(self.store, now=self.now)

    def test_complete_pages_and_allowlisted_snapshot_do_not_change_settings(self):
        write(self.store.global_file,{'schema_version':1,'defaults':{'implement':[{'provider':'codex','model':'pinned'}]}})
        write(self.store.project,{'schema_version':1,'pins':{'implement':[{'provider':'codex','model':'actual'}]}})
        settings=[p.read_bytes() for p in (self.store.global_file,self.store.project)]
        extra=model();extra['raw_secret']=self.key
        with patch('subprocess.Popen',side_effect=AssertionError('provider execution')), patch.object(self.store,'evaluate',side_effect=AssertionError('route selection')):
            report=self.refresh(page([extra],1,2),page([model('second')],2,2))
        snapshot=read(self.path)
        self.assertEqual(len(snapshot['models']),2)
        self.assertEqual(snapshot['models'][0]['performance']['median_output_tokens_per_second'],50)
        self.assertIsNone(snapshot['models'][0]['evaluations']['artificial_analysis_coding_index'])
        self.assertNotIn(self.key,self.path.read_text())
        self.assertEqual(settings,[p.read_bytes() for p in (self.store.global_file,self.store.project)])
        self.assertEqual(report['routes'][0]['model'],'actual')
        self.assertFalse(report['routes'][0]['matched'])
        self.assertEqual(report['routes'][0]['catalogue_status'],'missing-catalogue')
        self.assertTrue(report['baseline']); self.assertEqual(report['new'],[])
        self.assertFalse(report['routes_changed'])
        request,timeout=self.requests[0]
        self.assertEqual(request.get_header('X-api-key'),self.key)
        self.assertEqual(request.full_url,watch.SOURCE+'?page=1')
        self.assertLessEqual(timeout,10)

    def test_bad_or_incomplete_fetch_preserves_previous_bytes(self):
        self.refresh()
        before=self.path.read_bytes()
        variants=[b'not json',{},page(rows=[{}]),page(number=2),page(total=100),
                  page(rows=[model(),model()]),page(rows=[dict(model(), release_date='invalid')]),
                  page(rows=[dict(model(),pricing=[])]),page(rows=[dict(model(),name=self.key)]),
                  OSError('network '+self.key),
                  urllib.error.HTTPError(watch.SOURCE,401,self.key,{},io.BytesIO(self.key.encode())),
                  urllib.error.HTTPError(watch.SOURCE,429,self.key,{},io.BytesIO(self.key.encode())),
                  urllib.error.HTTPError(watch.SOURCE,500,self.key,{},io.BytesIO(self.key.encode()))]
        for payload in variants:
            with self.subTest(payload_type=type(payload).__name__):
                with self.assertRaises(ValueError) as error: self.refresh(payload)
                self.assertNotIn(self.key,str(error.exception))
                self.assertEqual(self.path.read_bytes(),before)
        with self.assertRaises(ValueError):
            self.refresh(page(number=1,total=2),page([model('second')],2,2,version=6))
        self.assertEqual(self.path.read_bytes(),before)

    def test_bounds_and_redirect_never_forward_credentials(self):
        self.refresh();before=self.path.read_bytes()
        with patch.object(watch,'MAX_BYTES',10):
            with self.assertRaises(ValueError): self.refresh()
        with patch.object(watch.time,'monotonic',side_effect=[0,46]):
            with self.assertRaises(ValueError): self.refresh()
        redirected=io.BytesIO(b'untrusted body')
        with self.assertRaisesRegex(ValueError,'redirect'):
            watch.NoRedirect().redirect_request(None,redirected,302,'',{},'https://example.invalid/')
        self.assertTrue(redirected.closed)
        self.assertEqual(self.path.read_bytes(),before)

    def test_key_file_is_explicit_and_never_executed(self):
        path=self.home/'key.env'
        marker=self.root/'must-not-exist'
        path.write_text(f"OTHER_KEY=ignored\nexport AA_API_KEY='file-key-value'\ntouch {marker}\n")
        self.assertEqual(watch.load_key(path),self.key)
        del os.environ['AA_API_KEY']
        self.assertEqual(watch.load_key(path),'file-key-value')
        self.assertFalse(marker.exists())
        with self.assertRaisesRegex(ValueError,'Set AA_API_KEY'): watch.load_key()
        with self.assertRaises(ValueError): watch.load_key(self.home/'missing')
        self.assertFalse(self.path.exists())

    def test_atomic_write_failure_preserves_snapshot(self):
        self.refresh();before=self.path.read_bytes()
        with patch('plovi.model_policy.storage.os.replace',side_effect=OSError('disk')):
            with self.assertRaises(OSError): self.refresh(page([model('new')]))
        self.assertEqual(self.path.read_bytes(),before)
        self.assertFalse(list(self.path.parent.glob('.watch.json*')))

    def test_null_numbers_and_malformed_types(self):
        for value in (True,float('nan'),float('inf'),-1,'42'):
            item=model();item['pricing']['price_1m_input_tokens']=value
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(ValueError): self.refresh(page([item]))
        item=model();item['evaluations']['artificial_analysis_intelligence_index']=-1.5
        self.refresh(page([item]))
        self.assertEqual(read(self.path)['models'][0]['evaluations']['artificial_analysis_intelligence_index'],-1.5)
        self.path.unlink()
        report=self.refresh(page([]))
        self.assertEqual(report['model_count'],0)
        self.assertTrue(report['baseline'])

    def test_reporting_dates_versions_aliases_and_effective_catalogue(self):
        current={'fetched_at':self.now.isoformat(),'models':watch.normalize([model(),model('future',released='2026-12-01')]),'intelligence_index_version':5}
        previous={'models':watch.normalize([model('gone'),model()]),'intelligence_index_version':5}
        current['models'][0]['pricing']['price_1m_input_tokens']=3
        aliases={'schema_version':1,'routes':[{'provider':'codex','model':'host-model','slug':'fixture-model'}]}
        routes={'implement':[{'provider':'codex','model':'host-model'}]}
        registry=[{'provider':'codex','model':'host-model','lineage':'lab-a'}]
        cat={'providers':{'codex':{'installed':True,'observed_at':self.now.isoformat(),'models':[{'model':'host-model','status':'advertised'}]}}}
        args=(aliases,cat,routes,registry,self.now.date())
        result=watch.summarize(previous,current,*args)
        self.assertEqual([r['slug'] for r in result['removed']],['gone'])
        self.assertEqual([r['slug'] for r in result['changed']],['fixture-model'])
        self.assertEqual([r['slug'] for r in result['recent']],['fixture-model'])
        self.assertEqual(result['routes'][0]['catalogue_status'],'advertised')
        self.assertTrue(result['routes'][0]['matched'])
        current['intelligence_index_version']=6
        result=watch.summarize(previous,current,*args)
        self.assertTrue(result['index_version_changed']);self.assertEqual(result['changed'],[])
        cat['providers']['codex']['observed_at']='2020-01-01T00:00:00+00:00'
        self.assertEqual(watch.summarize({},current,*args)['routes'][0]['catalogue_status'],'stale-catalogue')
        cat['providers']['codex']['observed_at']=self.now.isoformat();cat['providers']['codex']['models']=[]
        self.assertEqual(watch.summarize({},current,*args)['routes'][0]['catalogue_status'],'missing-id')
        cat['providers']['codex']['installed']=False
        self.assertEqual(watch.summarize({},current,*args)['routes'][0]['catalogue_status'],'unavailable')

    def test_command_dispatch_and_missing_key_never_print_key(self):
        args=parser().parse_args(['models','watch'])
        self.payloads=[page()]
        result=commands.execute(args,self.store,self.root)
        self.assertFalse(result['routes_changed'])
        self.assertNotIn(self.key,json.dumps(result))
        result=self.cli('models','watch',cwd=self.root,check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('AA_API_KEY',result.stderr)
        self.assertNotIn(self.key,result.stderr+result.stdout)

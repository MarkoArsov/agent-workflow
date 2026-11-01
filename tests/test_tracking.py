from tests.helpers import WorkspaceTest

class TrackingTests(WorkspaceTest):
    def api(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('plovi.tracking'), 'Tracking capability module is missing')
        from plovi import tracking
        return tracking

    def descriptor(self):
        return {'task':'fixture', 'run_id':'run-a', 'argv':['python', 'watch', 'fixture; echo unsafe'], 'cwd':str(self.root)}

    def test_open_and_run_is_verified(self):
        t=self.api(); calls=[]
        def open_tracker(d):
            calls.append(d); return {'session_id':'terminal-a','running':True}
        result=t.attach(self.descriptor(), 'open_and_run', open_tracker, self.root/'viewer.json')
        self.assertEqual(result['status'],'attached')
        self.assertEqual(calls[0]['argv'][-1], 'fixture; echo unsafe')

    def test_open_only_never_claims_running(self):
        t=self.api()
        result=t.attach(self.descriptor(),'open_only',lambda d:{'session_id':'terminal-a'}, self.root/'viewer.json')
        self.assertEqual(result['status'],'opened')
        self.assertFalse(result['running'])
        result=t.attach({**self.descriptor(),'run_id':'run-b'},'open_and_run',lambda d:{'session_id':'terminal-b'},self.root/'viewer.json')
        self.assertNotEqual(result['status'],'attached')

    def test_unavailable_host_falls_back(self):
        t=self.api()
        result=t.attach(self.descriptor(),'unavailable',None,self.root/'viewer.json')
        self.assertEqual(result['status'],'command_only')
        self.assertEqual(result['argv'],self.descriptor()['argv'])

    def test_reattach_reuses_viewer(self):
        t=self.api();calls=[]
        def opener(d): calls.append(d);return {'session_id':'terminal-a','running':True}
        for _ in range(2):t.attach(self.descriptor(),'open_and_run',opener,self.root/'viewer.json',probe=lambda session:True)
        self.assertEqual(len(calls),1)

    def test_viewer_close_preserves_worker(self):
        t=self.api()
        result=t.attach(self.descriptor(),'open_and_run',lambda d: (_ for _ in ()).throw(OSError('viewer unavailable')),self.root/'viewer.json')
        self.assertEqual(result['status'],'command_only')
        self.assertNotIn('cancel',result)

    def test_stale_viewer_is_not_claimed_running(self):
        t=self.api(); calls=[]
        def opener(d):calls.append(d);return {'session_id':'terminal-a','running':True}
        t.attach(self.descriptor(),'open_and_run',opener,self.root/'viewer.json')
        result=t.attach(self.descriptor(),'open_and_run',opener,self.root/'viewer.json')
        self.assertEqual(result['status'],'unverified')
        self.assertFalse(result['running'])
        self.assertEqual(len(calls),1)
        result=t.attach(self.descriptor(),'open_and_run',opener,self.root/'viewer.json',probe=lambda session:False)
        self.assertEqual(result['status'],'attached')
        self.assertEqual(len(calls),2)

    def test_host_bridge_uses_only_offered_capabilities(self):
        t=self.api()
        for host in ('codex','claude-cli','claude-vscode','cursor','headless'):
            with self.subTest(host=host):
                result=t.host_attach(self.descriptor(),host,self.root/(host+'.json'))
                self.assertEqual(result['status'],'command_only')
        result=t.host_attach(self.descriptor(),'codex',self.root/'codex-open.json',offered=['open_only'],
                             opener=lambda d:{'session_id':'panel'})
        self.assertEqual(result['status'],'opened')
        self.assertFalse(result['running'])

    def test_explicit_tracking_modes_do_not_open_unwanted_panels(self):
        t=self.api()
        def unexpected(d):self.fail('Tracking mode must not open a panel')
        for mode,status in [('off','disabled'),('command-only','command_only'),('current-terminal','current_terminal')]:
            result=t.attach(dict(self.descriptor(),mode=mode),'open_and_run',unexpected,self.root/(mode+'.json'))
            self.assertEqual(result['status'],status)
        result=t.attach(dict(self.descriptor(),mode='app-terminal'),'current_terminal',None,self.root/'app.json')
        self.assertEqual(result['status'],'command_only')

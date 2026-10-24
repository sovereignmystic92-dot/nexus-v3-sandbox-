from copy import deepcopy
import hashlib
import unittest
from nexus_sandbox.bound_cortex_tools import BoundCortexToolTransport,FixtureBinding
from nexus_sandbox.cortex_adapter import MARKER
from nexus_sandbox.cortex_tools import ToolFailure

ROOT='Nexus Sandbox Bound Root'
TARGET='Nexus Sandbox Bound Target'


class BoundCortexToolTests(unittest.TestCase):
    def setUp(self):
        self.data={n:{'id':'synthetic:'+n,'name':n,'version':1,'content':MARKER+' fixture',
                      'dependencies':[],'owner':'synthetic:owner','parent':None,'archived':False} for n in (ROOT,TARGET)}
        self.calls=[];self.bad_ack=False
        def invoke(tool,args):
            self.calls.append((tool,args))
            d=self.data[args['name']]
            if tool=='context_update':
                d.update(content=args['content'],dependencies=args['dependencies'],version=d['version']+1)
            result=deepcopy(d)
            if tool=='context_update' and self.bad_ack:result['id']='foreign'
            return {'structuredContent':result}
        bindings=[FixtureBinding(n,self.data[n]['id'],'synthetic:owner',None) for n in self.data]
        self.t=BoundCortexToolTransport(invoke,bindings,ROOT,1,hashlib.sha256(self.data[ROOT]['content'].encode()).hexdigest())

    def writes(self):return sum(tool=='context_update' for tool,_ in self.calls)
    def update(self):self.t.update(TARGET,MARKER+' new fixture',(ROOT,))

    def test_exact_read_and_bounded_update(self):
        self.assertEqual(self.t.get(TARGET).id,self.data[TARGET]['id'])
        self.update();self.assertEqual(self.writes(),1)
        self.assertEqual(set(self.calls[-1][1]),{'name','content','dependencies'})
    def test_wrong_root_owner_and_identity_block_before_write(self):
        for field in ('id','owner','parent'):
            old=self.data[ROOT][field];self.data[ROOT][field]='foreign'
            with self.subTest(field=field),self.assertRaises(ToolFailure):self.update()
            self.assertEqual(self.writes(),0);self.data[ROOT][field]=old
    def test_wrong_target_binding_blocks_before_write(self):
        for field in ('id','owner','parent','name'):
            old=self.data[TARGET][field];self.data[TARGET][field]='foreign'
            with self.subTest(field=field),self.assertRaises(ToolFailure):self.update()
            self.assertEqual(self.writes(),0);self.data[TARGET][field]=old
    def test_root_revision_or_marker_change_holds(self):
        self.data[ROOT]['version']=2
        with self.assertRaises(ToolFailure):self.update()
        self.data[ROOT]['version']=1;self.data[ROOT]['content']='not synthetic'
        with self.assertRaises(ToolFailure):self.update()
        self.assertEqual(self.writes(),0)
    def test_unbound_destination_dependency_and_create_make_no_calls(self):
        for operation in (lambda:self.t.get('foreign'),lambda:self.t.update('foreign',MARKER,()),
                          lambda:self.t.update(TARGET,MARKER,('foreign',)),lambda:self.t.create(TARGET,MARKER,())):
            with self.assertRaises(ToolFailure):operation()
        self.assertEqual(self.calls,[])
    def test_root_mutation_and_nonsynthetic_content_denied(self):
        for operation in (lambda:self.t.update(ROOT,MARKER,()),lambda:self.t.update(TARGET,'real data',())):
            with self.assertRaises(ToolFailure):operation()
        self.assertEqual(self.calls,[])
    def test_missing_metadata_and_archived_target_hold(self):
        del self.data[TARGET]['parent']
        with self.assertRaises(ToolFailure):self.update()
        self.data[TARGET]['parent']=None;self.data[TARGET]['archived']=True
        with self.assertRaises(ToolFailure):self.update()
        self.assertEqual(self.writes(),0)
    def test_bad_acknowledgment_does_not_trigger_repair_or_retry(self):
        self.bad_ack=True
        with self.assertRaises(ToolFailure):self.update()
        self.assertEqual(self.writes(),1)
        self.assertEqual(self.data[TARGET]['version'],2)

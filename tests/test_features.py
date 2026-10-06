import unittest
from orangejuice.features import inventory

def feature(name='欢迎新人', source='example/welcome.js', event='notice.group.increase', **extra):
    return dict(name=name,source=source,event=event,kind='notice',origin='framework',**extra)

def runtime(*items):
    return {'stale':False,'timestamp':123,'featureInventory':{'schemaVersion':1,'features':list(items),'files':[]}}

class FeaturesTest(unittest.TestCase):
    def test_default_controls_and_missing_configuration(self):
        entry=feature()
        self.assertEqual(inventory(runtime(entry))['items'][0]['defaultState'],'unknown')
        report=inventory(runtime(entry),{'default':{'disable':['欢迎新人']},'private-group':{}})
        self.assertEqual(report['items'][0]['defaultState'],'disabled')
        self.assertEqual(report['groupControl']['overrideCount'],1)
        self.assertNotIn('private-group',str(report))
        self.assertEqual(inventory(runtime(entry),{'default':{'enable':['其他功能']}})['items'][0]['defaultState'],'not-allowed')
        task=dict(entry,kind='task',scheduled=True)
        self.assertEqual(inventory(runtime(task),{'default':{'disable':['欢迎新人']}})['items'][0]['defaultState'],'not-applicable')
    def test_exact_rules_only_warn_for_overlapping_events(self):
        rule={'pattern':'^#系统$','event':'message.group','permission':'master'}
        a=feature('系统A',rules=[rule]);b=feature('系统B','ServerStatus-Plugin/index.js',rules=[dict(rule,event='message')]);c=feature('系统C',rules=[dict(rule,event='notice.group.increase')])
        report=inventory(runtime(a,b,c))
        self.assertEqual(report['duplicates'][0]['ids'],['0','1'])
        self.assertEqual(len(report['duplicates']),1)
        report=inventory(runtime(a,dict(a,source='other/b.js')))
        self.assertEqual(report['duplicates'][0]['type'],'name')
    def test_malformed_metadata_and_paths(self):
        self.assertFalse(inventory([])['available'])
        self.assertFalse(inventory({})['available'])
        report=inventory(runtime(feature(source='/opt/private'),feature(source='../config'),feature(rules=[None])))
        self.assertEqual([x['source'] for x in report['items'][:2]],['',''])
        self.assertNotIn('/opt/private',str(report))
        self.assertEqual(report['items'][2]['rules'],[])
    def test_catchall_is_labelled_without_assuming_every_feature_conflicts(self):
        report=inventory(runtime(feature('消息入口',rules=[{'pattern':'.*'}]),feature()))
        self.assertEqual(report['broadEntries'],['0'])
        self.assertEqual(report['duplicates'],[])
    def test_repeated_rules_are_deduplicated_before_overlap_comparison(self):
        rule={'pattern':'.*','event':'message'}
        report=inventory(runtime(*[feature('功能'+str(n),rules=[rule]*80) for n in range(200)]))
        self.assertEqual(len(report['duplicates']),1)
        self.assertEqual(len(report['duplicates'][0]['ids']),200)

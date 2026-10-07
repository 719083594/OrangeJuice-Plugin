import json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path


class HelpInstallTest(unittest.TestCase):
    def test_fresh_flat_bridge_includes_verified_help_resources_and_canonical_source(self):
        source=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='orangejuice-help-install-') as temporary:
            base=Path(temporary);repo=base/'source';scripts=repo/'scripts';scripts.mkdir(parents=True)
            shutil.copy2(source/'scripts/install.py',scripts/'install.py')
            # This filesystem-only installer check does not exercise psutil/YAML.
            (scripts/'yaml.py').write_text('',encoding='utf-8');(scripts/'psutil.py').write_text('',encoding='utf-8')
            (repo/'config').mkdir();(repo/'config/example.json').write_text('{}',encoding='utf-8')
            adapter=repo/'integrations/yunzai';adapter.mkdir(parents=True)
            (adapter/'index.js').write_text('public adapter fixture',encoding='utf-8')
            help_source=(source/'integrations/yunzai/help-content.mjs').read_bytes()
            (adapter/'help-content.mjs').write_bytes(help_source)
            resources=repo/'resources/help';resources.mkdir(parents=True)
            manifest={'version':1,'sources':[{'file':'integrations/yunzai/help-content.mjs'}]}
            (resources/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            (resources/'orangejuice-help-1.jpg').write_bytes(b'public jpeg fixture')
            framework=base/'framework';loader=framework/'lib/plugins/loader.js';loader.parent.mkdir(parents=True);loader.write_text('fixture',encoding='utf-8')
            command=[sys.executable,str(scripts/'install.py'),'--framework-root',str(framework),'--yunzai-bridge']
            result=subprocess.run(command,cwd=repo,text=True,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            bridge=framework/'plugins/OrangeJuice-Plugin'
            self.assertEqual((bridge/'index.js').read_text(encoding='utf-8'),'public adapter fixture')
            self.assertEqual((bridge/'help-content.mjs').read_bytes(),help_source)
            self.assertEqual((bridge/'integrations/yunzai/help-content.mjs').read_bytes(),help_source)
            self.assertEqual(json.loads((bridge/'resources/help/manifest.json').read_text(encoding='utf-8')),manifest)
            self.assertEqual((bridge/'resources/help/orangejuice-help-1.jpg').read_bytes(),b'public jpeg fixture')
            config=bridge/'config/local.json';before=config.read_bytes()
            again=subprocess.run(command,cwd=repo,text=True,capture_output=True,timeout=10)
            self.assertNotEqual(again.returncode,0)
            self.assertEqual(config.read_bytes(),before)
            self.assertEqual((bridge/'help-content.mjs').read_bytes(),help_source)


if __name__=='__main__':unittest.main()

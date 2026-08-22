from __future__ import annotations
import ast,stat,unittest
from tests.release._common import ROOT
class EntrypointTests(unittest.TestCase):
    def test_entrypoints_are_repo_relative_and_executable(self):
        for rel in ('bin/graphium','bin/graphium-selftest'):
            p=ROOT/rel; self.assertTrue(p.is_file()); self.assertTrue(p.stat().st_mode & stat.S_IXUSR)
            txt=p.read_text(encoding='utf-8'); self.assertNotIn('/home/',txt)
            t=ast.parse(txt,filename=rel); self.assertIn('__file__',[n.id for n in ast.walk(t) if isinstance(n,ast.Name)])

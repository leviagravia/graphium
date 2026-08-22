from __future__ import annotations
import ast,unittest
from tests.release._common import ROOT,imports
class ScopeBoundaryTests(unittest.TestCase):
    def test_forbidden_scope_expansion_absent(self):
        banned_imports=('requests','httpx','aiohttp','paramiko'); banned_attrs={('Gtk','Notebook'),('Gtk','Toolbar'),('Gio','FileMonitor')}; bad=[]
        for p in (ROOT/'graphium').rglob('*.py'):
            rel=p.relative_to(ROOT).as_posix(); t=ast.parse(p.read_text(encoding='utf-8'),filename=rel)
            for x in imports(rel):
                if x.startswith(banned_imports) or x.startswith('gi.repository.GtkSource'): bad.append((rel,'import',x))
            for n in ast.walk(t):
                if isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name) and (n.value.id,n.attr) in banned_attrs: bad.append((rel,'attr',f'{n.value.id}.{n.attr}'))
        self.assertEqual(bad,[])

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

from graphium.application.recent_files import MAX_RECENT_FILES, RecentFilesController
from graphium.infrastructure.recent_files_store import JsonRecentFilesStore


class MemoryStore:
    def __init__(self, initial=(), fail=False):
        self.value=tuple(initial); self.fail=fail; self.loads=0; self.saves=0
    def load(self): self.loads += 1; return self.value
    def save(self, paths):
        self.saves += 1
        if self.fail: raise OSError("simulated persistence failure")
        self.value=tuple(paths)


class G07RecentFilesTests(unittest.TestCase):
    def test_lazy_load_dedup_mru_and_cap(self):
        store=MemoryStore([f"/tmp/f{i}" for i in range(12)])
        recent=RecentFilesController(store)
        self.assertEqual(store.loads,0)
        self.assertEqual(len(recent.paths),MAX_RECENT_FILES)
        self.assertEqual(store.loads,1)
        recent.touch("/tmp/f5")
        self.assertEqual(recent.paths[0],os.path.abspath("/tmp/f5"))
        self.assertEqual(len(recent.paths),MAX_RECENT_FILES)
        self.assertEqual(len(set(recent.paths)),len(recent.paths))

    def test_unicode_logical_symlink_spelling_is_not_realpathed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); real=root/"real"; real.mkdir(); link=root/"logical"; link.symlink_to(real, target_is_directory=True)
            path=link/"café.txt"
            store=MemoryStore(); recent=RecentFilesController(store); recent.touch(str(path))
            self.assertEqual(recent.paths,(os.path.abspath(str(path)),))
            self.assertNotEqual(recent.paths[0],os.path.realpath(str(path)))

    def test_persistence_failure_does_not_publish_false_in_memory_update(self):
        store=MemoryStore(["/tmp/a"],fail=True); recent=RecentFilesController(store)
        self.assertEqual(recent.paths,("/tmp/a",))
        with self.assertRaises(OSError): recent.touch("/tmp/b")
        self.assertEqual(recent.paths,("/tmp/a",))
        with self.assertRaises(OSError): recent.clear()
        self.assertEqual(recent.paths,("/tmp/a",))

    def test_json_store_atomic_0600_roundtrip_and_no_metadata_schema(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"state"/"graphium"/"recent-files.json"
            store=JsonRecentFilesStore(path); values=("/tmp/α.txt","/tmp/b.txt")
            store.save(values)
            self.assertEqual(store.load(),values)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            payload=json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload,{"version":1,"paths":list(values)})
            self.assertEqual(set(payload),{"version","paths"})
            self.assertEqual(list(path.parent.glob(".*.tmp")),[])

    def test_missing_or_corrupt_store_is_empty_and_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"recent-files.json"; store=JsonRecentFilesStore(path)
            self.assertEqual(store.load(),()); self.assertFalse(path.exists())
            path.write_text("{broken",encoding="utf-8")
            self.assertEqual(store.load(),())

if __name__=='__main__': unittest.main()

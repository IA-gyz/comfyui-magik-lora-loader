import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

folder_paths = types.ModuleType("folder_paths")
folder_paths.get_filename_list = lambda category: []
folder_paths.get_full_path = lambda category, name: None
sys.modules["folder_paths"] = folder_paths

comfy = types.ModuleType("comfy")
comfy_sd = types.ModuleType("comfy.sd")
comfy_sd.load_lora_for_models = lambda model, clip, lora, strength_model, strength_clip: (model, clip)
comfy_utils = types.ModuleType("comfy.utils")
comfy_utils.load_torch_file = lambda path, safe_load=True: {"path": path}
comfy.sd = comfy_sd
comfy.utils = comfy_utils
sys.modules["comfy"] = comfy
sys.modules["comfy.sd"] = comfy_sd
sys.modules["comfy.utils"] = comfy_utils

sys.path.insert(0, str(REPO_ROOT))

import nodes  # noqa: E402


def _reset_folder_paths():
    folder_paths.get_filename_list = lambda category: []
    folder_paths.get_full_path = lambda category, name: None


class ApplyLoraTests(unittest.TestCase):
    def setUp(self):
        self.node = nodes.MagikLoraLoader()
        self.addCleanup(_reset_folder_paths)

    def test_clip_is_optional(self):
        result = self.node.apply_lora(
            model="MODEL", lora_name="x.safetensors",
            strength_model=1.0, strength_clip=1.0, bypass=True,
        )
        self.assertEqual(result, ("MODEL", None))

    def test_bypass_returns_inputs_unchanged(self):
        result = self.node.apply_lora(
            model="MODEL", clip="CLIP", lora_name="x.safetensors",
            strength_model=1.0, strength_clip=1.0, bypass=True,
        )
        self.assertEqual(result, ("MODEL", "CLIP"))

    def test_zero_strengths_pass_through(self):
        result = self.node.apply_lora(
            model="MODEL", clip="CLIP", lora_name="missing.safetensors",
            strength_model=0.0, strength_clip=0.0,
        )
        self.assertEqual(result, ("MODEL", "CLIP"))

    def test_missing_lora_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.node.apply_lora(
                model="MODEL", clip="CLIP", lora_name="missing.safetensors",
                strength_model=1.0, strength_clip=1.0,
            )

    def test_loads_lora_when_not_bypassed(self):
        with tempfile.TemporaryDirectory() as tmp:
            lora = Path(tmp) / "demo.safetensors"
            lora.write_bytes(b"weights")
            folder_paths.get_filename_list = lambda category: ["demo.safetensors"]
            folder_paths.get_full_path = lambda category, name: str(lora)
            result = self.node.apply_lora(
                model="MODEL", clip="CLIP", lora_name="demo.safetensors",
                strength_model=0.8, strength_clip=-0.5,
            )
            self.assertEqual(result, ("MODEL", "CLIP"))


class LibraryCacheTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(_reset_folder_paths)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.lora = root / "demo.safetensors"
        self.lora.write_bytes(b"0" * 16)
        (root / "demo.txt").write_text("trigger words", encoding="utf-8")
        folder_paths.get_filename_list = lambda category: ["demo.safetensors"]
        folder_paths.get_full_path = lambda category, name: str(self.lora)
        nodes._item_cache.clear()
        self.addCleanup(nodes._item_cache.clear)

    def test_library_item_fields(self):
        items = nodes._library_items()
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["name"], "demo.safetensors")
        self.assertEqual(item["folder"], "")
        self.assertEqual(item["size"], 16)
        self.assertFalse(item["preview"])
        self.assertEqual(item["triggers"], "trigger words")

    def test_triggers_are_cached_until_files_change(self):
        nodes._library_items()
        calls = []
        original = nodes._triggers_for

        def spy(path):
            calls.append(path)
            return original(path)

        nodes._triggers_for = spy
        try:
            nodes._library_items()
            self.assertEqual(calls, [])
            self.lora.write_bytes(b"0" * 32)
            nodes._library_items()
            self.assertEqual(len(calls), 1)
            (self.lora.parent / "demo.png").write_bytes(b"img")
            nodes._library_items()
            self.assertEqual(len(calls), 2)
        finally:
            nodes._triggers_for = original

    def test_cache_entry_removed_when_lora_disappears(self):
        nodes._library_items()
        self.assertIn("demo.safetensors", nodes._item_cache)
        os.remove(self.lora)
        items = nodes._library_items()
        self.assertEqual(items, [])
        self.assertNotIn("demo.safetensors", nodes._item_cache)


class PreviewTests(unittest.TestCase):
    def test_preview_sidecar_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lora = root / "demo.safetensors"
            lora.write_bytes(b"0")
            self.assertIsNone(nodes._preview_for(str(lora)))
            adjacent = root / "demo.png"
            adjacent.write_bytes(b"img")
            self.assertEqual(nodes._preview_for(str(lora)), str(adjacent))
            adjacent.unlink()
            prefixed = root / "demo.safetensors.preview.png"
            prefixed.write_bytes(b"img")
            self.assertEqual(nodes._preview_for(str(lora)), str(prefixed))


if __name__ == "__main__":
    unittest.main()

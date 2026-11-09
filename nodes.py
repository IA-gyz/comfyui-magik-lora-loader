import json
import os
from pathlib import Path

import folder_paths
import comfy.sd
import comfy.utils

try:
    from server import PromptServer
    from aiohttp import web
    from aiohttp.web_exceptions import HTTPNotFound, HTTPBadRequest
    _HAS_SERVER = True
except Exception:
    _HAS_SERVER = False


PREVIEW_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
TRIGGER_EXTENSIONS = (".txt", ".json", ".caption", ".trigger")


def _lora_names():
    try:
        return sorted(folder_paths.get_filename_list("loras"), key=str.casefold)
    except Exception:
        return []


def _full_lora_path(name):
    # Resolve through ComfyUI's registered LoRA paths rather than trusting a client path.
    return folder_paths.get_full_path("loras", name)


def _preview_for(lora_path):
    p = Path(lora_path)
    for ext in PREVIEW_EXTENSIONS:
        candidate = p.with_suffix(ext)
        if candidate.is_file():
            return str(candidate)
    # Some libraries use filename.preview.png
    for ext in PREVIEW_EXTENSIONS:
        candidate = Path(str(p) + ".preview" + ext)
        if candidate.is_file():
            return str(candidate)
    return None


def _triggers_for(lora_path):
    p = Path(lora_path)
    for ext in TRIGGER_EXTENSIONS:
        sidecar = p.with_suffix(ext)
        if not sidecar.is_file() or sidecar.stat().st_size > 256 * 1024:
            continue
        try:
            content = sidecar.read_text(encoding="utf-8", errors="replace").strip()
            if ext == ".json":
                data = json.loads(content)
                if isinstance(data, dict):
                    for key in ("trainedWords", "trigger_words", "triggerWords", "tags", "activation_text"):
                        value = data.get(key)
                        if isinstance(value, list):
                            return ", ".join(str(x) for x in value)
                        if isinstance(value, str) and value.strip():
                            return value.strip()
                    return ""
                if isinstance(data, list):
                    return ", ".join(str(x) for x in data)
            return content[:4000]
        except Exception:
            continue
    # Safetensors metadata is optional: don't make it a dependency.
    if p.suffix.lower() == ".safetensors":
        try:
            from safetensors import safe_open
            with safe_open(str(p), framework="pt", device="cpu") as f:
                metadata = f.metadata() or {}
            for key in ("ss_tag_frequency", "ss_trigger_words", "trigger_words", "trained_words"):
                value = metadata.get(key)
                if value:
                    if key == "ss_tag_frequency":
                        try:
                            parsed = json.loads(value)
                            tags = []
                            for bucket in parsed.values():
                                if isinstance(bucket, dict):
                                    tags.extend(bucket.keys())
                            if tags:
                                return ", ".join(tags[:80])
                        except Exception:
                            pass
                    return str(value)[:4000]
        except Exception:
            pass
    return ""


def _library_items():
    items = []
    for name in _lora_names():
        try:
            path = _full_lora_path(name)
            if not path or not os.path.isfile(path):
                continue
            stat = os.stat(path)
            rel_folder = str(Path(name).parent)
            if rel_folder == ".":
                rel_folder = ""
            preview = _preview_for(path)
            items.append({
                "name": name,
                "folder": rel_folder,
                "size": stat.st_size,
                "modified": int(stat.st_mtime),
                "preview": bool(preview),
                "triggers": _triggers_for(path),
            })
        except Exception:
            continue
    return items


if _HAS_SERVER:
    @PromptServer.instance.routes.get("/magik_lora_loader/library")
    async def magik_lora_library(request):
        return web.json_response({"loras": _library_items()})

    @PromptServer.instance.routes.get("/magik_lora_loader/preview")
    async def magik_lora_preview(request):
        name = request.query.get("name", "")
        # Only serve a preview associated with a registered LoRA entry.
        if name not in _lora_names():
            raise HTTPNotFound()
        path = _full_lora_path(name)
        if not path:
            raise HTTPNotFound()
        preview = _preview_for(path)
        if not preview or not os.path.isfile(preview):
            raise HTTPNotFound()
        return web.FileResponse(preview)


class MagikLoraLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "lora_name": (_lora_names(), {"tooltip": "Choose a LoRA from ComfyUI's registered LoRA folders."}),
                "strength_model": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "strength_clip": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "bypass": ("BOOLEAN", {"default": False, "tooltip": "Pass MODEL and CLIP through unchanged."}),
            },
            "optional": {
                "clip": ("CLIP",),
                "trigger_words": ("STRING", {"default": "", "multiline": True, "dynamicPrompts": False, "tooltip": "Optional notes only; this field does not modify the prompt."}),
            },
        }

    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("model", "clip")
    FUNCTION = "apply_lora"
    CATEGORY = "Magik/Loaders"
    DESCRIPTION = "A single-LoRA loader with bypass, library browser, preview, favorites and trigger-word helper."

    def apply_lora(self, model, clip, lora_name, strength_model, strength_clip, bypass=False, trigger_words=""):
        if bypass or (float(strength_model) == 0 and float(strength_clip) == 0):
            return (model, clip)
        path = _full_lora_path(lora_name)
        if not path or not os.path.isfile(path):
            raise FileNotFoundError(
                f"Magik LoRA Loader: LoRA '{lora_name}' was not found. Refresh the LoRA list or choose another file."
            )
        lora = comfy.utils.load_torch_file(path, safe_load=True)
        model_lora, clip_lora = comfy.sd.load_lora_for_models(
            model, clip, lora, float(strength_model), float(strength_clip)
        )
        return (model_lora, clip_lora)


NODE_CLASS_MAPPINGS = {
    "MagikLoraLoader": MagikLoraLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MagikLoraLoader": "Magik LoRA Loader",
}

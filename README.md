# Magik LoRA Loader

A single-LoRA ComfyUI custom node with a compact node UI and optional visual browser.

## Features

- Uses ComfyUI's registered `loras` folder paths and filename list.
- Separate MODEL and CLIP strengths, including negative values.
- Bypass switch; zero strengths also pass the original inputs through.
- Visual browser with search across names, folders, and trigger metadata.
- Folder filtering, preview thumbnails, favorites, file sizes, and trigger-word display.
- Preview discovery from adjacent `.png`, `.jpg`, `.jpeg`, `.webp`, or `.gif` files, including `.preview` variants.
- Reads common adjacent `.txt`, `.json`, `.caption`, and `.trigger` sidecars; optionally reads safetensors metadata when `safetensors` is installed.
- Copy trigger words into the optional `trigger_words` node field.

Favorites are stored in the browser's local storage. They are local to the browser profile and are not written into workflow files.

## Install

1. Unzip this folder into `ComfyUI/custom_nodes/` so the path is:
   `ComfyUI/custom_nodes/Magik_LoRA_Loader/`
2. Restart ComfyUI completely.
3. Refresh the browser tab (a hard refresh may be needed).
4. Add **Magik LoRA Loader** from `Magik/Loaders`.

No additional Python packages are required for core loading. Safetensors metadata reading is optional.

## Preview and trigger sidecars

For `my_lora.safetensors`, supported sidecar examples include:

- `my_lora.png`
- `my_lora.preview.jpg`
- `my_lora.txt` (trigger words or notes)
- `my_lora.json` (supports keys such as `trainedWords`, `trigger_words`, `triggerWords`, `tags`, and `activation_text`)

The preview image should sit beside the LoRA file. For LoRAs in nested folders, keep the sidecar in the same folder.

## Notes / limitations

- The node loads exactly one LoRA. Chain multiple nodes to apply multiple LoRAs.
- The `trigger_words` field is a helper/annotation only; it does not automatically inject text into a prompt.
- Favorites are browser-local. The visual browser endpoint is available only while ComfyUI is running.
- This package was statically reviewed and packaged, but not tested inside a running ComfyUI instance. ComfyUI frontend APIs can change between releases; check the terminal/browser console if your installation uses a significantly different frontend version.

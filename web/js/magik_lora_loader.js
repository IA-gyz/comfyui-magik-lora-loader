import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const EXT_ID = "Magik.LoRALoader";
const FAV_KEY = "magik_lora_loader_favorites_v1";

function getFavorites() {
    try { return new Set(JSON.parse(localStorage.getItem(FAV_KEY) || "[]")); }
    catch { return new Set(); }
}
function saveFavorites(favs) {
    try { localStorage.setItem(FAV_KEY, JSON.stringify([...favs])); } catch {}
}
function fmtSize(bytes) {
    if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}
function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, c => ({
        "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
    }[c]));
}

function makeBrowser(node) {
    const overlay = document.createElement("div");
    overlay.className = "magik-lora-overlay";
    overlay.innerHTML = `
      <style>
        .magik-lora-overlay{position:fixed;inset:0;z-index:100000;background:#090b10eF;display:flex;align-items:center;justify-content:center;font:14px system-ui;color:#e8eaf0}
        .magik-lora-panel{width:min(1120px,94vw);height:min(800px,92vh);background:#171a21;border:1px solid #3c414c;border-radius:12px;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 20px 70px #0009}
        .magik-lora-head{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid #343944}
        .magik-lora-head strong{font-size:17px}.magik-lora-head input,.magik-lora-head select{background:#252a34;color:#eee;border:1px solid #454b58;border-radius:6px;padding:8px;min-width:0}
        .magik-lora-head input{flex:1}.magik-lora-head button,.magik-lora-detail button{background:#343b49;color:#fff;border:1px solid #50596a;border-radius:6px;padding:8px 11px;cursor:pointer}
        .magik-lora-body{display:grid;grid-template-columns:minmax(0,1fr) 300px;min-height:0;flex:1}
        .magik-lora-grid{padding:12px;overflow:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(145px,1fr));gap:10px;align-content:start}
        .magik-lora-card{background:#20242d;border:1px solid #353b47;border-radius:8px;overflow:hidden;cursor:pointer;min-width:0}
        .magik-lora-card.selected{border:2px solid #72a7ff}.magik-lora-thumb{height:145px;background:#101217;display:flex;align-items:center;justify-content:center;color:#777;overflow:hidden}
        .magik-lora-thumb img{width:100%;height:100%;object-fit:cover}.magik-lora-cardname{padding:8px 8px 2px;white-space:normal;overflow-wrap:anywhere;font-size:12px}
        .magik-lora-meta{padding:3px 8px 8px;color:#9ca5b4;font-size:11px}.magik-lora-detail{padding:14px;border-left:1px solid #343944;overflow:auto}
        .magik-lora-detail h3{font-size:14px;overflow-wrap:anywhere}.magik-lora-detail .preview{width:100%;max-height:250px;object-fit:contain;background:#101217;border-radius:6px}
        .magik-lora-triggers{white-space:pre-wrap;overflow-wrap:anywhere;background:#101217;padding:9px;border-radius:6px;max-height:190px;overflow:auto;color:#c9d5e8;font-size:12px}
        .magik-lora-foot{padding:10px 14px;border-top:1px solid #343944;display:flex;gap:10px;align-items:center;color:#9ca5b4}
        .magik-lora-primary{background:#386ecb!important}.magik-lora-spacer{flex:1}
        @media(max-width:700px){.magik-lora-body{grid-template-columns:1fr}.magik-lora-detail{display:none}.magik-lora-head{flex-wrap:wrap}.magik-lora-head input{flex-basis:100%}}
      </style>
      <section class="magik-lora-panel">
        <header class="magik-lora-head">
          <strong>Magik LoRA Browser</strong>
          <input class="search" placeholder="Search name, folder, trigger words…">
          <select class="folder"><option value="">All folders</option></select>
          <select class="scope"><option value="all">All LoRAs</option><option value="favorites">★ Favorites</option><option value="preview">Has preview</option></select>
          <button class="refresh">↻</button><button class="close">✕</button>
        </header>
        <div class="magik-lora-body">
          <div class="magik-lora-grid"></div>
          <aside class="magik-lora-detail"><p>Select a LoRA to inspect it.</p></aside>
        </div>
        <footer class="magik-lora-foot"><span class="count"></span><span class="magik-lora-spacer"></span><span>Favorites are saved in this browser.</span><button class="apply magik-lora-primary" disabled>Use selected LoRA</button></footer>
      </section>`;
    document.body.appendChild(overlay);

    const $ = s => overlay.querySelector(s);
    let items = [], selected = null;
    let favorites = getFavorites();
    const currentName = () => {
        const w = node.widgets?.find(x => x.name === "lora_name");
        return w?.value || "";
    };
    function choose(item) {
        selected = item;
        renderGrid();
        renderDetail();
        $(".apply").disabled = !item;
    }
    function renderDetail() {
        const d = $(".magik-lora-detail");
        if (!selected) { d.innerHTML = "<p>Select a LoRA to inspect it.</p>"; return; }
        const img = selected.preview ? `<img class="preview" src="${api.apiURL("/magik_lora_loader/preview?name=" + encodeURIComponent(selected.name))}">` : `<div class="magik-lora-thumb">No preview found</div>`;
        const triggers = selected.triggers || "No trigger words found. You can enter them manually in the node's trigger_words field.";
        d.innerHTML = `${img}<h3>${escapeHtml(selected.name)}</h3><p>${escapeHtml(selected.folder || "Root folder")} · ${fmtSize(selected.size)}</p>
          <p><button class="favorite">${favorites.has(selected.name) ? "★ Remove favorite" : "☆ Add favorite"}</button></p>
          <h4>Trigger words / metadata</h4><div class="magik-lora-triggers">${escapeHtml(triggers)}</div>
          <p><button class="copy-trigger">Copy trigger words</button></p>`;
        d.querySelector(".favorite").onclick = () => {
            if (favorites.has(selected.name)) favorites.delete(selected.name); else favorites.add(selected.name);
            saveFavorites(favorites); renderGrid(); renderDetail();
        };
        d.querySelector(".copy-trigger").onclick = async () => {
            if (selected.triggers) {
                try { await navigator.clipboard.writeText(selected.triggers); } catch {}
                const widget = node.widgets?.find(x => x.name === "trigger_words");
                if (widget) { widget.value = selected.triggers; node.setDirtyCanvas(true, true); }
            }
        };
    }
    function renderGrid() {
        const q = $(".search").value.trim().toLowerCase();
        const folder = $(".folder").value;
        const scope = $(".scope").value;
        const visible = items.filter(x => {
            if (folder && folder !== x.folder) return false;
            if (scope === "favorites" && !favorites.has(x.name)) return false;
            if (scope === "preview" && !x.preview) return false;
            return !q || `${x.name} ${x.folder} ${x.triggers}`.toLowerCase().includes(q);
        });
        $(".count").textContent = `${visible.length} LoRA${visible.length === 1 ? "" : "s"}`;
        $(".grid")?.replaceChildren();
        const grid = $(".magik-lora-grid");
        grid.innerHTML = visible.map(x => {
            const thumb = x.preview ? `<img loading="lazy" src="${api.apiURL("/magik_lora_loader/preview?name=" + encodeURIComponent(x.name))}">` : "No preview";
            return `<article class="magik-lora-card ${selected?.name === x.name ? "selected" : ""}" data-name="${escapeHtml(x.name)}"><div class="magik-lora-thumb">${thumb}</div><div class="magik-lora-cardname">${escapeHtml(x.name)}</div><div class="magik-lora-meta">${favorites.has(x.name) ? "★ · " : ""}${fmtSize(x.size)}</div></article>`;
        }).join("");
        grid.querySelectorAll(".magik-lora-card").forEach(card => {
            card.onclick = () => choose(items.find(x => x.name === card.dataset.name));
        });
    }
    async function refresh() {
        $(".count").textContent = "Loading library…";
        try {
            const response = await api.fetchApi("/magik_lora_loader/library");
            if (!response.ok) throw new Error("Library endpoint unavailable");
            const data = await response.json();
            items = data.loras || [];
            const folders = [...new Set(items.map(x => x.folder).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
            $(".folder").innerHTML = `<option value="">All folders</option>` + folders.map(f=>`<option value="${escapeHtml(f)}">${escapeHtml(f)}</option>`).join("");
            const wanted = items.find(x => x.name === currentName());
            if (wanted) selected = wanted;
            renderGrid(); renderDetail();
        } catch (e) {
            $(".count").textContent = "Could not load library. Check ComfyUI console and restart ComfyUI.";
        }
    }
    $(".search").addEventListener("input", renderGrid);
    $(".folder").addEventListener("change", renderGrid);
    $(".scope").addEventListener("change", renderGrid);
    $(".refresh").onclick = refresh;
    $(".close").onclick = () => overlay.remove();
    overlay.addEventListener("keydown", e => { if (e.key === "Escape") overlay.remove(); });
    $(".apply").onclick = () => {
        if (!selected) return;
        const widget = node.widgets?.find(x => x.name === "lora_name");
        if (widget) {
            widget.value = selected.name;
            widget.callback?.(selected.name);
            node.setDirtyCanvas(true, true);
            app.graph.setDirtyCanvas(true, true);
        }
        overlay.remove();
    };
    overlay.addEventListener("click", e => { if (e.target === overlay) overlay.remove(); });
    refresh();
}

app.registerExtension({
    name: EXT_ID,
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "MagikLoraLoader") return;
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);
            const btn = this.addWidget("button", "Browse LoRAs…", null, () => makeBrowser(this));
            btn.serialize = false;
            this.addWidget("button", "Refresh LoRA list", null, async () => {
                try {
                    await api.fetchApi("/magik_lora_loader/library");
                    const widget = this.widgets?.find(w => w.name === "lora_name");
                    if (widget) {
                        const response = await api.fetchApi("/object_info/MagikLoraLoader");
                        const info = await response.json();
                        const values = info?.MagikLoraLoader?.input?.required?.lora_name?.[0];
                        if (Array.isArray(values)) widget.options.values = values;
                    }
                    this.setDirtyCanvas(true, true);
                } catch (e) { console.warn("[Magik LoRA Loader] refresh failed", e); }
            }).serialize = false;
        };
    }
});

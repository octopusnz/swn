# Campaign Compendium Dashboard

```dataviewjs
const linkPath = (v) => {
  if (!v) return null;
  if (Array.isArray(v)) v = v[0];
  return v.path || null;
};
const linkName = (v) => {
  const p = linkPath(v);
  return p ? p.split("/").pop().replace(/\.md$/, "") : null;
};
const openSearch = (query) => {
  try {
    app.internalPlugins.getPluginById("global-search").instance.openGlobalSearch(query);
  } catch (e) {
    // global search API unavailable; card is decorative in that case
  }
};
const internalLink = (parent, text, path, cls = "internal-link") => {
  const a = parent.createEl("a", { cls, text, href: path });
  a.dataset.href = path;
  return a;
};

const systems = dv.pages('"Systems"');
const worlds = dv.pages('"Worlds"');
const npcs = dv.pages('"NPCs"');
const ships = dv.pages('"Ships"');

// ---------------------------------------------------------------------
// BANNER: Campaign hero image
// ---------------------------------------------------------------------
const bannerFile = app.vault.getAbstractFileByPath("galaxy.png");
if (bannerFile) {
  const banner = dv.container.createEl("div", { cls: "swn-dashboard-banner" });
  banner.createEl("img", {
    cls: "swn-dashboard-banner-img",
    attr: { src: app.vault.getResourcePath(bannerFile), alt: "" },
  });
}

const root = dv.container.createEl("div", { cls: "swn-dashboard-layout" });
const main = root.createEl("div", { cls: "swn-dashboard-main" });
const side = root.createEl("div", { cls: "swn-dashboard-side" });

// ---------------------------------------------------------------------
// MAIN: Campaign Overview
// ---------------------------------------------------------------------
main.createEl("div", { cls: "swn-section-title", text: "Campaign Overview" });
const overviewGrid = main.createEl("div", { cls: "swn-dashboard-grid" });
for (const [label, count, folder] of [
  ["Systems", systems.length, "Systems"],
  ["Worlds", worlds.length, "Worlds"],
  ["NPCs", npcs.length, "NPCs"],
  ["Ships", ships.length, "Ships"],
]) {
  const card = overviewGrid.createEl("div", { cls: "swn-dashboard-card" });
  card.createEl("div", { cls: "swn-card-count", text: String(count) });
  card.createEl("div", { cls: "swn-card-label", text: label });
  card.onclick = () => openSearch(`path:"${folder}"`);
}

// ---------------------------------------------------------------------
// MAIN: Campaign Map — Systems -> Worlds/Ships -> NPCs
// ---------------------------------------------------------------------
main.createEl("div", { cls: "swn-section-title", text: "Campaign Map" });
if (systems.length === 0) {
  main.createEl("div", { cls: "swn-card-label", text: "No systems recorded yet." });
}
for (const sys of systems) {
  const sysWorlds = worlds.where((w) => linkPath(w.system) === sys.file.path);
  const sysShips = ships.where((s) => linkPath(s.current_location) === sys.file.path);

  const card = main.createEl("div", { cls: "swn-map-system" });
  const title = card.createEl("div", { cls: "swn-map-system-title" });
  internalLink(title, sys.file.name, sys.file.path);
  if (sys.tags && sys.tags.length) {
    const chipRow = card.createEl("div", { cls: "swn-chip-row" });
    for (const t of sys.tags) chipRow.createEl("span", { cls: "swn-chip", text: t });
  }

  if (sysWorlds.length) {
    card.createEl("div", { cls: "swn-map-branch-label", text: "Worlds" });
    for (const w of sysWorlds) {
      const node = card.createEl("div", { cls: "swn-map-node" });
      internalLink(node, w.file.name, w.file.path);
      if (w.population) node.createSpan({ cls: "swn-card-label", text: ` — ${w.population}` });

      const wNpcs = npcs.where((n) => n.location_type === "world" && linkPath(n.location) === w.file.path);
      if (wNpcs.length) {
        const chipRow = card.createEl("div", { cls: "swn-chip-row" });
        for (const n of wNpcs) internalLink(chipRow, n.file.name, n.file.path, "internal-link swn-chip");
      }
    }
  }

  if (sysShips.length) {
    card.createEl("div", { cls: "swn-map-branch-label", text: "Ships in system" });
    for (const s of sysShips) {
      const node = card.createEl("div", { cls: "swn-map-node" });
      internalLink(node, s.file.name, s.file.path);
      const hull = linkName(s.hull_type);
      if (hull) node.createSpan({ cls: "swn-card-label", text: ` — ${hull}` });

      const crew = npcs.where((n) => n.location_type === "ship" && linkPath(n.location) === s.file.path);
      if (crew.length) {
        const chipRow = card.createEl("div", { cls: "swn-chip-row" });
        for (const n of crew) internalLink(chipRow, n.file.name, n.file.path, "internal-link swn-chip");
      }
    }
  }
}

// Flag entries that aren't linked into the map yet, so nothing gets lost
const unlinked = [
  ...worlds.where((w) => !linkPath(w.system)).map((w) => [w, "missing system"]),
  ...ships.where((s) => !linkPath(s.current_location)).map((s) => [s, "missing current_location"]),
  ...npcs.where((n) => !linkPath(n.location)).map((n) => [n, "missing location"]),
];
if (unlinked.length) {
  main.createEl("div", { cls: "swn-section-title", text: "Unlinked Entries" });
  const list = main.createEl("div", { cls: "swn-recent-list" });
  for (const [p, reason] of unlinked) {
    const row = list.createEl("div", { cls: "swn-recent-row" });
    internalLink(row, p.file.name, p.file.path, "internal-link swn-recent-link");
    row.createEl("span", { cls: "swn-recent-date", text: reason });
  }
}

// ---------------------------------------------------------------------
// MAIN: Factions
// ---------------------------------------------------------------------
main.createEl("div", { cls: "swn-section-title", text: "Factions" });
const factionMap = new Map();
const addToFaction = (fac, page) => {
  if (!fac) return;
  const name = typeof fac === "string" ? fac : linkName(fac) || String(fac);
  if (!factionMap.has(name)) factionMap.set(name, []);
  factionMap.get(name).push(page);
};
for (const n of npcs) addToFaction(n.faction, n);
for (const s of ships) addToFaction(s.owner_faction, s);

if (factionMap.size === 0) {
  main.createEl("div", { cls: "swn-card-label", text: "No factions recorded yet." });
} else {
  for (const [name, members] of [...factionMap.entries()].sort((a, b) => b[1].length - a[1].length)) {
    const card = main.createEl("div", { cls: "swn-faction-card" });
    card.createEl("div", { cls: "swn-faction-name", text: name });
    const chipRow = card.createEl("div", { cls: "swn-chip-row" });
    for (const m of members) internalLink(chipRow, m.file.name, m.file.path, "internal-link swn-chip");
  }
}

// ---------------------------------------------------------------------
// MAIN: Open Threads — Hooks & Secrets pulled from every campaign page
// ---------------------------------------------------------------------
main.createEl("div", { cls: "swn-section-title", text: "Open Threads" });
const threadRows = [];
for (const p of [...systems, ...worlds, ...npcs, ...ships]) {
  const items = p.file.lists.where((l) => l.section?.subpath === "Hooks & Secrets" && l.text?.trim().length);
  for (const item of items) threadRows.push({ page: p, text: item.text });
}

if (threadRows.length === 0) {
  main.createEl("div", { cls: "swn-card-label", text: "No open threads recorded yet." });
} else {
  const list = main.createEl("div", { cls: "swn-recent-list" });
  for (const { page, text } of threadRows) {
    const row = list.createEl("div", { cls: "swn-thread-row" });
    internalLink(row, page.file.name, page.file.path, "internal-link swn-thread-source");
    row.createEl("span", { text });
  }
}

// ---------------------------------------------------------------------
// MAIN: Recently Edited (campaign data only)
// ---------------------------------------------------------------------
main.createEl("div", { cls: "swn-section-title", text: "Recently Edited" });
const recent = dv.pages('"Systems" or "Worlds" or "NPCs" or "Ships"')
  .sort((p) => p.file.mtime, "desc")
  .limit(8);
const recentList = main.createEl("div", { cls: "swn-recent-list" });
for (const p of recent) {
  const row = recentList.createEl("div", { cls: "swn-recent-row" });
  internalLink(row, p.file.name, p.file.path, "internal-link swn-recent-link");
  row.createEl("span", { cls: "swn-recent-date", text: p.file.mtime.toFormat("yyyy-MM-dd") });
}

// ---------------------------------------------------------------------
// SIDE PANEL: Rules Compendium (reference material, kept out of the way)
// ---------------------------------------------------------------------
side.createEl("div", { cls: "swn-side-title", text: "Rules Compendium" });
const compendiumRoot = "Compendium";
const compendiumPages = dv.pages(`"${compendiumRoot}"`);
side.createEl("div", { cls: "swn-card-label", text: `${compendiumPages.length} reference entries` });

const byCategory = {};
for (const p of compendiumPages) {
  const rel = p.file.folder.slice(compendiumRoot.length).replace(/^\//, "");
  const category = rel === "" ? "(uncategorized)" : rel.split("/")[0];
  byCategory[category] = (byCategory[category] || 0) + 1;
}
const sideGrid = side.createEl("div", { cls: "swn-side-grid" });
for (const [category, count] of Object.entries(byCategory).sort((a, b) => b[1] - a[1])) {
  const card = sideGrid.createEl("div", { cls: "swn-side-card" });
  card.createEl("div", { cls: "swn-card-count", text: String(count) });
  card.createEl("div", { cls: "swn-card-label", text: category });
  card.onclick = () => openSearch(`path:"${compendiumRoot}/${category}"`);
}

side.createEl("div", { cls: "swn-side-title", text: "Quick Links" });
const quickLinks = side.createEl("div", { cls: "swn-recent-list" });
for (const [text, path] of [
  ["SWN Compendium Index", "Compendium/SWN Compendium Index.md"],
  ["System Template", "z_templates/System Template.md"],
  ["World Template", "z_templates/World Template.md"],
  ["NPC Template", "z_templates/NPC Template.md"],
  ["Ship Template", "z_templates/Ship Template.md"],
]) {
  const row = quickLinks.createEl("div", { cls: "swn-recent-row" });
  internalLink(row, text, path, "internal-link swn-recent-link");
}
```

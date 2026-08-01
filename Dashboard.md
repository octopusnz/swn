# Campaign Compendium Dashboard

```dataviewjs
const all = dv.pages('""')
  .where(p => !p.file.path.startsWith("z_templates/") && p.file.name !== "Dashboard");

dv.container.createEl("div", {
  cls: "swn-total-stat",
  text: `${all.length} documents in campaign`
});
```

## Compendium by category

```dataviewjs
const root = "Compendium";
const pages = dv.pages(`"${root}"`);

const byCategory = {};
for (const p of pages) {
  const rel = p.file.folder.slice(root.length).replace(/^\//, "");
  const category = rel === "" ? "(uncategorized)" : rel.split("/")[0];
  byCategory[category] = (byCategory[category] || 0) + 1;
}

const rows = Object.entries(byCategory).sort((a, b) => b[1] - a[1]);

const grid = dv.container.createEl("div", { cls: "swn-dashboard-grid" });
for (const [category, count] of rows) {
  const card = grid.createEl("div", { cls: "swn-dashboard-card" });
  card.createEl("div", { cls: "swn-card-count", text: String(count) });
  card.createEl("div", { cls: "swn-card-label", text: category });

  card.onclick = () => {
    try {
      app.internalPlugins.getPluginById("global-search").instance.openGlobalSearch(`path:"${root}/${category}"`);
    } catch (e) {
      // global search API unavailable; card is decorative in that case
    }
  };
}
```

## Other areas

```dataviewjs
const folders = ["Systems", "z_templates"];

const grid = dv.container.createEl("div", { cls: "swn-dashboard-grid" });
for (const f of folders) {
  const count = dv.pages(`"${f}"`).length;
  const card = grid.createEl("div", { cls: "swn-dashboard-card" });
  card.createEl("div", { cls: "swn-card-count", text: String(count) });
  card.createEl("div", { cls: "swn-card-label", text: f });

  card.onclick = () => {
    try {
      app.internalPlugins.getPluginById("global-search").instance.openGlobalSearch(`path:"${f}"`);
    } catch (e) {
      // global search API unavailable; card is decorative in that case
    }
  };
}
```

## Recently edited

```dataviewjs
const recent = dv.pages('""')
  .where(p => p.file.name !== "Dashboard")
  .sort(p => p.file.mtime, "desc")
  .limit(10);

const list = dv.container.createEl("div", { cls: "swn-recent-list" });
for (const p of recent) {
  const row = list.createEl("div", { cls: "swn-recent-row" });
  const link = row.createEl("a", {
    cls: "internal-link swn-recent-link",
    text: p.file.name,
    href: p.file.path,
  });
  link.dataset.href = p.file.path;
  row.createEl("span", { cls: "swn-recent-date", text: p.file.mtime.toFormat("yyyy-MM-dd") });
}
```

## Quick links

- [[Compendium/SWN Compendium Index|SWN Compendium Index]]
- [[Main Index]]

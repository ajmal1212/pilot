# Plugin Frontend

A plugin's backend (`pilot/plugins/<slug>/`) can ship a frontend too, loaded into the Admin UI at runtime with no changes to core frontend source.

## Contract

A plugin with a frontend adds this layout under its own directory:

```text
frontend/
  dist/
    index.js    required - an ES module exporting init(registry)
```

`PluginManager.list_plugin_info()` reports `has_frontend: true` when `frontend/dist/index.js` exists. The Admin UI's `initializePlugins()` (`admin/frontend/src/plugins/index.js`) then, once the admin session is authenticated:

1. Dynamically imports `index.js` from `/api/v1/plugins/<slug>/assets/index.js` (served by `admin/backend/api/v1/plugins_api.py`, for both bundled and installed plugins).
2. Calls the module's exported `init(registry)`.

`init` registers UI into the same registry core sections use:

```js
export function init(registry) {
  registry.registerSettingsSection({
    id: 'my-plugin',
    label: 'My Plugin',
    icon: 'lucide-plug',
    component: MySettingsComponent,
  })
}
```

See `admin/frontend/src/plugins/registry.js` for the full registry API.

## Shared runtime, not a bundled copy

`index.js` should `import` from `vue`, `vue-router`, and `frappe-ui` like any other component in this codebase - do not bundle them. In the built Admin UI, those three specifiers resolve through the import map in `index.html` to `plugin-runtime/vendor.js`, a chunk built independently by `vite.vendor.config.js` (see `admin/frontend/package.json`'s `build` script). This is what lets a plugin's UI look and behave exactly like core's: it runs on the literal same Vue instance, not a second copy, and can use frappe-ui components (`Button`, `FormControl`, `Dialog`, `toast`, ...) the same way core does.

A plugin author builds `frontend/dist/` with their own small Vite project, marking `vue`, `vue-router`, and `frappe-ui` as external so the build doesn't inline them - only resolve them as bare imports.

## Don't ship your own Tailwind CSS build

There is deliberately no `index.css` in the loaded contract. Style with frappe-ui components and Tailwind utility classes exactly as core does - since your component mounts into the same page, whatever core's own build already generates (which is most of the common utility vocabulary, since both use the same `frappe-ui/tailwind` preset) is already available for free, no import needed.

Do **not** run your own `@tailwind utilities`/`base`/`components` build and load it as a second stylesheet. Tailwind's utility classes are global and unscoped (`.hidden`, `.sm\:flex`, etc.), and Tailwind relies on *source order within one stylesheet* to make responsive variants win over their base counterparts. A second, independently-built stylesheet loaded after core's breaks that guarantee for the *whole page*: whichever stylesheet happens to define a given class last wins the cascade, not whichever one is "correct" for the current viewport. This was tried and measured directly - a plugin's own Tailwind build made every `sm:`/`md:`/`lg:` responsive class across all of core's UI (not just the plugin's own markup) stop responding to viewport width, because the plugin's unconditional `.hidden` rule loaded after core's viewport-gated `.sm\:flex` rule.

If a plugin genuinely needs bespoke visual styling frappe-ui components and Pilot's existing utility classes can't express, that needs a deliberately scoped approach (e.g. hand-written CSS under a single wrapper class unique to the plugin, never a generated utility build) - treat it as an exception to design carefully, not the default.

## Limits

- This only works against a built Admin UI (`npm run build`), not `vite dev` - the dev server resolves those specifiers itself, so a plugin bundle has nothing valid to import against.

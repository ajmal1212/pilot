# Plugin Frontend

A plugin's backend (`pilot/plugins/<slug>/`) can ship a frontend too, loaded into the Admin UI at runtime with no changes to core frontend source.

## Contract

A plugin with a frontend adds this layout under its own directory:

```text
frontend/
  dist/
    index.js    required - an ES module exporting init(registry)
    index.css   optional
```

`PluginManager.list_plugin_info()` reports `has_frontend: true` when `frontend/dist/index.js` exists. The Admin UI's `initializePlugins()` (`admin/frontend/src/plugins/index.js`) then, once the admin session is authenticated:

1. Links `index.css` if present.
2. Dynamically imports `index.js` from `/api/v1/plugins/<slug>/assets/index.js` (served by `admin/backend/api/v1/plugins_api.py`, for both bundled and installed plugins).
3. Calls the module's exported `init(registry)`.

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

## Limits

- This only works against a built Admin UI (`npm run build`), not `vite dev` - the dev server resolves those specifiers itself, so a plugin bundle has nothing valid to import against.
- `index.css` should be compiled with the same `frappe-ui/tailwind` preset core uses (`admin/frontend/tailwind.config.js`) so colors and spacing match.

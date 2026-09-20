import { build } from 'esbuild'

// `npm run build` typechecks first (see package.json). esbuild only strips types, so a
// stray backtick inside the CSS template literals in style.ts / shell-style.ts closes
// the string early and bundles cleanly — and then the whole plugin fails to load with
// an undefined identifier from the middle of a CSS rule. tsc catches that; esbuild will
// not. The bundle is served to the browser by dsh web, so it must be rebuilt before any
// browser check: dsh serves plugins/dist/client.js, never the TS source.

// DSH's native closure-factory protocol. React is the host's singleton instance.
await build({
  entryPoints: ['src/client/index.tsx'], outfile: 'dist/client.js', bundle: true,
  platform: 'browser', format: 'cjs', target: 'es2022', jsx: 'automatic',
  external: ['react', 'react/jsx-runtime'],
  banner: { js: 'window.__ModuleLoader__.load({id:"bridgeflow-plugins",factory:(require)=>{var module={exports:{}};var exports=module.exports;' },
  footer: { js: 'return module.exports;}});' },
})

import { build } from 'esbuild'

// DSH's native closure-factory protocol. React is the host's singleton instance.
await build({
  entryPoints: ['src/client/index.tsx'], outfile: 'dist/client.js', bundle: true,
  platform: 'browser', format: 'cjs', target: 'es2022', jsx: 'automatic',
  external: ['react', 'react/jsx-runtime'],
  banner: { js: 'window.__ModuleLoader__.load({id:"bridgeflow-plugins",factory:(require)=>{var module={exports:{}};var exports=module.exports;' },
  footer: { js: 'return module.exports;}});' },
})

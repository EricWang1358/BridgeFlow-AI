import { useEffect, useState, useSyncExternalStore } from 'react'
import type { Context } from '@deepseek-ai/cordis'
import { useUI } from './ui.ts'

const frame = () => document.querySelector('[data-slot="root"] > div')
const sidebarOpen = () => Boolean(frame() && !frame()?.hasAttribute('data-sidebar-collapsed'))
function subscribeSidebar(update: () => void) {
  const node = frame()
  if (!node) return () => {}
  const observer = new MutationObserver(update)
  observer.observe(node,{attributes:true,attributeFilter:['data-sidebar-collapsed']})
  return () => observer.disconnect()
}

/** The public frame attribute is the rendered native state, including narrow-screen concessions. */
export function useNativeSidebar(ctx: Context) {
  const open = useSyncExternalStore(subscribeSidebar, sidebarOpen)
  useEffect(() => { if (sidebarOpen()) ctx.layout.toggleSidebar() }, [ctx])
  return {open,toggle:()=>ctx.layout.toggleSidebar(),close:()=>{if(sidebarOpen())ctx.layout.toggleSidebar()}}
}

type Widths = { left: number; right: number }
function initialWidths(): Widths {
  try {
    const value=JSON.parse(localStorage.getItem('bridgeflow.panel-widths') ?? 'null')
    if (Number.isFinite(value?.left) && Number.isFinite(value?.right)) return value
  } catch { /* Invalid or unavailable preferences use the viewport default. */ }
  return {left:window.innerWidth*.25,right:window.innerWidth*.26}
}
function fit(value:Widths, viewport:number):Widths {
  const available=Math.max(480,viewport-444)
  const left=Math.max(220,Math.min(value.left,available-260))
  return {left,right:Math.max(260,Math.min(value.right,available-left))}
}

export function PanelResizers({hiddenSources,hiddenStudio}:{hiddenSources:boolean;hiddenStudio:boolean}) {
  const {t}=useUI(), [widths,setWidths]=useState(initialWidths), [viewport,setViewport]=useState(window.innerWidth)
  const actual=fit(widths,viewport)
  useEffect(()=>{const resize=()=>setViewport(window.innerWidth);window.addEventListener('resize',resize);return()=>window.removeEventListener('resize',resize)},[])
  useEffect(()=>{
    if(viewport>1100){document.body.style.setProperty('--bf-shell-left',`${actual.left}px`);document.body.style.setProperty('--bf-shell-right',`${actual.right}px`)}
    else {document.body.style.removeProperty('--bf-shell-left');document.body.style.removeProperty('--bf-shell-right')}
    return()=>{document.body.style.removeProperty('--bf-shell-left');document.body.style.removeProperty('--bf-shell-right')}
  },[actual.left,actual.right,viewport])
  function update(side:'left'|'right',value:number) {
    const other=side==='left'?(hiddenStudio?0:actual.right):(hiddenSources?0:actual.left)
    const minimum=side==='left'?220:260
    const maximum=Math.max(minimum,viewport-444-other)
    setWidths(previous=>{const next={...previous,[side]:Math.round(Math.max(minimum,Math.min(value,maximum)))};try{localStorage.setItem('bridgeflow.panel-widths',JSON.stringify(next))}catch{}return next})
  }
  if(viewport<=1100)return null
  return <>{(['left','right'] as const).map(side=>(side==='left'?hiddenSources:hiddenStudio)?null:<div key={side} role="separator" tabIndex={0} aria-orientation="vertical" aria-label={t(side==='left'?'resizeSources':'resizeStudio')} aria-valuemin={side==='left'?220:260} aria-valuemax={Math.max(side==='left'?220:260,viewport-444-(side==='left'?(hiddenStudio?0:actual.right):(hiddenSources?0:actual.left)))} aria-valuenow={Math.round(actual[side])} className={`bf-panel-resizer bf-panel-resizer-${side}`}
    onDoubleClick={()=>update(side,viewport*(side==='left'?.25:.26))}
    onKeyDown={event=>{if(['ArrowLeft','ArrowRight','Home'].includes(event.key)){event.preventDefault();update(side,event.key==='Home'?(side==='left'?220:260):actual[side]+(event.key==='ArrowRight'?1:-1)*(side==='left'?1:-1)*20)}}}
    onPointerDown={event=>{event.currentTarget.setPointerCapture(event.pointerId);event.preventDefault()}}
    onPointerMove={event=>{if(event.currentTarget.hasPointerCapture(event.pointerId))update(side,side==='left'?event.clientX-18:viewport-event.clientX-18)}}
    onPointerUp={event=>{if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId)}}
  />)}</>
}

// Instalar SupplySense como app y usarlo sin conexión. Todo es local: el service worker guarda
// en este navegador lo que ya se consultó; no hay cuentas, avisos ni servicios externos.
import { useEffect, useState } from 'react'

const INSTALLABLE = 'supplysense:instalable'
let installPrompt = null

export function registerServiceWorker() {
  if (typeof window === 'undefined') return
  // El navegador ofrece instalar la app; se guarda la oferta para mostrar un botón propio.
  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault()
    installPrompt = event
    window.dispatchEvent(new Event(INSTALLABLE))
  })
  window.addEventListener('appinstalled', () => {
    installPrompt = null
    window.dispatchEvent(new Event(INSTALLABLE))
  })
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return
  window.addEventListener('load', () => {
    navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`, { scope: import.meta.env.BASE_URL })
      .catch(() => { /* sin service worker el sitio funciona igual, solo que no sin conexión */ })
  })
}

export function useOnline() {
  const [online, setOnline] = useState(() => (typeof navigator === 'undefined' ? true : navigator.onLine))
  useEffect(() => {
    const on = () => setOnline(true)
    const off = () => setOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => {
      window.removeEventListener('online', on)
      window.removeEventListener('offline', off)
    }
  }, [])
  return online
}

/** { canInstall, install }: el botón solo aparece donde el navegador permite instalar. */
export function useInstall() {
  const [canInstall, setCanInstall] = useState(Boolean(installPrompt))
  useEffect(() => {
    const sync = () => setCanInstall(Boolean(installPrompt))
    window.addEventListener(INSTALLABLE, sync)
    return () => window.removeEventListener(INSTALLABLE, sync)
  }, [])
  const install = async () => {
    if (!installPrompt) return
    installPrompt.prompt()
    await installPrompt.userChoice.catch(() => null)
    installPrompt = null
    setCanInstall(false)
  }
  return { canInstall, install }
}

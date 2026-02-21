import { format, formatDistanceToNow, parseISO } from 'date-fns'
import { es } from 'date-fns/locale'

/**
 * Formatear moneda MXN
 */
export function formatMoney(amount) {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
    minimumFractionDigits: 2,
  }).format(amount || 0)
}

/**
 * Formatear fecha: "17 Feb 2026"
 */
export function formatDate(dateStr) {
  if (!dateStr) return '—'
  const date = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr
  return format(date, "d MMM yyyy", { locale: es })
}

/**
 * Formatear fecha y hora: "17 Feb 2026 14:30"
 */
export function formatDateTime(dateStr) {
  if (!dateStr) return '—'
  const date = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr
  return format(date, "d MMM yyyy HH:mm", { locale: es })
}

/**
 * Tiempo relativo: "hace 5 minutos"
 */
export function formatRelativeTime(dateStr) {
  if (!dateStr) return '—'
  const date = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr
  return formatDistanceToNow(date, { addSuffix: true, locale: es })
}

/**
 * Formatear velocidad: "50 Mbps"
 */
export function formatSpeed(mbps) {
  if (!mbps && mbps !== 0) return '—'
  return `${mbps} Mbps`
}

/**
 * Formatear MAC address: aa:bb:cc:dd:ee:ff
 */
export function formatMAC(mac) {
  if (!mac) return '—'
  return mac.toLowerCase().replace(/[^a-f0-9]/g, '').match(/.{2}/g)?.join(':') || mac
}

/**
 * Truncar texto
 */
export function truncate(str, maxLength = 50) {
  if (!str) return ''
  return str.length > maxLength ? str.substring(0, maxLength) + '...' : str
}

/**
 * Status labels para conexiones
 */
export const connectionStatusLabels = {
  active: { label: 'Activo', variant: 'success' },
  suspended: { label: 'Suspendido', variant: 'warning' },
  cancelled: { label: 'Cancelado', variant: 'danger' },
}

/**
 * Status labels para tickets
 */
export const ticketStatusLabels = {
  abierto: { label: 'Abierto', variant: 'info' },
  en_proceso: { label: 'En proceso', variant: 'warning' },
  esperando_cliente: { label: 'Esperando cliente', variant: 'orange' },
  resuelto: { label: 'Resuelto', variant: 'success' },
  cerrado: { label: 'Cerrado', variant: 'default' },
  cancelado: { label: 'Cancelado', variant: 'danger' },
}

/**
 * Priority labels para tickets
 */
export const ticketPriorityLabels = {
  baja: { label: 'Baja', variant: 'default' },
  media: { label: 'Media', variant: 'info' },
  alta: { label: 'Alta', variant: 'warning' },
  urgente: { label: 'Urgente', variant: 'danger' },
}

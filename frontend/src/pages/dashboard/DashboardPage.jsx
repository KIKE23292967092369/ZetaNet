import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { StatCard } from '../../components/ui'
import api from '../../api/axios'
import {
  Users, UserPlus, Wifi, WifiOff, CalendarCheck, CalendarPlus,
  RotateCcw, Ticket, Tag, Box, Router, Cpu,
  ClipboardList, MessageCircle, DollarSign, AlertTriangle,
  Receipt, Loader2,
} from 'lucide-react'

export default function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const { data } = await api.get('/dashboard/stats')
        setStats(data)
      } catch (err) {
        console.error('Error cargando dashboard:', err)
        setError('No se pudieron cargar las métricas')
      } finally {
        setLoading(false)
      }
    }
    fetchStats()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
        <span className="ml-2 text-gray-500">Cargando métricas...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-600">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-3 text-sm text-brand-600 hover:underline"
        >
          Reintentar
        </button>
      </div>
    )
  }

  const s = stats || {}

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Bienvenido, {user?.name} — {user?.tenant_name}
        </p>
      </div>

      {/* Fila 1: Instalaciones y Clientes */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <StatCard
          title={`Instalaciones ${s.prev_month_name || ''} ${s.prev_year || ''}`}
          icon={CalendarCheck}
          value={s.instalaciones_mes_anterior ?? 0}
          color="blue"
          onClick={() => navigate('/conexiones')}
        />
        <StatCard
          title={`Instalaciones ${s.current_month_name || ''} ${s.current_year || ''}`}
          icon={CalendarPlus}
          value={s.instalaciones_mes_actual ?? 0}
          color="blue"
          onClick={() => navigate('/conexiones')}
        />
        <StatCard
          title={`Clientes ${s.prev_month_name || ''} ${s.prev_year || ''}`}
          icon={Users}
          value={s.clientes_mes_anterior ?? 0}
          color="green"
          onClick={() => navigate('/clientes')}
        />
        <StatCard
          title={`Clientes ${s.current_month_name || ''} ${s.current_year || ''}`}
          icon={UserPlus}
          value={s.clientes_mes_actual ?? 0}
          color="green"
          onClick={() => navigate('/clientes')}
        />
      </div>

      {/* Fila 2: Tickets */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <StatCard
          title="Resolución Tickets Instalación"
          subtitle="Promedio"
          icon={RotateCcw}
          value={`${s.resolucion_instalacion_dias ?? 0} días`}
          color="orange"
          onClick={() => navigate('/tickets')}
        />
        <StatCard
          title="Resolución Otros Tickets"
          subtitle="Promedio"
          icon={RotateCcw}
          value={`${s.resolucion_otros_dias ?? 0} días`}
          color="orange"
          onClick={() => navigate('/tickets')}
        />
        <StatCard
          title="Tickets instalación"
          subtitle="Pendientes"
          icon={Tag}
          value={s.tickets_instalacion_pendientes ?? 0}
          color="red"
          onClick={() => navigate('/tickets')}
        />
        <StatCard
          title="Tickets de cobranza"
          subtitle="Pendientes"
          icon={Receipt}
          value={s.tickets_cobranza_pendientes ?? 0}
          color="red"
          onClick={() => navigate('/tickets')}
        />
      </div>

      {/* Fila 3: Inventario y Eventos */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <StatCard
          title="Tickets de evento"
          subtitle="Pendientes"
          icon={ClipboardList}
          value={s.tickets_evento_pendientes ?? 0}
          color="red"
          onClick={() => navigate('/tickets')}
        />
        <StatCard
          title="CPEs disponibles"
          icon={Box}
          value={s.cpes_disponibles ?? 0}
          color="cyan"
          onClick={() => navigate('/inventario')}
        />
        <StatCard
          title="Routers disponibles"
          icon={Router}
          value={s.routers_disponibles ?? 0}
          color="cyan"
          onClick={() => navigate('/inventario')}
        />
        <StatCard
          title="ONUs disponibles"
          icon={Cpu}
          value={s.onus_disponibles ?? 0}
          color="cyan"
          onClick={() => navigate('/inventario')}
        />
      </div>

      {/* Fila 4: Prospectos + extras */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <StatCard
          title="Prospectos"
          subtitle="En seguimiento"
          icon={UserPlus}
          value={s.prospectos_seguimiento ?? 0}
          color="purple"
          onClick={() => navigate('/prospectos')}
        />
        <StatCard
          title="Clientes activos"
          icon={Users}
          value={s.clientes_activos ?? 0}
          color="green"
          onClick={() => navigate('/clientes')}
        />
        <StatCard
          title="Clientes suspendidos"
          icon={WifiOff}
          value={s.clientes_suspendidos ?? 0}
          color="orange"
          onClick={() => navigate('/clientes')}
        />
        <StatCard
          title="Ingresos del mes"
          icon={DollarSign}
          value={`$${(s.ingresos_mes ?? 0).toLocaleString()}`}
          color="green"
          onClick={() => navigate('/facturacion')}
        />
      </div>

      {/* Fila 5: Conexiones, mensajes, morosos */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Conexiones activas"
          icon={Wifi}
          value={s.conexiones_activas ?? 0}
          color="blue"
          onClick={() => navigate('/conexiones')}
        />
        <StatCard
          title="WhatsApp sin leer"
          icon={MessageCircle}
          value={s.mensajes_sin_leer ?? 0}
          color="green"
          onClick={() => navigate('/whatsapp')}
        />
        <StatCard
          title="Clientes morosos"
          icon={AlertTriangle}
          value={s.clientes_morosos ?? 0}
          color="red"
          onClick={() => navigate('/facturacion')}
        />
      </div>
    </div>
  )
}
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../../api/axios'
import {
  ArrowLeft, Loader2, AlertTriangle, UserCheck, MessageSquarePlus,
  Phone, Mail, MapPin, Calendar, Tag, Megaphone, Edit2, Save, X,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { createPortal } from 'react-dom'

// ─── Constantes ───
const STATUS_STYLES = {
  pending:    { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Pendiente' },
  contacted:  { bg: 'bg-blue-100',   text: 'text-blue-700',   label: 'Contactado' },
  interested: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Interesado' },
  converted:  { bg: 'bg-green-100',  text: 'text-green-700',  label: 'Convertido' },
  rejected:   { bg: 'bg-red-100',    text: 'text-red-700',    label: 'Rechazado' },
}

const STATUS_OPTIONS = [
  { value: 'pending',    label: 'Pendiente' },
  { value: 'contacted',  label: 'Contactado' },
  { value: 'interested', label: 'Interesado' },
  { value: 'rejected',   label: 'Rechazado' },
]

const INSTALL_LABELS = {
  fiber:   'Fibra Óptica',
  antenna: 'Antena',
}

export default function ProspectDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [prospect, setProspect] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Follow-up
  const [note, setNote] = useState('')
  const [addingNote, setAddingNote] = useState(false)

  // Editar estado
  const [editingStatus, setEditingStatus] = useState(false)
  const [newStatus, setNewStatus] = useState('')

  // Modal convertir
  const [showConvertModal, setShowConvertModal] = useState(false)
  const [cutDay, setCutDay] = useState(10)
  const [converting, setConverting] = useState(false)

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [])

  // ─── Fetch ───
  const fetchProspect = async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get(`/prospects/${id}`)
      setProspect(data)
      setNewStatus(data.status)
    } catch (err) {
      console.error('Error cargando prospecto:', err)
      setError('No se pudo cargar el prospecto')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProspect()
  }, [id])

  // ─── Agregar seguimiento ───
  const handleAddNote = async () => {
    if (!note.trim()) return
    setAddingNote(true)
    try {
      await api.post(`/prospects/${id}/follow-up`, { note })
      toast.success('Seguimiento agregado')
      setNote('')
      fetchProspect()
    } catch (err) {
      console.error('Error agregando seguimiento:', err)
      toast.error('Error al agregar seguimiento')
    } finally {
      setAddingNote(false)
    }
  }

  // ─── Cambiar estado ───
  const handleStatusChange = async () => {
    try {
      await api.patch(`/prospects/${id}`, { status: newStatus })
      toast.success('Estado actualizado')
      setEditingStatus(false)
      fetchProspect()
    } catch (err) {
      console.error('Error actualizando estado:', err)
      toast.error('Error al actualizar estado')
    }
  }

  // ─── Convertir a cliente ───
  const handleConvert = async () => {
    setConverting(true)
    try {
      const { data } = await api.post(`/prospects/${id}/convert?cut_day=${cutDay}`)
      toast.success(data.message || 'Prospecto convertido a cliente')
      setShowConvertModal(false)
      // Redirigir al nuevo cliente
      navigate(`/clientes/${data.client_id}`)
    } catch (err) {
      console.error('Error convirtiendo:', err)
      const msg = err.response?.data?.detail
      toast.error(typeof msg === 'string' ? msg : 'Error al convertir prospecto')
    } finally {
      setConverting(false)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return '—'
    return new Date(dateStr).toLocaleDateString('es-MX', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  // ─── Loading / Error ───
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-500">Cargando prospecto...</span>
      </div>
    )
  }

  if (error || !prospect) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <AlertTriangle className="w-8 h-8 text-red-500 mb-2" />
        <p className="text-red-600 mb-3">{error || 'Prospecto no encontrado'}</p>
        <button onClick={() => navigate('/prospectos')} className="text-sm text-blue-600 hover:underline">
          Volver a prospectos
        </button>
      </div>
    )
  }

  const st = STATUS_STYLES[prospect.status] || STATUS_STYLES.pending
  const isConverted = prospect.status === 'converted'

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/prospectos')}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-600" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {prospect.first_name} {prospect.last_name}
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">Prospecto #{prospect.id}</p>
          </div>
        </div>

        {/* Acciones */}
        {!isConverted && (
          <button
            onClick={() => setShowConvertModal(true)}
            className="inline-flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
          >
            <UserCheck className="w-4 h-4" />
            Convertir a Cliente
          </button>
        )}
        {isConverted && prospect.converted_client_id && (
          <button
            onClick={() => navigate(`/clientes/${prospect.converted_client_id}`)}
            className="inline-flex items-center gap-2 bg-green-100 text-green-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-200 transition-colors"
          >
            <UserCheck className="w-4 h-4" />
            Ver Cliente #{prospect.converted_client_id}
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Columna izquierda: Info */}
        <div className="lg:col-span-1 space-y-4">
          {/* Estado */}
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-500 uppercase">Estado</h3>
              {!isConverted && (
                <button
                  onClick={() => setEditingStatus(!editingStatus)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
              )}
            </div>

            {editingStatus && !isConverted ? (
              <div className="flex items-center gap-2">
                <select
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {STATUS_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
                <button
                  onClick={handleStatusChange}
                  className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  <Save className="w-4 h-4" />
                </button>
                <button
                  onClick={() => { setEditingStatus(false); setNewStatus(prospect.status) }}
                  className="p-2 text-gray-400 hover:text-gray-600"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <span className={`inline-flex px-3 py-1 rounded-full text-sm font-semibold ${st.bg} ${st.text}`}>
                {st.label}
              </span>
            )}
          </div>

          {/* Datos de contacto */}
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-500 uppercase mb-3">Contacto</h3>
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <Phone className="w-4 h-4 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm text-gray-900">{prospect.phone || '—'}</p>
                  {prospect.phone_alt && (
                    <p className="text-xs text-gray-500">{prospect.phone_alt}</p>
                  )}
                </div>
              </div>
              <div className="flex items-start gap-3">
                <Mail className="w-4 h-4 text-gray-400 mt-0.5" />
                <p className="text-sm text-gray-900">{prospect.email || '—'}</p>
              </div>
              <div className="flex items-start gap-3">
                <MapPin className="w-4 h-4 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm text-gray-900">{prospect.locality || '—'}</p>
                  {prospect.address && (
                    <p className="text-xs text-gray-500">{prospect.address}</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Clasificación */}
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-500 uppercase mb-3">Clasificación</h3>
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <Tag className="w-4 h-4 text-gray-400 mt-0.5" />
                <p className="text-sm text-gray-900">
                  {prospect.installation_type
                    ? INSTALL_LABELS[prospect.installation_type]
                    : 'Sin definir'}
                </p>
              </div>
              <div className="flex items-start gap-3">
                <Megaphone className="w-4 h-4 text-gray-400 mt-0.5" />
                <p className="text-sm text-gray-900">{prospect.broadcast_medium || '—'}</p>
              </div>
              <div className="flex items-start gap-3">
                <Calendar className="w-4 h-4 text-gray-400 mt-0.5" />
                <p className="text-sm text-gray-900">{formatDate(prospect.created_at)}</p>
              </div>
            </div>

            {prospect.extra_data && (
              <div className="mt-4 pt-3 border-t border-gray-100">
                <p className="text-xs text-gray-500 mb-1">Notas:</p>
                <p className="text-sm text-gray-700">{prospect.extra_data}</p>
              </div>
            )}
          </div>
        </div>

        {/* Columna derecha: Seguimiento */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-500 uppercase mb-4">
              Seguimiento ({prospect.follow_ups?.length || 0})
            </h3>

            {/* Agregar nota */}
            {!isConverted && (
              <div className="mb-5">
                <div className="flex gap-2">
                  <textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Agregar nota de seguimiento..."
                    rows={2}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  />
                  <button
                    onClick={handleAddNote}
                    disabled={!note.trim() || addingNote}
                    className="self-end inline-flex items-center gap-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    {addingNote ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <MessageSquarePlus className="w-4 h-4" />
                    )}
                    Agregar
                  </button>
                </div>
              </div>
            )}

            {/* Lista de seguimientos */}
            {prospect.follow_ups?.length > 0 ? (
              <div className="space-y-3">
                {prospect.follow_ups.map((fup) => (
                  <div key={fup.id} className="border-l-3 border-blue-400 pl-4 py-2">
                    <p className="text-sm text-gray-800">{fup.note}</p>
                    <p className="text-xs text-gray-400 mt-1">{formatDate(fup.created_at)}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <MessageSquarePlus className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                <p className="text-gray-400 text-sm">Sin seguimientos aún</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modal Convertir a Cliente */}
      {showConvertModal && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowConvertModal(false)} />
          <div className="relative bg-white rounded-xl shadow-2xl w-[90%] max-w-[600px] mx-auto p-12">
           <h2 className="text-3xl font-bold text-gray-900 mb-4">Convertir a Cliente</h2>
           <p className="text-lg text-gray-500 mb-8">
              Se creará un nuevo cliente con los datos de <strong>{prospect.first_name} {prospect.last_name}</strong>.
            </p>
            <div className="mb-8">
              <label className="block text-lg font-medium text-gray-700 mb-2">
                Día de corte
              </label>
              <input
                type="number"
                min={1}
                max={31}
                value={cutDay}
                onChange={(e) => setCutDay(parseInt(e.target.value) || 10)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg text-lg outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-sm text-gray-400 mt-2">Día del mes para cobro (1-31)</p>
            </div>

            <div className="flex justify-end gap-4">
              <button
                onClick={() => setShowConvertModal(false)}
                className="px-6 py-3 border border-gray-300 rounded-lg text-lg font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleConvert}
                disabled={converting}
                className="inline-flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg text-lg font-medium hover:bg-green-700 disabled:opacity-50"
              >
                {converting ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <UserCheck className="w-5 h-5" />
                )}
                {converting ? 'Convirtiendo...' : 'Confirmar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
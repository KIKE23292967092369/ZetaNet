import { useState, useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import api from '../../api/axios'
import {
  Plus, Pencil, Trash2, X, Save, Loader2, AlertTriangle,
  CalendarDays, Users,
} from 'lucide-react'
import toast from 'react-hot-toast'

export default function BillingGroupsPage() {
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Modal state
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null) // null = crear, object = editar
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    name: '',
    cutoff_day: 1,
    grace_days: 5,
    reconnection_fee: 50,
    description: '',
  })
  const [formErrors, setFormErrors] = useState({})

  // Delete confirm
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  // ─── Fetch ───
  const fetchGroups = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get('/billing/groups')
      setGroups(data)
    } catch (err) {
      console.error('Error cargando grupos:', err)
      setError('No se pudieron cargar los grupos de facturación')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchGroups()
  }, [fetchGroups])

  // ─── Modal handlers ───
  const openCreate = () => {
    setEditing(null)
    setForm({ name: '', cutoff_day: 1, grace_days: 5, reconnection_fee: 50, description: '' })
    setFormErrors({})
    setShowModal(true)
  }

  const openEdit = (group) => {
    setEditing(group)
    setForm({
      name: group.name,
      cutoff_day: group.cutoff_day,
      grace_days: group.grace_days,
      reconnection_fee: group.reconnection_fee,
      description: group.description || '',
    })
    setFormErrors({})
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditing(null)
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
    if (formErrors[name]) setFormErrors(prev => ({ ...prev, [name]: '' }))
  }

  const validate = () => {
    const errs = {}
    if (!form.name.trim()) errs.name = 'Nombre es requerido'
    if (!form.cutoff_day || form.cutoff_day < 1 || form.cutoff_day > 28) errs.cutoff_day = 'Día de corte: 1-28'
    if (form.grace_days < 0 || form.grace_days > 30) errs.grace_days = 'Días de gracia: 0-30'
    if (form.reconnection_fee < 0) errs.reconnection_fee = 'Debe ser >= 0'
    setFormErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return

    setSaving(true)
    try {
      const payload = {
        name: form.name.trim(),
        cutoff_day: parseInt(form.cutoff_day),
        grace_days: parseInt(form.grace_days),
        reconnection_fee: parseFloat(form.reconnection_fee),
        description: form.description.trim() || null,
      }

      if (editing) {
        await api.patch(`/billing/groups/${editing.id}`, payload)
        toast.success('Grupo actualizado')
      } else {
        await api.post('/billing/groups', payload)
        toast.success('Grupo creado exitosamente')
      }

      closeModal()
      fetchGroups()
    } catch (err) {
      console.error('Error guardando grupo:', err)
      const detail = err.response?.data?.detail
      const message = typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map(e => e.msg).join(', ')
          : 'Error al guardar el grupo'
      toast.error(message)
    } finally {
      setSaving(false)
    }
  }

  // ─── Delete ───
  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await api.delete(`/billing/groups/${deleteTarget.id}`)
      toast.success('Grupo eliminado')
      setDeleteTarget(null)
      fetchGroups()
    } catch (err) {
      const detail = err.response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : 'Error al eliminar')
    } finally {
      setDeleting(false)
    }
  }

  // ─── Input helper ───
  const InputField = ({ label, name, type = 'text', required = false, placeholder = '', min, max }) => (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        type={type}
        name={name}
        value={form[name]}
        onChange={handleChange}
        placeholder={placeholder}
        min={min}
        max={max}
        className={`w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none ${
          formErrors[name] ? 'border-red-400 bg-red-50' : 'border-gray-300'
        }`}
      />
      {formErrors[name] && <p className="text-red-500 text-xs mt-1">{formErrors[name]}</p>}
    </div>
  )

  // ─── Render ───
  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Grupos de Facturación</h1>
          <p className="text-sm text-gray-500 mt-0.5">Configura los días de corte y condiciones de pago</p>
        </div>
        <button
          onClick={openCreate}
          className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nuevo Grupo
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
            <span className="ml-2 text-gray-500">Cargando grupos...</span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-64">
            <AlertTriangle className="w-8 h-8 text-red-500 mb-2" />
            <p className="text-red-600 mb-3">{error}</p>
            <button onClick={fetchGroups} className="text-sm text-blue-600 hover:underline">Reintentar</button>
          </div>
        ) : groups.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64">
            <CalendarDays className="w-12 h-12 text-gray-300 mb-3" />
            <p className="text-gray-500 font-medium">No hay grupos de facturación</p>
            <button onClick={openCreate} className="mt-3 text-sm text-blue-600 hover:underline">
              Crear primer grupo
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Nombre</th>
                  <th className="text-center px-4 py-3 font-semibold text-gray-600">Día de corte</th>
                  <th className="text-center px-4 py-3 font-semibold text-gray-600">Días de gracia</th>
                  <th className="text-right px-4 py-3 font-semibold text-gray-600">Recargo</th>
                  <th className="text-center px-4 py-3 font-semibold text-gray-600">Clientes</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Descripción</th>
                  <th className="text-center px-4 py-3 font-semibold text-gray-600">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {groups.map((g) => (
                  <tr key={g.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">{g.name}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold">
                        <CalendarDays className="w-3 h-3" />
                        Día {g.cutoff_day}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-gray-600">{g.grace_days} días</td>
                    <td className="px-4 py-3 text-right text-gray-700 font-medium">
                      ${g.reconnection_fee.toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center gap-1 text-gray-600">
                        <Users className="w-3.5 h-3.5" />
                        {g.client_count || 0}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 max-w-[200px] truncate">{g.description || '—'}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          onClick={() => openEdit(g)}
                          className="p-1.5 rounded-lg text-gray-500 hover:bg-blue-50 hover:text-blue-600 transition-colors"
                          title="Editar"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setDeleteTarget(g)}
                          className="p-1.5 rounded-lg text-gray-500 hover:bg-red-50 hover:text-red-600 transition-colors"
                          title="Eliminar"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ═══ MODAL CREAR/EDITAR ═══ */}
      {showModal && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4" style={{ zoom: 2.2 }}>
          <div className="fixed inset-0 bg-black/50" onClick={closeModal} />
          <div className="relative bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                {editing ? 'Editar Grupo' : 'Nuevo Grupo de Facturación'}
              </h3>
              <button onClick={closeModal} className="p-1 rounded-lg hover:bg-gray-100 text-gray-500">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <InputField label="Nombre del grupo" name="name" required placeholder="Corte día 5" />

              <div className="grid grid-cols-2 gap-4">
                <InputField label="Día de corte" name="cutoff_day" type="number" required min={1} max={28} />
                <InputField label="Días de gracia" name="grace_days" type="number" min={0} max={30} />
              </div>

              <InputField label="Recargo por pago tardío ($)" name="reconnection_fee" type="number" min={0} placeholder="50.00" />

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Descripción (opcional)</label>
                <textarea
                  name="description"
                  value={form.description}
                  onChange={handleChange}
                  placeholder="Notas del grupo..."
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  disabled={saving}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  <X className="w-4 h-4" />
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  {saving ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* ═══ MODAL CONFIRMAR DELETE ═══ */}
      {deleteTarget && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4" style={{ zoom: 2.2 }}>
          <div className="fixed inset-0 bg-black/50" onClick={() => setDeleteTarget(null)} />
          <div className="relative bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <div className="text-center">
              <div className="mx-auto w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mb-4">
                <Trash2 className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Eliminar grupo</h3>
              <p className="text-sm text-gray-500 mb-6">
                ¿Eliminar <strong>"{deleteTarget.name}"</strong>? Esta acción no se puede deshacer.
                {deleteTarget.client_count > 0 && (
                  <span className="block mt-2 text-red-600 font-medium">
                    Este grupo tiene {deleteTarget.client_count} clientes asignados.
                  </span>
                )}
              </p>
              <div className="flex gap-3 justify-center">
                <button
                  onClick={() => setDeleteTarget(null)}
                  disabled={deleting}
                  className="px-4 py-2 rounded-lg text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
                >
                  {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                  {deleting ? 'Eliminando...' : 'Eliminar'}
                </button>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  )
}
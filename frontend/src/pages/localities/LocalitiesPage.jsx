import { useState, useEffect, useCallback } from 'react'
import api from '../../api/axios'
import {
  Plus, Loader2, AlertTriangle, MapPin, Edit2, Trash2, X, Save,
} from 'lucide-react'
import toast from 'react-hot-toast'

const EMPTY_FORM = {
  name: '',
  municipality: '',
  state: '',
  zip_code: '',
  clave_inegi: '',
  inhabited_homes: '',
  is_active: true,
  notes: '',
}

export default function LocalitiesPage() {
  const [localities, setLocalities] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Modal
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null) // null = crear, object = editar
  const [form, setForm] = useState(EMPTY_FORM)
  const [formErrors, setFormErrors] = useState({})
  const [saving, setSaving] = useState(false)

  // Eliminar
  const [deleting, setDeleting] = useState(null)

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [])

  // ─── Fetch ───
  const fetchLocalities = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get('/localities/')
      setLocalities(data || [])
    } catch (err) {
      console.error('Error cargando localidades:', err)
      setError('No se pudieron cargar las localidades')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchLocalities()
  }, [fetchLocalities])

  // ─── Modal handlers ───
  const openCreate = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
    setFormErrors({})
    setShowModal(true)
  }

  const openEdit = (loc) => {
    setEditing(loc)
    setForm({
      name: loc.name || '',
      municipality: loc.municipality || '',
      state: loc.state || '',
      zip_code: loc.zip_code || '',
      clave_inegi: loc.clave_inegi || '',
      inhabited_homes: loc.inhabited_homes ?? '',
      is_active: loc.is_active ?? true,
      notes: loc.notes || '',
    })
    setFormErrors({})
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditing(null)
    setForm(EMPTY_FORM)
    setFormErrors({})
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
    if (formErrors[name]) setFormErrors((prev) => ({ ...prev, [name]: '' }))
  }

  const validate = () => {
    const errs = {}
    if (!form.name.trim()) errs.name = 'Nombre es requerido'
    if (!form.municipality.trim()) errs.municipality = 'Municipio es requerido'
    if (!form.state.trim()) errs.state = 'Entidad es requerida'
    setFormErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSave = async () => {
    if (!validate()) return
    setSaving(true)
    try {
      const payload = {
        name: form.name.trim(),
        municipality: form.municipality.trim(),
        state: form.state.trim(),
        is_active: form.is_active,
      }
      if (form.zip_code.trim()) payload.zip_code = form.zip_code.trim()
      if (form.clave_inegi.trim()) payload.clave_inegi = form.clave_inegi.trim()
      if (form.inhabited_homes !== '') payload.inhabited_homes = parseInt(form.inhabited_homes) || null
      if (form.notes.trim()) payload.notes = form.notes.trim()

      if (editing) {
        await api.patch(`/localities/${editing.id}`, payload)
        toast.success('Localidad actualizada')
      } else {
        await api.post('/localities/', payload)
        toast.success('Localidad creada')
      }
      closeModal()
      fetchLocalities()
    } catch (err) {
      console.error('Error guardando localidad:', err)
      const msg = err.response?.data?.detail
      toast.error(typeof msg === 'string' ? msg : 'Error al guardar localidad')
    } finally {
      setSaving(false)
    }
  }

  // ─── Eliminar ───
  const handleDelete = async (loc) => {
    setDeleting(loc.id)
    try {
      await api.delete(`/localities/${loc.id}`)
      toast.success('Localidad eliminada')
      fetchLocalities()
    } catch (err) {
      console.error('Error eliminando localidad:', err)
      const msg = err.response?.data?.detail
      toast.error(typeof msg === 'string' ? msg : 'No se pudo eliminar')
    } finally {
      setDeleting(null)
    }
  }

  const inputClass = (field) =>
    `w-full px-3 py-2 border rounded-lg text-sm outline-none transition-colors ${
      formErrors[field]
        ? 'border-red-400 focus:ring-2 focus:ring-red-300'
        : 'border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
    }`

  // ─── Render ───
  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Localidades</h1>
          <p className="text-sm text-gray-500 mt-0.5">{localities.length} localidades registradas</p>
        </div>
        <button
          onClick={openCreate}
          className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nueva Localidad
        </button>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
            <span className="ml-2 text-gray-500">Cargando localidades...</span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-64">
            <AlertTriangle className="w-8 h-8 text-red-500 mb-2" />
            <p className="text-red-600 mb-3">{error}</p>
            <button onClick={fetchLocalities} className="text-sm text-blue-600 hover:underline">
              Reintentar
            </button>
          </div>
        ) : localities.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64">
            <MapPin className="w-12 h-12 text-gray-300 mb-3" />
            <p className="text-gray-500 font-medium">No hay localidades registradas</p>
            <button onClick={openCreate} className="mt-3 text-sm text-blue-600 hover:underline">
              Crear primera localidad
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">ID</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Localidad</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Municipio</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Entidad</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">C.P.</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Clave INEGI</th>
                  <th className="text-right px-4 py-3 font-semibold text-gray-600">Viviendas</th>
                  <th className="text-center px-4 py-3 font-semibold text-gray-600">Activa</th>
                  <th className="text-center px-4 py-3 font-semibold text-gray-600">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {localities.map((loc) => (
                  <tr key={loc.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-gray-500 font-mono text-xs">#{loc.id}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{loc.name}</td>
                    <td className="px-4 py-3 text-gray-600">{loc.municipality}</td>
                    <td className="px-4 py-3 text-gray-600">{loc.state}</td>
                    <td className="px-4 py-3 text-gray-600">{loc.zip_code || '—'}</td>
                    <td className="px-4 py-3 text-gray-600">{loc.clave_inegi || '—'}</td>
                    <td className="px-4 py-3 text-right text-gray-600">{loc.inhabited_homes ?? '—'}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${
                        loc.is_active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-500'
                      }`}>
                        {loc.is_active ? 'Sí' : 'No'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => openEdit(loc)}
                          className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Editar"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(loc)}
                          disabled={deleting === loc.id}
                          className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                          title="Eliminar"
                        >
                          {deleting === loc.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Trash2 className="w-4 h-4" />
                          )}
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

      {/* Modal Crear/Editar */}
      {showModal && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={closeModal} />
          <div className="relative bg-white rounded-xl shadow-2xl w-[90%] max-w-[600px] mx-auto p-10">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">
                {editing ? 'Editar Localidad' : 'Nueva Localidad'}
              </h2>
              <button onClick={closeModal} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  placeholder="Ej: Colinas del Sol"
                  className={inputClass('name')}
                />
                {formErrors.name && <p className="text-red-500 text-xs mt-1">{formErrors.name}</p>}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Municipio <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    name="municipality"
                    value={form.municipality}
                    onChange={handleChange}
                    placeholder="Ej: Tuxtepec"
                    className={inputClass('municipality')}
                  />
                  {formErrors.municipality && <p className="text-red-500 text-xs mt-1">{formErrors.municipality}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Entidad <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    name="state"
                    value={form.state}
                    onChange={handleChange}
                    placeholder="Ej: Oaxaca"
                    className={inputClass('state')}
                  />
                  {formErrors.state && <p className="text-red-500 text-xs mt-1">{formErrors.state}</p>}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Código Postal</label>
                  <input
                    type="text"
                    name="zip_code"
                    value={form.zip_code}
                    onChange={handleChange}
                    placeholder="68000"
                    className={inputClass('zip_code')}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Clave INEGI</label>
                  <input
                    type="text"
                    name="clave_inegi"
                    value={form.clave_inegi}
                    onChange={handleChange}
                    placeholder="123456789"
                    className={inputClass('clave_inegi')}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Viviendas habitadas</label>
                  <input
                    type="number"
                    name="inhabited_homes"
                    value={form.inhabited_homes}
                    onChange={handleChange}
                    placeholder="0"
                    className={inputClass('inhabited_homes')}
                  />
                </div>
                <div className="flex items-end pb-1">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      name="is_active"
                      checked={form.is_active}
                      onChange={handleChange}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <label className="text-sm text-gray-700">Localidad activa (visible para clientes)</label>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notas</label>
                <textarea
                  name="notes"
                  value={form.notes}
                  onChange={handleChange}
                  placeholder="Notas adicionales..."
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={closeModal}
                className="px-5 py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                {saving ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api/axios'
import { ArrowLeft, Save, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

const INSTALL_OPTIONS = [
  { value: '',        label: 'Seleccionar...' },
  { value: 'fiber',   label: 'Fibra Óptica' },
  { value: 'antenna', label: 'Antena' },
]

export default function ProspectCreatePage() {
  const navigate = useNavigate()
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [])

  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    phone_alt: '',
    email: '',
    locality: '',
    address: '',
    latitude: '',
    longitude: '',
    installation_type: '',
    broadcast_medium: '',
    extra_data: '',
  })

  const [errors, setErrors] = useState({})

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }))
  }

  const validate = () => {
    const errs = {}
    if (!form.first_name.trim()) errs.first_name = 'Nombre es requerido'
    if (!form.last_name.trim()) errs.last_name = 'Apellido es requerido'
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return

    setSaving(true)
    try {
      const payload = { ...form }
      // Limpiar campos vacíos
      Object.keys(payload).forEach((k) => {
        if (payload[k] === '') payload[k] = null
      })

      await api.post('/prospects/', payload)
      toast.success('Prospecto registrado')
      navigate('/prospectos')
    } catch (err) {
      console.error('Error creando prospecto:', err)
      const msg = err.response?.data?.detail
      toast.error(typeof msg === 'string' ? msg : 'Error al registrar prospecto')
    } finally {
      setSaving(false)
    }
  }

  const inputClass = (field) =>
    `w-full px-3 py-2 border rounded-lg text-sm outline-none transition-colors ${
      errors[field]
        ? 'border-red-400 focus:ring-2 focus:ring-red-300'
        : 'border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
    }`

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => navigate('/prospectos')}
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Nuevo Prospecto</h1>
          <p className="text-sm text-gray-500 mt-0.5">Registrar un pre-cliente interesado</p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Datos Personales */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-4">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Datos Personales</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="first_name"
                value={form.first_name}
                onChange={handleChange}
                className={inputClass('first_name')}
                placeholder="Nombre(s)"
              />
              {errors.first_name && <p className="text-red-500 text-xs mt-1">{errors.first_name}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Apellido <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="last_name"
                value={form.last_name}
                onChange={handleChange}
                className={inputClass('last_name')}
                placeholder="Apellido(s)"
              />
              {errors.last_name && <p className="text-red-500 text-xs mt-1">{errors.last_name}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
              <input
                type="text"
                name="phone"
                value={form.phone}
                onChange={handleChange}
                className={inputClass('phone')}
                placeholder="Ej: 287 100 0000"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono Alterno</label>
              <input
                type="text"
                name="phone_alt"
                value={form.phone_alt}
                onChange={handleChange}
                className={inputClass('phone_alt')}
                placeholder="Otro teléfono"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                name="email"
                value={form.email}
                onChange={handleChange}
                className={inputClass('email')}
                placeholder="correo@ejemplo.com"
              />
            </div>
          </div>
        </div>

        {/* Ubicación */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-4">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Ubicación</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Localidad</label>
              <input
                type="text"
                name="locality"
                value={form.locality}
                onChange={handleChange}
                className={inputClass('locality')}
                placeholder="Colonia, pueblo o zona"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Dirección</label>
              <input
                type="text"
                name="address"
                value={form.address}
                onChange={handleChange}
                className={inputClass('address')}
                placeholder="Calle y número"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Latitud</label>
              <input
                type="text"
                name="latitude"
                value={form.latitude}
                onChange={handleChange}
                className={inputClass('latitude')}
                placeholder="Ej: 18.0883"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Longitud</label>
              <input
                type="text"
                name="longitude"
                value={form.longitude}
                onChange={handleChange}
                className={inputClass('longitude')}
                placeholder="Ej: -96.1222"
              />
            </div>
          </div>
        </div>

        {/* Clasificación */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-4">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Clasificación</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Instalación</label>
              <select
                name="installation_type"
                value={form.installation_type}
                onChange={handleChange}
                className={inputClass('installation_type')}
              >
                {INSTALL_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Medio de Difusión</label>
              <input
                type="text"
                name="broadcast_medium"
                value={form.broadcast_medium}
                onChange={handleChange}
                className={inputClass('broadcast_medium')}
                placeholder="Ej: Facebook, Recomendación, Volante"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Notas Adicionales</label>
              <textarea
                name="extra_data"
                value={form.extra_data}
                onChange={handleChange}
                rows={3}
                className={inputClass('extra_data')}
                placeholder="Información extra sobre el prospecto..."
              />
            </div>
          </div>
        </div>

        {/* Botones */}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate('/prospectos')}
            className="px-5 py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? 'Guardando...' : 'Guardar Prospecto'}
          </button>
        </div>
      </form>
    </div>
  )
}
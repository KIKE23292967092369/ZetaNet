import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api/axios'
import { Save, X, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

// ─── Componentes FUERA del componente principal (evita pérdida de foco) ───

function InputField({ label, name, type = 'text', required = false, placeholder = '', maxLength, colSpan = false, value, onChange, error }) {
  return (
    <div className={colSpan ? 'sm:col-span-2' : ''}>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        type={type}
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        maxLength={maxLength}
        className={`w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors ${
          error ? 'border-red-400 bg-red-50' : 'border-gray-300'
        }`}
      />
      {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
    </div>
  )
}

function SelectField({ label, name, options, required = false, value, onChange, error }) {
  const [open, setOpen] = useState(false)
  const selected = options.find(o => o.value === value) || options[0]

  return (
    <div className="relative">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        className={`w-full flex items-center justify-between px-3 py-2 border rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-left ${
          error ? 'border-red-400 bg-red-50' : 'border-gray-300'
        }`}
      >
        <span className={value ? 'text-gray-900' : 'text-gray-400'}>{selected.label}</span>
        <svg className={`w-4 h-4 text-gray-500 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden max-h-60 overflow-y-auto">
          {options.map(opt => (
            <div
              key={opt.value}
              onClick={() => {
                onChange({ target: { name, value: opt.value, type: 'text' } })
                setOpen(false)
              }}
              className={`px-3 py-2.5 text-sm cursor-pointer transition-colors ${
                value === opt.value
                  ? 'bg-blue-50 text-blue-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              {opt.label}
            </div>
          ))}
        </div>
      )}
      {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
    </div>
  )
}

function CheckboxField({ label, name, checked, onChange }) {
  return (
    <div className="flex items-center gap-2">
      <input
        type="checkbox"
        name={name}
        checked={checked}
        onChange={onChange}
        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
      />
      <label className="text-sm text-gray-700">{label}</label>
    </div>
  )
}

function TextareaField({ label, name, placeholder = '', colSpan = false, value, onChange }) {
  return (
    <div className={colSpan ? 'sm:col-span-2' : ''}>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <textarea
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        rows={3}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none"
      />
    </div>
  )
}

// ─── Componente principal ───

export default function ClientCreatePage() {
  const navigate = useNavigate()
  const [saving, setSaving] = useState(false)
  const [billingGroups, setBillingGroups] = useState([])
  const [localities, setLocalities] = useState([])

  // Cargar grupos de facturación y localidades
  useEffect(() => {
    api.get('/billing/groups')
      .then(({ data }) => setBillingGroups(data))
      .catch(err => console.error('Error cargando grupos:', err))

    api.get('/localities/?active_only=true')
      .then(({ data }) => setLocalities(data))
      .catch(err => console.error('Error cargando localidades:', err))
  }, [])

  const [form, setForm] = useState({
    contract_date: new Date().toISOString().split('T')[0],
    first_name: '',
    last_name: '',
    locality: '',
    locality_id: '',
    address: '',
    zip_code: '',
    official_id: '',
    rfc: '',
    seller_id: '',
    referral: '',
    requires_einvoice: false,
    phone_landline: '',
    phone_cell: '',
    phone_alt: '',
    email: '',
    email_alt: '',
    broadcast_medium: '',
    extra_data: '',
    client_type: 'con_plan',
    billing_group_id: '',
    cut_day: '',
    no_suspend_first_month: true,
    apply_iva: false,
    bank_account: '',
    latitude: '',
    longitude: '',
    notes: '',
  })

  const [errors, setErrors] = useState({})

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm(prev => {
      const updated = {
        ...prev,
        [name]: type === 'checkbox' ? checked : value,
      }

      // Al seleccionar localidad del dropdown, autocompletar el texto
      if (name === 'locality_id' && value) {
        const loc = localities.find(l => String(l.id) === value)
        if (loc) {
          updated.locality = loc.name
        }
      }
      // Si limpian el dropdown, limpiar el texto
      if (name === 'locality_id' && !value) {
        updated.locality = ''
      }

      return updated
    })
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const validate = () => {
    const errs = {}
    if (!form.first_name.trim()) errs.first_name = 'Nombre es requerido'
    if (!form.last_name.trim()) errs.last_name = 'Apellido es requerido'
    if (!form.locality.trim() && !form.locality_id) errs.locality_id = 'Localidad es requerida'
    if (!form.address.trim()) errs.address = 'Domicilio es requerido'
    if (!form.contract_date) errs.contract_date = 'Fecha de contrato es requerida'
    if (!form.phone_cell.trim()) errs.phone_cell = 'Celular es requerido'
    if (!form.email.trim()) errs.email = 'Email es requerido'
    if (form.cut_day && (parseInt(form.cut_day) < 1 || parseInt(form.cut_day) > 31)) {
      errs.cut_day = 'Día de corte debe ser entre 1 y 31'
    }
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return

    setSaving(true)
    try {
      const payload = {
        contract_date: form.contract_date,
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        locality: form.locality.trim(),
        address: form.address.trim(),
        client_type: form.client_type,
        no_suspend_first_month: form.no_suspend_first_month,
        apply_iva: form.apply_iva,
        requires_einvoice: form.requires_einvoice,
      }

      if (form.locality_id) payload.locality_id = parseInt(form.locality_id)
      if (form.zip_code.trim()) payload.zip_code = form.zip_code.trim()
      if (form.official_id.trim()) payload.official_id = form.official_id.trim()
      if (form.rfc.trim()) payload.rfc = form.rfc.trim()
      if (form.seller_id) payload.seller_id = parseInt(form.seller_id)
      if (form.referral.trim()) payload.referral = form.referral.trim()
      if (form.phone_landline.trim()) payload.phone_landline = form.phone_landline.trim()
      if (form.phone_cell.trim()) payload.phone_cell = form.phone_cell.trim()
      if (form.phone_alt.trim()) payload.phone_alt = form.phone_alt.trim()
      if (form.email.trim()) payload.email = form.email.trim()
      if (form.email_alt.trim()) payload.email_alt = form.email_alt.trim()
      if (form.broadcast_medium.trim()) payload.broadcast_medium = form.broadcast_medium.trim()
      if (form.extra_data.trim()) payload.extra_data = form.extra_data.trim()
      if (form.billing_group_id) payload.billing_group_id = parseInt(form.billing_group_id)
      if (form.cut_day) payload.cut_day = parseInt(form.cut_day)
      if (form.bank_account.trim()) payload.bank_account = form.bank_account.trim()
      if (form.latitude.trim()) payload.latitude = form.latitude.trim()
      if (form.longitude.trim()) payload.longitude = form.longitude.trim()
      if (form.notes.trim()) payload.notes = form.notes.trim()

      const { data } = await api.post('/clients/', payload)
      toast.success(`Cliente ${data.first_name} ${data.last_name} creado exitosamente`)
      navigate('/clientes')
    } catch (err) {
      console.error('Error creando cliente:', err)
      const detail = err.response?.data?.detail
      const message = typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map(e => e.msg).join(', ')
          : 'Error al crear el cliente'
      toast.error(message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Nuevo Cliente</h1>
          <p className="text-sm text-gray-500 mt-0.5">Registra un nuevo suscriptor</p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        {/* ═══ DATOS PERSONALES ═══ */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-4">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100">
            Datos Personales
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <InputField label="Fecha de contrato" name="contract_date" type="date" required value={form.contract_date} onChange={handleChange} error={errors.contract_date} />
            <div />
            <InputField label="Nombre(s)" name="first_name" required placeholder="Juan Carlos" maxLength={200} value={form.first_name} onChange={handleChange} error={errors.first_name} />
            <InputField label="Apellido(s)" name="last_name" required placeholder="García López" maxLength={200} value={form.last_name} onChange={handleChange} error={errors.last_name} />

            {/* Localidad: dropdown si hay localidades, texto libre si no */}
            {localities.length > 0 ? (
              <SelectField
                label="Localidad"
                name="locality_id"
                required
                value={form.locality_id}
                onChange={handleChange}
                error={errors.locality_id}
                options={[
                  { value: '', label: 'Seleccionar localidad...' },
                  ...localities.map(l => ({
                    value: String(l.id),
                    label: `${l.name} — ${l.municipality}`,
                  })),
                ]}
              />
            ) : (
              <InputField label="Localidad" name="locality" required placeholder="Col. Centro" maxLength={300} value={form.locality} onChange={handleChange} error={errors.locality} />
            )}

            <InputField label="Domicilio" name="address" required placeholder="Calle 5 de Mayo #123" maxLength={500} value={form.address} onChange={handleChange} error={errors.address} />
            <InputField label="Código Postal" name="zip_code" placeholder="68000" maxLength={10} value={form.zip_code} onChange={handleChange} error={errors.zip_code} />
            <InputField label="Identificación Oficial" name="official_id" placeholder="INE / Pasaporte" maxLength={100} value={form.official_id} onChange={handleChange} error={errors.official_id} />
            <InputField label="RFC" name="rfc" placeholder="XXXX000000XX0" maxLength={13} value={form.rfc} onChange={handleChange} error={errors.rfc} />
            <InputField label="Referido por" name="referral" placeholder="Nombre de quien lo refirió" maxLength={200} value={form.referral} onChange={handleChange} error={errors.referral} />
          </div>
        </div>

        {/* ═══ CONTACTO ═══ */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-4">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100">
            Información de Contacto
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <InputField label="Teléfono Fijo" name="phone_landline" placeholder="951 123 4567" maxLength={20} value={form.phone_landline} onChange={handleChange} error={errors.phone_landline} />
            <InputField label="Celular" name="phone_cell" required placeholder="951 987 6543" maxLength={20} value={form.phone_cell} onChange={handleChange} error={errors.phone_cell} />
            <InputField label="Teléfono Alternativo" name="phone_alt" placeholder="951 555 1234" maxLength={20} value={form.phone_alt} onChange={handleChange} error={errors.phone_alt} />
            <InputField label="Medio de difusión" name="broadcast_medium" placeholder="Facebook, Volante, etc." maxLength={100} value={form.broadcast_medium} onChange={handleChange} error={errors.broadcast_medium} />
            <InputField label="Email" name="email" type="email" required placeholder="cliente@correo.com" value={form.email} onChange={handleChange} error={errors.email} />
            <InputField label="Email alternativo" name="email_alt" type="email" placeholder="otro@correo.com" value={form.email_alt} onChange={handleChange} error={errors.email_alt} />
            <TextareaField label="Datos extra" name="extra_data" placeholder="Información adicional del cliente..." colSpan value={form.extra_data} onChange={handleChange} />
          </div>
        </div>

        {/* ═══ FACTURACIÓN ═══ */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-4">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100">
            Facturación
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <SelectField
              label="Tipo de cliente"
              name="client_type"
              required
              value={form.client_type}
              onChange={handleChange}
              options={[
                { value: 'con_plan', label: 'Con Plan (mensualidad)' },
                { value: 'prepago', label: 'Prepago' },
              ]}
            />
            <SelectField
              label="Grupo de facturación"
              name="billing_group_id"
              value={form.billing_group_id}
              onChange={handleChange}
              options={[
                { value: '', label: 'Sin grupo asignado' },
                ...billingGroups.map(g => ({
                  value: String(g.id),
                  label: `${g.name} (Corte día ${g.cutoff_day})`,
                })),
              ]}
            />
            <InputField
              label="Día de corte individual"
              name="cut_day"
              type="number"
              placeholder="1-31 (vacío = usa grupo)"
              value={form.cut_day}
              onChange={handleChange}
              error={errors.cut_day}
            />
            <InputField label="Cuenta bancaria (CLABE)" name="bank_account" placeholder="CLABE interbancaria" maxLength={50} value={form.bank_account} onChange={handleChange} error={errors.bank_account} />
            <div className="sm:col-span-2 flex flex-wrap gap-6 pt-2">
              <CheckboxField label="No suspender primer mes" name="no_suspend_first_month" checked={form.no_suspend_first_month} onChange={handleChange} />
              <CheckboxField label="Aplicar IVA" name="apply_iva" checked={form.apply_iva} onChange={handleChange} />
              <CheckboxField label="Requiere factura electrónica" name="requires_einvoice" checked={form.requires_einvoice} onChange={handleChange} />
            </div>
          </div>
        </div>

        {/* ═══ UBICACIÓN Y NOTAS ═══ */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100">
            Ubicación y Notas
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <InputField label="Latitud" name="latitude" placeholder="17.0654" maxLength={20} value={form.latitude} onChange={handleChange} error={errors.latitude} />
            <InputField label="Longitud" name="longitude" placeholder="-96.7236" maxLength={20} value={form.longitude} onChange={handleChange} error={errors.longitude} />
            <TextareaField label="Notas internas" name="notes" placeholder="Notas del cliente visibles solo para el ISP..." colSpan value={form.notes} onChange={handleChange} />
          </div>
        </div>

        {/* ═══ BOTONES ═══ */}
        <div className="flex items-center justify-end gap-3 pb-8">
          <button
            type="button"
            onClick={() => navigate('/clientes')}
            disabled={saving}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            <X className="w-4 h-4" />
            Cancelar
          </button>
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {saving ? 'Guardando...' : 'Guardar'}
          </button>
        </div>
      </form>
    </div>
  )
}
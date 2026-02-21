import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../../api/axios'
import {
  ArrowLeft, Edit2, Save, X, Loader2, AlertTriangle,
  User, Phone, Mail, MapPin, CreditCard, FileText,
  Wifi, Ticket, FolderOpen, Calendar, Hash, Building,
  CheckCircle, XCircle, PauseCircle, Clock, Upload, Trash2, Eye,
  ChevronDown, Plus, Settings, DollarSign, Tag,
} from 'lucide-react'
import toast from 'react-hot-toast'
import CreateConnectionModal from '../connections/CreateConnectionModal'

// ─── Constantes ───
const STATUS_CONFIG = {
  active:    { label: 'Activo',     bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle },
  suspended: { label: 'Suspendido', bg: 'bg-red-100',   text: 'text-red-700',   icon: PauseCircle },
  cancelled: { label: 'Cancelado',  bg: 'bg-gray-100',  text: 'text-gray-600',  icon: XCircle },
  pending:   { label: 'Pendiente',  bg: 'bg-yellow-100',text: 'text-yellow-700', icon: Clock },
}

// ─── Componentes auxiliares ───
function EditField({ label, name, type = 'text', value, onChange, options, placeholder }) {
  if (options) {
    return (
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
        <select name={name} value={value || ''} onChange={onChange}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white outline-none focus:ring-2 focus:ring-blue-500">
          {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>
    )
  }
  if (type === 'textarea') {
    return (
      <div className="sm:col-span-2">
        <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
        <textarea name={name} value={value || ''} onChange={onChange} rows={3} placeholder={placeholder}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
      </div>
    )
  }
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
      <input type={type} name={name} value={value || ''} onChange={onChange} placeholder={placeholder}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500" />
    </div>
  )
}

function Accordion({ icon: Icon, title, count, color = 'bg-gray-600', defaultOpen = false, children, actions }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* ← div en lugar de button para evitar <button> anidados */}
      <div
        onClick={() => setOpen(!open)}
        className={`w-full flex items-center justify-between px-5 py-3.5 transition-colors hover:bg-gray-50 cursor-pointer ${open ? 'border-b border-gray-200' : ''}`}
      >
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg ${color} flex items-center justify-center`}>
            <Icon className="w-4 h-4 text-white" />
          </div>
          <span className="text-sm font-semibold text-gray-800">{title}</span>
          {count !== undefined && (
            <span className="bg-gray-100 text-gray-600 text-xs font-semibold px-2 py-0.5 rounded-full">{count}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {actions && open && (
            <div onClick={(e) => e.stopPropagation()}>
              {actions}
            </div>
          )}
          <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
        </div>
      </div>
      {open && <div className="p-5">{children}</div>}
    </div>
  )
}

// ─── Componente Principal ───
export default function ClientDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [client, setClient] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState({})
  const [saving, setSaving] = useState(false)

  const [localities, setLocalities] = useState([])
  const [billingGroups, setBillingGroups] = useState([])
  const [connections, setConnections] = useState([])
  const [invoices, setInvoices] = useState([])
  const [tickets, setTickets] = useState([])
  const [files, setFiles] = useState([])

  // Modales
  const [showSuspendModal, setShowSuspendModal] = useState(false)
  const [cancelVigency, setCancelVigency] = useState(false)
  const [showEnableModal, setShowEnableModal] = useState(false)
  const [enableDays, setEnableDays] = useState(1)
  const [showConnectionModal, setShowConnectionModal] = useState(false)  // ← NUEVO

  useEffect(() => { window.scrollTo(0, 0) }, [])

  const fetchClient = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get(`/clients/${id}`)
      setClient(data)
    } catch (err) {
      console.error('Error cargando cliente:', err)
      setError('No se pudo cargar el cliente')
    } finally { setLoading(false) }
  }, [id])

  const fetchConnections = useCallback(() => {
    api.get(`/connections?client_id=${id}`)
      .then(({ data }) => setConnections(data.connections || data || []))
      .catch(() => setConnections([]))
  }, [id])

  useEffect(() => {
    fetchClient()
    fetchConnections()
    api.get('/localities/?active_only=true').then(({ data }) => setLocalities(data || [])).catch(() => {})
    api.get('/billing/groups').then(({ data }) => setBillingGroups(data || [])).catch(() => {})
    api.get(`/billing/invoices?client_id=${id}`).then(({ data }) => setInvoices(data.invoices || data || [])).catch(() => setInvoices([]))
    api.get(`/tickets?client_id=${id}`).then(({ data }) => setTickets(data.tickets || data || [])).catch(() => setTickets([]))
    api.get(`/clients/${id}/files`).then(({ data }) => setFiles(data || [])).catch(() => setFiles([]))
  }, [fetchClient, fetchConnections, id])

  // ─── Edit handlers ───
  const startEdit = () => {
    setEditForm({
      first_name: client.first_name, last_name: client.last_name,
      locality: client.locality, locality_id: client.locality_id || '',
      address: client.address, zip_code: client.zip_code || '',
      official_id: client.official_id || '', rfc: client.rfc || '',
      referral: client.referral || '',
      phone_landline: client.phone_landline || '', phone_cell: client.phone_cell || '',
      phone_alt: client.phone_alt || '', email: client.email || '',
      email_alt: client.email_alt || '', broadcast_medium: client.broadcast_medium || '',
      extra_data: client.extra_data || '',
      client_type: client.client_type, billing_group_id: client.billing_group_id || '',
      cut_day: client.cut_day || '',
      no_suspend_first_month: client.no_suspend_first_month,
      apply_iva: client.apply_iva, requires_einvoice: client.requires_einvoice,
      bank_account: client.bank_account || '',
      latitude: client.latitude || '', longitude: client.longitude || '',
      notes: client.notes || '',
    })
    setEditing(true)
  }
  const cancelEdit = () => { setEditing(false); setEditForm({}) }
  const handleEditChange = (e) => {
    const { name, value, type, checked } = e.target
    setEditForm(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
  }

  const saveEdit = async () => {
    setSaving(true)
    try {
      const payload = {}
      const fields = [
        'first_name', 'last_name', 'locality', 'address', 'zip_code',
        'official_id', 'rfc', 'referral', 'phone_landline', 'phone_cell',
        'phone_alt', 'email', 'email_alt', 'broadcast_medium', 'extra_data',
        'client_type', 'bank_account', 'latitude', 'longitude', 'notes',
      ]
      fields.forEach(f => {
        if (editForm[f] !== undefined && editForm[f] !== '') payload[f] = editForm[f]
        else if (editForm[f] === '' && client[f]) payload[f] = null
      })
      if (editForm.billing_group_id) payload.billing_group_id = parseInt(editForm.billing_group_id)
      if (editForm.cut_day) payload.cut_day = parseInt(editForm.cut_day)
      if (editForm.locality_id) payload.locality_id = parseInt(editForm.locality_id)
      payload.no_suspend_first_month = editForm.no_suspend_first_month
      payload.apply_iva = editForm.apply_iva
      payload.requires_einvoice = editForm.requires_einvoice
      await api.put(`/clients/${id}`, payload)
      toast.success('Cliente actualizado')
      setEditing(false)
      fetchClient()
    } catch (err) {
      const msg = err.response?.data?.detail
      toast.error(typeof msg === 'string' ? msg : 'Error al actualizar')
    } finally { setSaving(false) }
  }

  const changeStatus = async (newStatus) => {
    try {
      await api.put(`/clients/${id}`, { status: newStatus })
      toast.success(`Estado cambiado a ${STATUS_CONFIG[newStatus]?.label}`)
      fetchClient()
    } catch { toast.error('Error al cambiar estado') }
  }

  const handleSuspend = async () => {
    try {
      await api.put(`/clients/${id}`, { status: 'suspended' })
      toast.success('Cliente suspendido exitosamente')
      setShowSuspendModal(false)
      setCancelVigency(false)
      fetchClient()
    } catch { toast.error('Error al suspender') }
  }

  const handleEnableTemp = async () => {
    try {
      await api.put(`/clients/${id}`, { status: 'active' })
      toast.success(`Servicio habilitado temporalmente por ${enableDays} día(s)`)
      setShowEnableModal(false)
      setEnableDays(1)
      fetchClient()
    } catch { toast.error('Error al habilitar') }
  }

  const handleUpload = async (category) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*,.pdf'
    input.multiple = true
    input.onchange = async (e) => {
      const selectedFiles = Array.from(e.target.files)
      if (!selectedFiles.length) return
      try {
        for (const file of selectedFiles) {
          const formData = new FormData()
          formData.append('file', file)
          formData.append('category', category)
          await api.post(`/clients/${id}/files`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
        }
        toast.success(`${selectedFiles.length} archivo(s) subido(s)`)
        const { data } = await api.get(`/clients/${id}/files`)
        setFiles(data || [])
      } catch { toast.error('Error al subir archivo (endpoint pendiente)') }
    }
    input.click()
  }

  // ─── Loading / Error ───
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <span className="ml-3 text-gray-500">Cargando cliente...</span>
      </div>
    )
  }
  if (error || !client) {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <AlertTriangle className="w-10 h-10 text-red-500 mb-3" />
        <p className="text-red-600 mb-4">{error || 'Cliente no encontrado'}</p>
        <button onClick={() => navigate('/clientes')} className="text-blue-600 hover:underline text-sm">Volver a clientes</button>
      </div>
    )
  }

  const st = STATUS_CONFIG[client.status] || STATUS_CONFIG.pending
  const StIcon = st.icon

  return (
    <div className="p-6">
      {/* ─── Volver ─── */}
      <button onClick={() => navigate('/clientes')}
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-3">
        <ArrowLeft className="w-4 h-4" /> Volver a clientes
      </button>

      {/* ═══ HEADER 3 COLUMNAS ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">

        {/* Col 1: Datos personales */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                <User className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900">{client.first_name} {client.last_name}</h1>
                <span className="text-xs text-gray-500 font-mono">Cliente #{client.id}</span>
              </div>
            </div>
            {!editing ? (
              <button onClick={startEdit} className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg" title="Editar">
                <Edit2 className="w-4 h-4" />
              </button>
            ) : (
              <div className="flex gap-1">
                <button onClick={cancelEdit} className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg"><X className="w-4 h-4" /></button>
                <button onClick={saveEdit} disabled={saving} className="p-2 text-green-600 hover:bg-green-50 rounded-lg disabled:opacity-50">
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                </button>
              </div>
            )}
          </div>

          {editing ? (
            <div className="space-y-3">
              <EditField label="Nombre(s)" name="first_name" value={editForm.first_name} onChange={handleEditChange} />
              <EditField label="Apellido(s)" name="last_name" value={editForm.last_name} onChange={handleEditChange} />
              {localities.length > 0 ? (
                <EditField label="Localidad" name="locality_id" value={editForm.locality_id} onChange={(e) => {
                  handleEditChange(e)
                  const loc = localities.find(l => String(l.id) === e.target.value)
                  if (loc) handleEditChange({ target: { name: 'locality', value: loc.name, type: 'text' } })
                }} options={[{ value: '', label: 'Seleccionar...' }, ...localities.map(l => ({ value: String(l.id), label: `${l.name} — ${l.municipality}` }))]} />
              ) : (
                <EditField label="Localidad" name="locality" value={editForm.locality} onChange={handleEditChange} />
              )}
              <EditField label="Domicilio" name="address" value={editForm.address} onChange={handleEditChange} />
              <EditField label="Código Postal" name="zip_code" value={editForm.zip_code} onChange={handleEditChange} />
              <EditField label="Identificación" name="official_id" value={editForm.official_id} onChange={handleEditChange} />
              <EditField label="RFC" name="rfc" value={editForm.rfc} onChange={handleEditChange} />
              <EditField label="Referido por" name="referral" value={editForm.referral} onChange={handleEditChange} />
            </div>
          ) : (
            <div className="space-y-0 text-sm">
              <Row label="Contrato" value={client.contract_date} />
              <Row label="Localidad" value={client.locality} />
              <Row label="Domicilio" value={client.address} />
              <Row label="C.P." value={client.zip_code} />
              <Row label="Identificación" value={client.official_id} />
              <Row label="RFC" value={client.rfc} />
              <Row label="Factura electrónica" value={client.requires_einvoice ? 'Sí' : 'No'} />
              <Row label="Referido por" value={client.referral} last />
            </div>
          )}
        </div>

        {/* Col 2: Contacto */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100 uppercase tracking-wide">Contacto</h3>
          {editing ? (
            <div className="space-y-3">
              <EditField label="Celular" name="phone_cell" value={editForm.phone_cell} onChange={handleEditChange} />
              <EditField label="Teléfono Fijo" name="phone_landline" value={editForm.phone_landline} onChange={handleEditChange} />
              <EditField label="Tel. Alternativo" name="phone_alt" value={editForm.phone_alt} onChange={handleEditChange} />
              <EditField label="Email" name="email" type="email" value={editForm.email} onChange={handleEditChange} />
              <EditField label="Email alternativo" name="email_alt" type="email" value={editForm.email_alt} onChange={handleEditChange} />
              <EditField label="Medio difusión" name="broadcast_medium" value={editForm.broadcast_medium} onChange={handleEditChange} />
              <EditField label="Dato Extra" name="extra_data" value={editForm.extra_data} onChange={handleEditChange} />
            </div>
          ) : (
            <div className="space-y-0 text-sm">
              <Row label="Celular" value={client.phone_cell} />
              <Row label="Teléfono fijo" value={client.phone_landline} />
              <Row label="Tel. alternativo" value={client.phone_alt} />
              <Row label="Email" value={client.email} />
              <Row label="Email alternativo" value={client.email_alt} />
              <Row label="Medio difusión" value={client.broadcast_medium} />
              <Row label="Dato Extra" value={client.extra_data} />
              <Row label="Vendedor" value={client.seller_id ? `#${client.seller_id}` : null} />
              <Row label="Tags" value={null} last />
            </div>
          )}
        </div>

        {/* Col 3: Resumen facturación */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="text-center mb-4 pb-4 border-b border-gray-100">
            <p className="text-xs text-gray-500 mb-1">Saldo:</p>
            <p className={`text-4xl font-bold ${Number(client.balance) > 0 ? 'text-red-600' : Number(client.balance) < 0 ? 'text-orange-600' : 'text-green-600'}`}>
              $ {Number(client.balance || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}
            </p>
          </div>

          {editing ? (
            <div className="space-y-3">
              <EditField label="Tipo de cliente" name="client_type" value={editForm.client_type} onChange={handleEditChange}
                options={[{ value: 'con_plan', label: 'Con Plan' }, { value: 'prepago', label: 'Prepago' }]} />
              <EditField label="Grupo facturación" name="billing_group_id" value={editForm.billing_group_id} onChange={handleEditChange}
                options={[{ value: '', label: 'Sin grupo' }, ...billingGroups.map(g => ({ value: String(g.id), label: `${g.name} (Día ${g.cutoff_day})` }))]} />
              <EditField label="Día de corte" name="cut_day" type="number" value={editForm.cut_day} onChange={handleEditChange} placeholder="1-31" />
              <EditField label="Cuenta bancaria" name="bank_account" value={editForm.bank_account} onChange={handleEditChange} />
              <EditField label="Latitud" name="latitude" value={editForm.latitude} onChange={handleEditChange} />
              <EditField label="Longitud" name="longitude" value={editForm.longitude} onChange={handleEditChange} />
              <div className="space-y-2 pt-2">
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input type="checkbox" name="no_suspend_first_month" checked={editForm.no_suspend_first_month} onChange={handleEditChange} className="w-4 h-4 text-blue-600 rounded" />
                  No suspender primer mes
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input type="checkbox" name="apply_iva" checked={editForm.apply_iva} onChange={handleEditChange} className="w-4 h-4 text-blue-600 rounded" />
                  Aplicar IVA
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input type="checkbox" name="requires_einvoice" checked={editForm.requires_einvoice} onChange={handleEditChange} className="w-4 h-4 text-blue-600 rounded" />
                  Requiere factura
                </label>
              </div>
              <EditField label="Notas" name="notes" type="textarea" value={editForm.notes} onChange={handleEditChange} />
            </div>
          ) : (
            <div className="space-y-0 text-sm">
              <div className="flex justify-between py-2 border-b border-gray-50">
                <span className="text-gray-500">Tipo:</span>
                <span className={`font-bold ${client.client_type === 'prepago' ? 'text-orange-600' : 'text-blue-600'}`}>
                  {client.client_type === 'prepago' ? 'Prepago' : 'Con Plan'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-50">
                <span className="text-gray-500">Estado:</span>
                <div className="flex items-center gap-2">
                  <span className={`font-bold ${st.text}`}>{st.label}</span>
                  {client.status !== 'suspended' && (
                    <button onClick={() => setShowSuspendModal(true)} className="text-xs text-red-500 hover:underline">[Suspender]</button>
                  )}
                  {client.status === 'suspended' && (
                    <button onClick={() => setShowEnableModal(true)} className="text-xs text-green-600 hover:underline">[Habilitar]</button>
                  )}
                </div>
              </div>
              <Row label="Día de corte" value={client.cut_day ? `Día ${client.cut_day}` : 'No definido'} />
              <Row label="Grupo" value={client.billing_group_id ? `Grupo #${client.billing_group_id}` : null} />
              <Row label="Cuenta bancaria" value={client.bank_account} last />

              <div className="flex flex-wrap gap-2 pt-3">
                {client.no_suspend_first_month && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                    <CheckCircle className="w-3 h-3" /> No susp. 1er mes
                  </span>
                )}
                {client.apply_iva && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-50 text-purple-700">
                    <CheckCircle className="w-3 h-3" /> IVA
                  </span>
                )}
              </div>

              {(client.latitude && client.longitude) && (
                <a href={`https://www.google.com/maps?q=${client.latitude},${client.longitude}`} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 mt-3 text-xs text-blue-600 hover:underline">
                  <MapPin className="w-3.5 h-3.5" /> Ver en Google Maps
                </a>
              )}

              {client.notes && (
                <div className="mt-3 p-3 bg-yellow-50 rounded-lg border border-yellow-100">
                  <p className="text-xs text-yellow-600 font-medium mb-1">Notas</p>
                  <p className="text-xs text-gray-700 whitespace-pre-wrap">{client.notes}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ═══ ACORDEONES ═══ */}
      <div className="space-y-3 pb-8">

        {/* ─── Conexiones ─── */}
        <Accordion
          icon={Wifi}
          title="Conexiones"
          count={connections.length}
          color="bg-green-600"
          defaultOpen={connections.length > 0}
          
          >
          {connections.length === 0 ? (
            <div className="text-center py-8">
              <Wifi className="w-10 h-10 text-gray-300 mx-auto mb-2" />
              <p className="text-gray-500 text-sm mb-3">No hay conexiones registradas</p>
              <button
                onClick={() => setShowConnectionModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700"
              >
                <Plus className="w-4 h-4" /> Crear primera conexión
              </button>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left px-3 py-2 font-semibold text-gray-600">ID</th>
                  <th className="text-left px-3 py-2 font-semibold text-gray-600">Tipo</th>
                  <th className="text-left px-3 py-2 font-semibold text-gray-600">Plan</th>
                  <th className="text-left px-3 py-2 font-semibold text-gray-600">IP</th>
                  <th className="text-left px-3 py-2 font-semibold text-gray-600">Estado</th>
                  <th className="text-left px-3 py-2 font-semibold text-gray-600">Célula</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {connections.map(conn => (
                  <tr key={conn.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => navigate(`/conexiones/${conn.id}`)}>
                    <td className="px-3 py-2.5 font-mono text-xs text-gray-500">#{conn.id}</td>
                    <td className="px-3 py-2.5">
                      <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                        conn.connection_type === 'fiber_pppoe' ? 'bg-blue-100 text-blue-700'
                        : conn.connection_type === 'fiber_dhcp' ? 'bg-cyan-100 text-cyan-700'
                        : 'bg-amber-100 text-amber-700'
                      }`}>
                        {conn.connection_type === 'fiber_pppoe' ? 'FIBRA PPPoE'
                          : conn.connection_type === 'fiber_dhcp' ? 'FIBRA DHCP'
                          : 'ANTENA'}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-gray-700">{conn.plan_name || conn.plan_id || '—'}</td>
                    <td className="px-3 py-2.5 font-mono text-gray-600">{conn.ip_address || '—'}</td>
                    <td className="px-3 py-2.5">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                        conn.status === 'active' ? 'bg-green-100 text-green-700'
                        : conn.status === 'suspended' ? 'bg-red-100 text-red-700'
                        : 'bg-gray-100 text-gray-600'
                      }`}>
                        {conn.status === 'active' ? 'Activa' : conn.status === 'suspended' ? 'Suspendida' : conn.status}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-gray-600">{conn.cell_name || conn.cell_id || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Accordion>

        {/* ─── Facturación y Cobranza ─── */}
        <Accordion icon={DollarSign} title="Facturación y cobranza" count={invoices.length} color="bg-emerald-600">
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500">Saldo</p>
              <p className={`text-xl font-bold ${Number(client.balance) > 0 ? 'text-red-600' : 'text-green-600'}`}>
                ${Number(client.balance || 0).toFixed(2)}
              </p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500">Facturas</p>
              <p className="text-xl font-bold text-gray-800">{invoices.length}</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500">Día corte</p>
              <p className="text-xl font-bold text-gray-800">{client.cut_day || '—'}</p>
            </div>
          </div>
          {invoices.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-gray-400 text-sm">No hay facturas registradas</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left px-3 py-2 font-semibold text-gray-600">#</th>
                  <th className="text-left px-3 py-2 font-semibold text-gray-600">Periodo</th>
                  <th className="text-right px-3 py-2 font-semibold text-gray-600">Monto</th>
                  <th className="text-left px-3 py-2 font-semibold text-gray-600">Estado</th>
                  <th className="text-left px-3 py-2 font-semibold text-gray-600">Fecha</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {invoices.map(inv => (
                  <tr key={inv.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2.5 font-mono text-xs">#{inv.id}</td>
                    <td className="px-3 py-2.5">{inv.period || '—'}</td>
                    <td className="px-3 py-2.5 text-right font-semibold">${Number(inv.amount || 0).toFixed(2)}</td>
                    <td className="px-3 py-2.5">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                        inv.status === 'paid' ? 'bg-green-100 text-green-700'
                        : inv.status === 'overdue' ? 'bg-red-100 text-red-700'
                        : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {inv.status === 'paid' ? 'Pagada' : inv.status === 'overdue' ? 'Vencida' : 'Pendiente'}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-gray-600">{inv.created_at?.split('T')[0] || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Accordion>

        {/* ─── Archivos ─── */}
        <Accordion icon={FolderOpen} title="Archivos" count={files.length} color="bg-violet-600">
          {[
            { id: 'ine_front', label: 'INE (Frente)', Icon: CreditCard },
            { id: 'ine_back', label: 'INE (Reverso)', Icon: CreditCard },
            { id: 'contract', label: 'Contrato firmado', Icon: FileText },
            { id: 'address_proof', label: 'Comprobante domicilio', Icon: Building },
            { id: 'installation', label: 'Fotos instalación', Icon: Eye },
            { id: 'other', label: 'Otros', Icon: FolderOpen },
          ].map(cat => {
            const catFiles = files.filter(f => f.category === cat.id)
            return (
              <div key={cat.id} className="flex items-center justify-between py-2.5 border-b border-gray-100 last:border-0">
                <div className="flex items-center gap-2">
                  <cat.Icon className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-700">{cat.label}</span>
                  {catFiles.length > 0 && <span className="text-xs text-gray-400">({catFiles.length})</span>}
                </div>
                <div className="flex items-center gap-2">
                  {catFiles.map(f => (
                    <a key={f.id} href={f.url} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline">{f.filename}</a>
                  ))}
                  <button onClick={() => handleUpload(cat.id)}
                    className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg">
                    <Upload className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )
          })}
          <div className="mt-3 p-2 bg-amber-50 rounded-lg">
            <p className="text-xs text-amber-600">Nota: El upload de archivos requiere implementar el endpoint en el backend.</p>
          </div>
        </Accordion>

        {/* ─── Ajustes ─── */}
        <Accordion icon={Settings} title="Ajustes" color="bg-slate-600">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500 mb-2 font-medium">Cambiar Estado</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(STATUS_CONFIG).map(([key, cfg]) => (
                  <button key={key} onClick={() => changeStatus(key)} disabled={client.status === key}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors disabled:opacity-30 ${cfg.bg} ${cfg.text} hover:opacity-80`}>
                    {cfg.label}
                  </button>
                ))}
              </div>
            </div>
            {(client.latitude && client.longitude) && (
              <div>
                <p className="text-xs text-gray-500 mb-2 font-medium">Ubicación</p>
                <a href={`https://www.google.com/maps?q=${client.latitude},${client.longitude}`} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline">
                  <MapPin className="w-4 h-4" /> Ver en Google Maps ({client.latitude}, {client.longitude})
                </a>
              </div>
            )}
          </div>
        </Accordion>

        {/* ─── Tickets ─── */}
        <Accordion icon={Ticket} title="Tickets" count={tickets.length} color="bg-amber-600">
          {tickets.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-gray-400 text-sm">No hay tickets vinculados a este cliente</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left px-3 py-2 font-semibold text-gray-600">#</th>
                  <th className="text-left px-3 py-2 font-semibold text-gray-600">Asunto</th>
                  <th className="text-left px-3 py-2 font-semibold text-gray-600">Tipo</th>
                  <th className="text-left px-3 py-2 font-semibold text-gray-600">Estado</th>
                  <th className="text-left px-3 py-2 font-semibold text-gray-600">Fecha</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {tickets.map(t => (
                  <tr key={t.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => navigate(`/tickets/${t.id}`)}>
                    <td className="px-3 py-2.5 font-mono text-xs">#{t.id}</td>
                    <td className="px-3 py-2.5 font-medium">{t.subject || '—'}</td>
                    <td className="px-3 py-2.5 text-gray-600">{t.ticket_type || '—'}</td>
                    <td className="px-3 py-2.5">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                        t.status === 'closed' ? 'bg-gray-100 text-gray-600'
                        : t.status === 'resolved' ? 'bg-green-100 text-green-700'
                        : t.status === 'in_progress' ? 'bg-blue-100 text-blue-700'
                        : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {t.status === 'closed' ? 'Cerrado' : t.status === 'resolved' ? 'Resuelto' : t.status === 'in_progress' ? 'En proceso' : 'Abierto'}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-gray-600">{t.created_at?.split('T')[0] || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Accordion>

      </div>

      {/* ═══ MODAL: NUEVA CONEXIÓN ═══ */}
      {showConnectionModal && (
        <CreateConnectionModal
          preClientId={id}
          onClose={() => setShowConnectionModal(false)}
          onSaved={() => {
            setShowConnectionModal(false)
            fetchConnections()
            toast.success('Conexión creada y lista')
          }}
        />
      )}

      {/* ═══ MODAL: SUSPENDER SERVICIO ═══ */}
      {showSuspendModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowSuspendModal(false)}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-red-50 rounded-t-xl">
              <h3 className="text-base font-bold text-red-700">Suspender servicio</h3>
              <button onClick={() => setShowSuspendModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="px-6 py-5">
              <p className="text-sm text-gray-700 mb-1">
                Suspenderá el servicio a <strong>{client.first_name} {client.last_name}</strong>, ¿desea continuar?
              </p>
              <p className="text-xs text-gray-500 mb-4">El cliente será suspendido y perderá acceso a internet.</p>
              <label className="flex items-center gap-2 text-sm text-gray-700 mb-2">
                <input type="checkbox" checked={cancelVigency} onChange={(e) => setCancelVigency(e.target.checked)}
                  className="w-4 h-4 text-red-600 border-gray-300 rounded" />
                Cancelar vigencia
              </label>
            </div>
            <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-xl">
              <button onClick={() => setShowSuspendModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
                Cancelar
              </button>
              <button onClick={handleSuspend}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700">
                Suspender
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ MODAL: HABILITAR SERVICIO TEMPORAL ═══ */}
      {showEnableModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowEnableModal(false)}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-green-50 rounded-t-xl">
              <h3 className="text-base font-bold text-green-700">Habilitar servicio</h3>
              <button onClick={() => setShowEnableModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="px-6 py-5">
              <p className="text-sm text-gray-700 mb-1">
                Habilitará el servicio a <strong>{client.first_name} {client.last_name}</strong>
                {Number(client.balance) > 0 && (
                  <span className="text-red-600">, el cliente cuenta con un adeudo de ${Number(client.balance).toFixed(2)}</span>
                )}
                , ¿desea habilitarlo temporalmente?
              </p>
              <div className="flex items-center gap-3 mt-4 mb-4">
                <label className="text-sm font-medium text-gray-700">Tiempo:</label>
                <select value={enableDays} onChange={(e) => setEnableDays(Number(e.target.value))}
                  className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white outline-none focus:ring-2 focus:ring-green-500">
                  {[1,2,3,4,5,6,7,8,9,10].map(d => (
                    <option key={d} value={d}>{d} día{d > 1 ? 's' : ''}</option>
                  ))}
                </select>
              </div>
              <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-100">
                <p className="text-xs text-yellow-700">
                  Después de haber transcurrido el tiempo se revisará el saldo del cliente nuevamente.
                  Si el cliente paga mediante pasarela, el servicio se activa permanentemente de forma automática.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-xl">
              <button onClick={() => setShowEnableModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
                Cancelar
              </button>
              <button onClick={handleEnableTemp}
                className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700">
                Habilitar
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}

// ─── Row helper ───
function Row({ label, value, last = false }) {
  return (
    <div className={`flex justify-between py-2 ${!last ? 'border-b border-gray-50' : ''}`}>
      <span className="text-gray-500">{label}:</span>
      <span className="font-medium text-right max-w-[60%]">{value || '—'}</span>
    </div>
  )
}
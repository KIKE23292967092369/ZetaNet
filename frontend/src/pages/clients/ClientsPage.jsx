import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api/axios'
import {
  Search, Plus, Filter, ChevronLeft, ChevronRight,
  Users, Loader2, AlertTriangle, X, FileSpreadsheet, FileText,
} from 'lucide-react'
import toast from 'react-hot-toast'

// ─── Constantes ───
const STATUS_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'active', label: 'Activo' },
  { value: 'suspended', label: 'Suspendido' },
  { value: 'cancelled', label: 'Cancelado' },
  { value: 'pending', label: 'Pendiente' },
]

const STATUS_STYLES = {
  active:    { bg: 'bg-green-100', text: 'text-green-700', label: 'Activo' },
  suspended: { bg: 'bg-red-100',   text: 'text-red-700',   label: 'Suspendido' },
  cancelled: { bg: 'bg-gray-100',  text: 'text-gray-600',  label: 'Cancelado' },
  pending:   { bg: 'bg-yellow-100',text: 'text-yellow-700', label: 'Pendiente' },
}

const TYPE_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'con_plan', label: 'Con Plan' },
  { value: 'prepago', label: 'Prepago' },
]

const BALANCE_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'yes', label: 'Con deuda' },
  { value: 'no', label: 'Sin deuda' },
]

const PER_PAGE = 20

// ─── Helpers de Export ───
async function exportXLSX(clients) {
  const XLSX = await import('xlsx')
  const rows = clients.map((c) => ({
    ID: c.id,
    Nombre: `${c.first_name} ${c.last_name}`,
    Estado: STATUS_STYLES[c.status]?.label || c.status,
    Saldo: c.balance || 0,
    Localidad: c.locality || '',
    Domicilio: c.address || '',
    Celular: c.phone_cell || '',
    Email: c.email || '',
    Tipo: c.client_type === 'prepago' ? 'Prepago' : 'Con Plan',
  }))
  const ws = XLSX.utils.json_to_sheet(rows)
  // Ancho de columnas
  ws['!cols'] = [
    { wch: 6 }, { wch: 30 }, { wch: 12 }, { wch: 10 },
    { wch: 20 }, { wch: 30 }, { wch: 15 }, { wch: 25 }, { wch: 10 },
  ]
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Clientes')
  XLSX.writeFile(wb, `clientes_${new Date().toISOString().split('T')[0]}.xlsx`)
}

async function exportPDF(clients) {
  const { default: jsPDF } = await import('jspdf')
  await import('jspdf-autotable')

  const doc = new jsPDF('landscape')
  doc.setFontSize(16)
  doc.text('Listado de Clientes', 14, 15)
  doc.setFontSize(9)
  doc.text(`Generado: ${new Date().toLocaleDateString('es-MX')}  •  Total: ${clients.length}`, 14, 22)

  const rows = clients.map((c) => [
    c.id,
    `${c.first_name} ${c.last_name}`,
    STATUS_STYLES[c.status]?.label || c.status,
    `$${(c.balance || 0).toFixed(2)}`,
    c.locality || '',
    c.address || '',
    c.phone_cell || '',
    c.email || '',
    c.client_type === 'prepago' ? 'Prepago' : 'Con Plan',
  ])

  doc.autoTable({
    startY: 27,
    head: [['ID', 'Nombre', 'Estado', 'Saldo', 'Localidad', 'Domicilio', 'Celular', 'Email', 'Tipo']],
    body: rows,
    styles: { fontSize: 7, cellPadding: 2 },
    headStyles: { fillColor: [37, 99, 235], fontSize: 8 },
    alternateRowStyles: { fillColor: [245, 247, 250] },
  })

  doc.save(`clientes_${new Date().toISOString().split('T')[0]}.pdf`)
}

// ─── Componente DropdownFilter ───
function DropdownFilter({ label, value, onChange, options }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  )
}

export default function ClientsPage() {
  const navigate = useNavigate()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [])

  // ─── State ───
  const [clients, setClients] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [exporting, setExporting] = useState('')

  // Filtros
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [localityFilter, setLocalityFilter] = useState('')
  const [groupFilter, setGroupFilter] = useState('')
  const [balanceFilter, setBalanceFilter] = useState('')

  // Datos para dropdowns
  const [localities, setLocalities] = useState([])
  const [billingGroups, setBillingGroups] = useState([])

  // Cargar datos auxiliares
  useEffect(() => {
    api.get('/localities/?active_only=true')
      .then(({ data }) => setLocalities(data || []))
      .catch(() => {})
    api.get('/billing/groups')
      .then(({ data }) => setBillingGroups(data || []))
      .catch(() => {})
  }, [])

  // Contar filtros activos
  const activeFilters = [statusFilter, typeFilter, localityFilter, groupFilter, balanceFilter].filter(Boolean).length

  // ─── Fetch Clients ───
  const fetchClients = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = { page, per_page: PER_PAGE }
      if (search) params.search = search
      if (statusFilter) params.status = statusFilter
      if (typeFilter) params.client_type = typeFilter
      if (localityFilter) params.locality_id = localityFilter
      if (groupFilter) params.billing_group_id = groupFilter
      if (balanceFilter) params.has_balance = balanceFilter

      const { data } = await api.get('/clients/', { params })
      setClients(data.clients || [])
      setTotal(data.total || 0)
    } catch (err) {
      console.error('Error cargando clientes:', err)
      setError('No se pudieron cargar los clientes')
    } finally {
      setLoading(false)
    }
  }, [page, search, statusFilter, typeFilter, localityFilter, groupFilter, balanceFilter])

  useEffect(() => {
    fetchClients()
  }, [fetchClients])

  // ─── Fetch ALL para export (sin paginación) ───
  const fetchAllForExport = async () => {
    const params = { page: 1, per_page: 10000 }
    if (search) params.search = search
    if (statusFilter) params.status = statusFilter
    if (typeFilter) params.client_type = typeFilter
    if (localityFilter) params.locality_id = localityFilter
    if (groupFilter) params.billing_group_id = groupFilter
    if (balanceFilter) params.has_balance = balanceFilter

    const { data } = await api.get('/clients/', { params })
    return data.clients || []
  }

  // ─── Handlers ───
  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    setSearch(searchInput)
  }

  const handleClearSearch = () => {
    setSearchInput('')
    setSearch('')
    setPage(1)
  }

  const handleClearFilters = () => {
    setStatusFilter('')
    setTypeFilter('')
    setLocalityFilter('')
    setGroupFilter('')
    setBalanceFilter('')
    setPage(1)
  }

  const handleExportXLSX = async () => {
    setExporting('xlsx')
    try {
      const all = await fetchAllForExport()
      await exportXLSX(all)
      toast.success(`${all.length} clientes exportados a Excel`)
    } catch (err) {
      console.error('Error exportando XLSX:', err)
      toast.error('Error al exportar Excel')
    } finally {
      setExporting('')
    }
  }

  const handleExportPDF = async () => {
    setExporting('pdf')
    try {
      const all = await fetchAllForExport()
      await exportPDF(all)
      toast.success(`${all.length} clientes exportados a PDF`)
    } catch (err) {
      console.error('Error exportando PDF:', err)
      toast.error('Error al exportar PDF')
    } finally {
      setExporting('')
    }
  }

  const totalPages = Math.ceil(total / PER_PAGE)

  const getRowClass = (client) => {
    if (client.status === 'suspended') return 'bg-red-50 hover:bg-red-100'
    if (client.balance < 0) return 'bg-yellow-50 hover:bg-yellow-100'
    return 'hover:bg-gray-50'
  }

  // ─── Render ───
  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clientes</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} clientes registrados</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleExportXLSX}
            disabled={!!exporting || loading}
            className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            {exporting === 'xlsx' ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSpreadsheet className="w-4 h-4 text-green-600" />}
            Exportar XLSX
          </button>
          <button
            onClick={handleExportPDF}
            disabled={!!exporting || loading}
            className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            {exporting === 'pdf' ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4 text-red-600" />}
            Exportar PDF
          </button>
          <button
            onClick={() => navigate('/clientes/nuevo')}
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Nuevo Cliente
          </button>
        </div>
      </div>

      {/* Search + Filters bar */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Search */}
          <form onSubmit={handleSearch} className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por nombre, email, teléfono, localidad..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
            {searchInput && (
              <button
                type="button"
                onClick={handleClearSearch}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </form>

          {/* Filter toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
              showFilters || activeFilters > 0
                ? 'bg-blue-50 border-blue-300 text-blue-700'
                : 'border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Filter className="w-4 h-4" />
            Filtrar
            {activeFilters > 0 && (
              <span className="bg-blue-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {activeFilters}
              </span>
            )}
          </button>
        </div>

        {/* Advanced Filter panel */}
        {showFilters && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              <DropdownFilter
                label="Estado"
                value={statusFilter}
                onChange={(v) => { setStatusFilter(v); setPage(1) }}
                options={STATUS_OPTIONS}
              />
              <DropdownFilter
                label="Tipo"
                value={typeFilter}
                onChange={(v) => { setTypeFilter(v); setPage(1) }}
                options={TYPE_OPTIONS}
              />
              <DropdownFilter
                label="Localidad"
                value={localityFilter}
                onChange={(v) => { setLocalityFilter(v); setPage(1) }}
                options={[
                  { value: '', label: 'Todas' },
                  ...localities.map((l) => ({ value: String(l.id), label: l.name })),
                ]}
              />
              <DropdownFilter
                label="Grupo de facturación"
                value={groupFilter}
                onChange={(v) => { setGroupFilter(v); setPage(1) }}
                options={[
                  { value: '', label: 'Todos' },
                  ...billingGroups.map((g) => ({ value: String(g.id), label: g.name })),
                ]}
              />
              <DropdownFilter
                label="Saldo"
                value={balanceFilter}
                onChange={(v) => { setBalanceFilter(v); setPage(1) }}
                options={BALANCE_OPTIONS}
              />
            </div>
            {activeFilters > 0 && (
              <div className="mt-3 flex justify-end">
                <button
                  onClick={handleClearFilters}
                  className="text-sm text-blue-600 hover:underline"
                >
                  Limpiar filtros
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
            <span className="ml-2 text-gray-500">Cargando clientes...</span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-64">
            <AlertTriangle className="w-8 h-8 text-red-500 mb-2" />
            <p className="text-red-600 mb-3">{error}</p>
            <button onClick={fetchClients} className="text-sm text-blue-600 hover:underline">
              Reintentar
            </button>
          </div>
        ) : clients.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64">
            <Users className="w-12 h-12 text-gray-300 mb-3" />
            <p className="text-gray-500 font-medium">
              {search || activeFilters > 0 ? 'No se encontraron clientes con esos filtros' : 'No hay clientes registrados'}
            </p>
            {!search && activeFilters === 0 && (
              <button onClick={() => navigate('/clientes/nuevo')} className="mt-3 text-sm text-blue-600 hover:underline">
                Registrar primer cliente
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">ID</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Nombre</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Estado</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-600">Saldo</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Grupo</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Localidad</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Domicilio</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Celular</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Email</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Tipo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {clients.map((client) => {
                    const st = STATUS_STYLES[client.status] || STATUS_STYLES.pending
                    return (
                      <tr
                        key={client.id}
                        className={`cursor-pointer transition-colors ${getRowClass(client)}`}
                        onClick={() => navigate(`/clientes/${client.id}`)}
                      >
                        <td className="px-4 py-3 text-gray-500 font-mono text-xs">#{client.id}</td>
                        <td className="px-4 py-3 font-medium text-gray-900">
                          {client.first_name} {client.last_name}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${st.bg} ${st.text}`}>
                            {st.label}
                          </span>
                        </td>
                        <td className={`px-4 py-3 text-right font-semibold ${
                          client.balance < 0 ? 'text-red-600' : 'text-gray-700'
                        }`}>
                          ${(client.balance || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="px-4 py-3 text-gray-600">{client.billing_group_id || '—'}</td>
                        <td className="px-4 py-3 text-gray-600 max-w-[150px] truncate">{client.locality}</td>
                        <td className="px-4 py-3 text-gray-600 max-w-[200px] truncate">{client.address}</td>
                        <td className="px-4 py-3 text-gray-600">{client.phone_cell || '—'}</td>
                        <td className="px-4 py-3 text-gray-600 max-w-[180px] truncate">{client.email || '—'}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs font-medium ${
                            client.client_type === 'prepago' ? 'text-orange-600' : 'text-blue-600'
                          }`}>
                            {client.client_type === 'prepago' ? 'Prepago' : 'Con Plan'}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
                <p className="text-sm text-gray-600">
                  Mostrando {((page - 1) * PER_PAGE) + 1}–{Math.min(page * PER_PAGE, total)} de {total}
                </p>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="p-1.5 rounded-lg border border-gray-300 text-gray-600 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>

                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNum
                    if (totalPages <= 5) {
                      pageNum = i + 1
                    } else if (page <= 3) {
                      pageNum = i + 1
                    } else if (page >= totalPages - 2) {
                      pageNum = totalPages - 4 + i
                    } else {
                      pageNum = page - 2 + i
                    }
                    return (
                      <button
                        key={pageNum}
                        onClick={() => setPage(pageNum)}
                        className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                          page === pageNum
                            ? 'bg-blue-600 text-white'
                            : 'text-gray-600 hover:bg-white border border-transparent hover:border-gray-300'
                        }`}
                      >
                        {pageNum}
                      </button>
                    )
                  })}

                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="p-1.5 rounded-lg border border-gray-300 text-gray-600 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
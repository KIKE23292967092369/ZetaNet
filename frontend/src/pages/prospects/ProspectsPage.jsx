import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api/axios'
import {
  Search, Plus, Filter, ChevronLeft, ChevronRight,
  UserPlus, Loader2, AlertTriangle, X,
} from 'lucide-react'

// ─── Constantes ───
const STATUS_OPTIONS = [
  { value: '',          label: 'Todos' },
  { value: 'pending',   label: 'Pendiente' },
  { value: 'contacted', label: 'Contactado' },
  { value: 'interested',label: 'Interesado' },
  { value: 'converted', label: 'Convertido' },
  { value: 'rejected',  label: 'Rechazado' },
]

const STATUS_STYLES = {
  pending:    { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Pendiente' },
  contacted:  { bg: 'bg-blue-100',   text: 'text-blue-700',   label: 'Contactado' },
  interested: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Interesado' },
  converted:  { bg: 'bg-green-100',  text: 'text-green-700',  label: 'Convertido' },
  rejected:   { bg: 'bg-red-100',    text: 'text-red-700',    label: 'Rechazado' },
}

const INSTALL_LABELS = {
  fiber:   'Fibra',
  antenna: 'Antena',
}

const PER_PAGE = 20

export default function ProspectsPage() {
  const navigate = useNavigate()

  // ─── State ───
  const [prospects, setProspects] = useState([])
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [])

  // ─── Fetch Prospects ───
  const fetchProspects = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = { page, per_page: PER_PAGE }
      if (statusFilter) params.status = statusFilter

      const { data } = await api.get('/prospects/', { params })
      setProspects(data || [])
    } catch (err) {
      console.error('Error cargando prospectos:', err)
      setError('No se pudieron cargar los prospectos')
    } finally {
      setLoading(false)
    }
  }, [page, statusFilter])

  useEffect(() => {
    fetchProspects()
  }, [fetchProspects])

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

  const handleStatusFilter = (value) => {
    setStatusFilter(value)
    setPage(1)
  }

  // Filtrar por búsqueda local (el API no tiene search param)
  const filtered = search
    ? prospects.filter((p) => {
        const term = search.toLowerCase()
        return (
          p.first_name?.toLowerCase().includes(term) ||
          p.last_name?.toLowerCase().includes(term) ||
          p.phone?.toLowerCase().includes(term) ||
          p.email?.toLowerCase().includes(term) ||
          p.locality?.toLowerCase().includes(term)
        )
      })
    : prospects

  const formatDate = (dateStr) => {
    if (!dateStr) return '—'
    return new Date(dateStr).toLocaleDateString('es-MX', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  }

  // ─── Render ───
  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Prospectos</h1>
          <p className="text-sm text-gray-500 mt-0.5">{filtered.length} prospectos</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => navigate('/prospectos/nuevo')}
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Nuevo Prospecto
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
              placeholder="Buscar por nombre, teléfono, email, localidad..."
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
              showFilters || statusFilter
                ? 'bg-blue-50 border-blue-300 text-blue-700'
                : 'border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Filter className="w-4 h-4" />
            Filtrar
            {statusFilter && (
              <span className="bg-blue-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">1</span>
            )}
          </button>
        </div>

        {/* Filter panel */}
        {showFilters && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <div className="flex flex-wrap gap-2">
              <span className="text-sm text-gray-500 py-1">Estado:</span>
              {STATUS_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => handleStatusFilter(opt.value)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    statusFilter === opt.value
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
            <span className="ml-2 text-gray-500">Cargando prospectos...</span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-64">
            <AlertTriangle className="w-8 h-8 text-red-500 mb-2" />
            <p className="text-red-600 mb-3">{error}</p>
            <button onClick={fetchProspects} className="text-sm text-blue-600 hover:underline">
              Reintentar
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64">
            <UserPlus className="w-12 h-12 text-gray-300 mb-3" />
            <p className="text-gray-500 font-medium">
              {search || statusFilter ? 'No se encontraron prospectos con esos filtros' : 'No hay prospectos registrados'}
            </p>
            {!search && !statusFilter && (
              <button
                onClick={() => navigate('/prospectos/nuevo')}
                className="mt-3 text-sm text-blue-600 hover:underline"
              >
                Registrar primer prospecto
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">ID</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Nombre</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Estado</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Teléfono</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Email</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Localidad</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Tipo</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Fecha</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((prospect) => {
                  const st = STATUS_STYLES[prospect.status] || STATUS_STYLES.pending
                  return (
                    <tr
                      key={prospect.id}
                      className="cursor-pointer hover:bg-gray-50 transition-colors"
                      onClick={() => navigate(`/prospectos/${prospect.id}`)}
                    >
                      <td className="px-4 py-3 text-gray-500 font-mono text-xs">#{prospect.id}</td>
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {prospect.first_name} {prospect.last_name}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${st.bg} ${st.text}`}>
                          {st.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600">{prospect.phone || '—'}</td>
                      <td className="px-4 py-3 text-gray-600 max-w-[180px] truncate">{prospect.email || '—'}</td>
                      <td className="px-4 py-3 text-gray-600 max-w-[150px] truncate">{prospect.locality || '—'}</td>
                      <td className="px-4 py-3">
                        {prospect.installation_type ? (
                          <span className={`text-xs font-medium ${
                            prospect.installation_type === 'fiber' ? 'text-blue-600' : 'text-orange-600'
                          }`}>
                            {INSTALL_LABELS[prospect.installation_type] || prospect.installation_type}
                          </span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{formatDate(prospect.created_at)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
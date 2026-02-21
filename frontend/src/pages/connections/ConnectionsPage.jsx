import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../api/axios";
import toast from "react-hot-toast";
import {
  Wifi, Plus, Search, Filter, ChevronDown,
  Radio, Zap, Clock, CheckCircle2, XCircle,
  AlertCircle, Ban, Eye
} from "lucide-react";
import CreateConnectionModal from "./CreateConnectionModal";
const STATUS_CONFIG = {
  active:          { label: "Activa",           color: "bg-green-100 text-green-700",   icon: CheckCircle2 },
  suspended:       { label: "Suspendida",        color: "bg-red-100 text-red-700",       icon: Ban },
  pending_install: { label: "Pendiente inst.",   color: "bg-yellow-100 text-yellow-700", icon: Clock },
  pending_auth:    { label: "Pendiente auth.",   color: "bg-blue-100 text-blue-700",     icon: AlertCircle },
  cancelled:       { label: "Cancelada",         color: "bg-gray-100 text-gray-500",     icon: XCircle },
};

const TYPE_CONFIG = {
  fiber:   { label: "Fibra",   color: "bg-blue-50 text-blue-600",   icon: Zap },
  antenna: { label: "Antena",  color: "bg-purple-50 text-purple-600", icon: Radio },
};

export default function ConnectionsPage() {
  const navigate = useNavigate();
  const [connections, setConnections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterType, setFilterType] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => { fetchConnections(); }, [filterStatus, filterType]);

  const fetchConnections = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterStatus) params.status = filterStatus;
      if (filterType) params.connection_type = filterType;
      const res = await api.get("/connections/", { params });
      setConnections(res.data);
    } catch { toast.error("Error al cargar conexiones"); }
    finally { setLoading(false); }
  };

  const filtered = connections.filter(c => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      c.client_name?.toLowerCase().includes(s) ||
      c.ip_address?.toLowerCase().includes(s) ||
      c.cell_name?.toLowerCase().includes(s)
    );
  });

  const counts = {
    total: connections.length,
    active: connections.filter(c => c.status === "active").length,
    suspended: connections.filter(c => c.status === "suspended").length,
    pending: connections.filter(c => ["pending_install","pending_auth"].includes(c.status)).length,
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Conexiones</h1>
          <p className="text-sm text-gray-500 mt-0.5">Gestión de conexiones de internet</p>
        </div>
        <button onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
          <Plus className="w-4 h-4" /> Nueva conexión
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total", value: counts.total, color: "text-gray-700", bg: "bg-gray-50" },
          { label: "Activas", value: counts.active, color: "text-green-700", bg: "bg-green-50" },
          { label: "Suspendidas", value: counts.suspended, color: "text-red-700", bg: "bg-red-50" },
          { label: "Pendientes", value: counts.pending, color: "text-yellow-700", bg: "bg-yellow-50" },
        ].map(s => (
          <div key={s.label} className={`${s.bg} rounded-xl p-4 border border-gray-200`}>
            <p className="text-xs font-medium text-gray-500">{s.label}</p>
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 mb-4">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Buscar por cliente, IP, célula..."
              className="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <select value={filterType} onChange={e => setFilterType(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
            <option value="">Todos los tipos</option>
            <option value="fiber">Fibra</option>
            <option value="antenna">Antena</option>
          </select>
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
            <option value="">Todos los estados</option>
            <option value="active">Activas</option>
            <option value="suspended">Suspendidas</option>
            <option value="pending_install">Pendiente instalación</option>
            <option value="pending_auth">Pendiente autorización</option>
            <option value="cancelled">Canceladas</option>
          </select>
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-16">
            <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <Wifi className="w-10 h-10 mx-auto mb-3 text-gray-300" />
            <p className="font-medium">Sin conexiones</p>
            <p className="text-sm mt-1">Crea la primera conexión</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">Cliente</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">Tipo</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">IP</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">Plan</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">Célula</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">Estado</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map(conn => {
                const status = STATUS_CONFIG[conn.status] || STATUS_CONFIG.active;
                const type = TYPE_CONFIG[conn.connection_type] || TYPE_CONFIG.fiber;
                const StatusIcon = status.icon;
                const TypeIcon = type.icon;
                return (
                  <tr key={conn.id} className="hover:bg-gray-50 transition-colors cursor-pointer"
                    onClick={() => navigate(`/conexiones/${conn.id}`)}>
                    <td className="px-4 py-3">
                      <p className="text-sm font-semibold text-gray-900">{conn.client_name || "—"}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${type.color}`}>
                        <TypeIcon className="w-3 h-3" /> {type.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm font-mono text-gray-700">{conn.ip_address || "—"}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-600">{conn.plan_name || "—"}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-600">{conn.cell_name || "—"}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${status.color}`}>
                        <StatusIcon className="w-3 h-3" /> {status.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button onClick={e => { e.stopPropagation(); navigate(`/conexiones/${conn.id}`); }}
                        className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal crear — próximo paso */}
     {showCreateModal && (
  <CreateConnectionModal
    onClose={() => setShowCreateModal(false)}
    onSaved={() => { setShowCreateModal(false); fetchConnections(); }}
  />
)}
    </div>
  );
}

/**
 * CellDetailPage.jsx
 * NetKeeper - Ficha completa de Célula
 * PATHS CORREGIDOS: baseURL ya es /api/v1, todas las llamadas sin prefijo /v1/
 */
import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../../api/axios";
import toast from "react-hot-toast";
import {
  ArrowLeft, ChevronDown, ChevronUp, Pencil, Check, X,
  Server, Wifi, Radio, Zap, Network, Settings, Router,
  Plus, CheckCircle2, XCircle, AlertCircle,
  Globe, Cable, ToggleLeft, ToggleRight, RefreshCw, Activity,
} from "lucide-react";

const CELL_TYPE_LABELS = {
  fibra:        { label: "Fibra PPPoE",  color: "bg-blue-100 text-blue-700"    },
  antenas:      { label: "Antenas",       color: "bg-purple-100 text-purple-700" },
  hifiber_ipoe: { label: "Fibra IPoE",   color: "bg-cyan-100 text-cyan-700"    },
};
const ASSIGNMENT_LABELS = {
  pppoe_distributed: { label: "PPPoE",     color: "bg-blue-50 text-blue-600"     },
  static_addressing:  { label: "Estático",  color: "bg-orange-50 text-orange-600" },
  dhcp_pool:          { label: "DHCP",      color: "bg-green-50 text-green-600"   },
};

// ─── Inputs FUERA del componente principal ────────────────────────────────────
const FieldText = ({ label, name, value, onChange, placeholder, className = "" }) => (
  <div className={className}>
    <label className="block text-xs font-semibold text-gray-500 mb-1">{label}</label>
    <input type="text" name={name} value={value || ""} onChange={onChange} placeholder={placeholder}
      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
  </div>
);
const FieldPassword = ({ label, name, value, onChange, className = "" }) => (
  <div className={className}>
    <label className="block text-xs font-semibold text-gray-500 mb-1">{label}</label>
    <input type="password" name={name} value={value || ""} onChange={onChange} placeholder="••••••••"
      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
  </div>
);
const FieldNumber = ({ label, name, value, onChange, placeholder, className = "" }) => (
  <div className={className}>
    <label className="block text-xs font-semibold text-gray-500 mb-1">{label}</label>
    <input type="number" name={name} value={value || ""} onChange={onChange} placeholder={placeholder}
      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
  </div>
);
const FieldSelect = ({ label, name, value, onChange, options, className = "" }) => (
  <div className={className}>
    <label className="block text-xs font-semibold text-gray-500 mb-1">{label}</label>
    <select name={name} value={value || ""} onChange={onChange}
      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  </div>
);
const FieldToggle = ({ label, name, checked, onChange, description }) => (
  <label className="flex items-center gap-3 cursor-pointer">
    <div className="relative">
      <input type="checkbox" name={name} checked={!!checked} onChange={onChange} className="sr-only" />
      <div className={`w-10 h-5 rounded-full transition-colors ${checked ? "bg-blue-600" : "bg-gray-300"}`} />
      <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${checked ? "translate-x-5" : ""}`} />
    </div>
    <div>
      <span className="text-sm font-medium text-gray-700">{label}</span>
      {description && <p className="text-xs text-gray-400">{description}</p>}
    </div>
  </label>
);

// ─── Acordeón ─────────────────────────────────────────────────────────────────
const Accordion = ({ title, icon: Icon, iconColor = "text-blue-600", bgColor = "bg-blue-50", open, onToggle, badge, children }) => (
  <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
    <button type="button" onClick={onToggle}
      className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors">
      <div className="flex items-center gap-3">
        <div className={`p-2 ${bgColor} rounded-lg`}><Icon className={`w-4 h-4 ${iconColor}`} /></div>
        <span className="font-semibold text-gray-800">{title}</span>
        {badge && <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs font-medium">{badge}</span>}
      </div>
      {open ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
    </button>
    {open && <div className="px-6 pb-6 border-t border-gray-100">{children}</div>}
  </div>
);

// ─── EditBar ──────────────────────────────────────────────────────────────────
const EditBar = ({ editing, onEdit, onSave, onCancel, saving, section }) => (
  <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-gray-100">
    {!editing ? (
      <button onClick={() => onEdit(section)}
        className="flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50">
        <Pencil className="w-3.5 h-3.5" /> Editar
      </button>
    ) : (
      <>
        <button onClick={onCancel}
          className="flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50">
          <X className="w-3.5 h-3.5" /> Cancelar
        </button>
        <button onClick={() => onSave(section)} disabled={saving}
          className="flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
          {saving ? <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Check className="w-3.5 h-3.5" />}
          Guardar
        </button>
      </>
    )}
  </div>
);

// ─── InfoRow ──────────────────────────────────────────────────────────────────
const InfoRow = ({ label, value, mono = false }) => (
  <div>
    <p className="text-xs font-semibold text-gray-400 mb-0.5">{label}</p>
    <p className={`text-sm text-gray-800 ${mono ? "font-mono" : "font-medium"}`}>{value || <span className="text-gray-300">—</span>}</p>
  </div>
);

// ─── IP Pool Table (por interfaz MikroTik) ────────────────────────────────────
const InterfacePoolBlock = ({ iface, navigate }) => {
  const [showAll, setShowAll] = useState(false);
  const usedPct = iface.total > 0 ? Math.round((iface.used / iface.total) * 100) : 0;
  const displayIps = showAll ? iface.ips : iface.ips.slice(0, 20);

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden mb-4">
      {/* Header de la interfaz */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <span className="font-mono font-bold text-gray-800 text-sm">{iface.interface}</span>
          <span className="font-mono text-xs text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-200">
            {iface.cidr}
          </span>
          {iface.disabled && (
            <span className="text-xs text-red-500 bg-red-50 px-2 py-0.5 rounded-full border border-red-200">
              Deshabilitada
            </span>
          )}
        </div>
        {/* Mini stats */}
        <div className="flex items-center gap-4 text-xs">
          <span className="text-gray-500">Total: <strong className="text-gray-700">{iface.total}</strong></span>
          <span className="text-red-500">Usadas: <strong>{iface.used}</strong></span>
          <span className="text-green-600">Libres: <strong>{iface.available}</strong></span>
        </div>
      </div>

      {/* Barra de progreso */}
      <div className="px-4 pt-3 pb-2">
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>{usedPct}% ocupado</span>
          <span className={usedPct > 80 ? "text-red-500 font-semibold" : usedPct > 60 ? "text-amber-500" : "text-green-600"}>
            {iface.available} IPs libres
          </span>
        </div>
        <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${usedPct > 80 ? "bg-red-500" : usedPct > 60 ? "bg-amber-400" : "bg-green-500"}`}
            style={{ width: `${usedPct}%` }}
          />
        </div>
      </div>

      {/* Tabla de IPs */}
      <div className="divide-y divide-gray-100 max-h-64 overflow-y-auto">
        {/* Header tabla */}
        <div className="grid grid-cols-12 px-4 py-1.5 bg-gray-50 border-y border-gray-100">
          <span className="col-span-3 text-xs font-semibold text-gray-400">IP</span>
          <span className="col-span-2 text-xs font-semibold text-gray-400">Estado</span>
          <span className="col-span-4 text-xs font-semibold text-gray-400">Cliente</span>
          <span className="col-span-2 text-xs font-semibold text-gray-400">PPPoE</span>
          <span className="col-span-1 text-xs font-semibold text-gray-400"></span>
        </div>
        {displayIps.map((ip) => (
          <div key={ip.address}
            className={`grid grid-cols-12 px-4 py-2 text-xs transition-colors ${ip.used ? "hover:bg-red-50/40" : "hover:bg-green-50/40"}`}>
            <span className="col-span-3 font-mono text-gray-800">{ip.address}</span>
            <span className="col-span-2">
              {ip.used ? (
                <span className="flex items-center gap-1 font-medium text-red-600">
                  <span className="w-1.5 h-1.5 bg-red-500 rounded-full" /> Ocupada
                </span>
              ) : (
                <span className="flex items-center gap-1 font-medium text-green-600">
                  <span className="w-1.5 h-1.5 bg-green-500 rounded-full" /> Libre
                </span>
              )}
            </span>
            <span className="col-span-4 text-gray-700 truncate font-medium">
              {ip.client_name || <span className="text-gray-300">—</span>}
            </span>
            <span className="col-span-2 font-mono text-gray-400 truncate">
              {ip.pppoe_username || <span className="text-gray-300">—</span>}
            </span>
            <span className="col-span-1 text-right">
              {ip.used && ip.client_id && (
                <button
                  onClick={() => navigate(`/clientes/${ip.client_id}`)}
                  className="text-indigo-400 hover:text-indigo-600 transition-colors"
                  title="Ver cliente"
                >
                  →
                </button>
              )}
            </span>
          </div>
        ))}
      </div>

      {/* Ver más */}
      {iface.ips.length > 20 && (
        <div className="border-t border-gray-200 px-4 py-2 bg-gray-50 text-center">
          <button onClick={() => setShowAll(v => !v)}
            className="text-xs text-indigo-600 font-medium hover:underline">
            {showAll ? "Mostrar menos" : `Ver ${iface.ips.length - 20} IPs más`}
          </button>
        </div>
      )}
    </div>
  );
};

const IpPoolTable = ({ cellId }) => {
  const navigate = useNavigate();
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded]   = useState(false);

  const loadPool = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/cells/${cellId}/ip-pool-by-interface`);
      setData(res.data);
      setLoaded(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al cargar IP Pool");
    } finally {
      setLoading(false);
    }
  };

  // Totales globales
  const totals = data?.interfaces?.reduce(
    (acc, iface) => ({
      total:     acc.total + iface.total,
      used:      acc.used + iface.used,
      available: acc.available + iface.available,
    }),
    { total: 0, used: 0, available: 0 }
  ) ?? null;

  return (
    <div className="mt-6 border-t border-gray-100 pt-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-xs font-bold text-gray-500 uppercase tracking-wide">IP Pool por Interfaz</p>
          {totals && (
            <p className="text-xs text-gray-400 mt-0.5">
              {data.interfaces.length} interfaz{data.interfaces.length !== 1 ? "es" : ""} ·{" "}
              <span className="text-red-500">{totals.used} usadas</span> ·{" "}
              <span className="text-green-600">{totals.available} libres</span>
            </p>
          )}
        </div>
        <button
          onClick={loadPool}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-indigo-600 border border-indigo-200 bg-indigo-50 rounded-lg hover:bg-indigo-100 disabled:opacity-50 transition-colors"
        >
          {loading
            ? <><div className="w-3 h-3 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /> Leyendo MikroTik...</>
            : <><RefreshCw className="w-3 h-3" /> {loaded ? "Actualizar" : "Ver IPs"}</>
          }
        </button>
      </div>

      {!loaded && !loading && (
        <p className="text-xs text-gray-400 italic text-center py-4">
          Conecta al MikroTik para ver los rangos por interfaz y quién ocupa cada IP
        </p>
      )}

      {loaded && data?.interfaces?.length === 0 && (
        <p className="text-xs text-gray-400 italic text-center py-4">
          No se encontraron interfaces con IPs configuradas en el MikroTik
        </p>
      )}

      {loaded && data?.interfaces?.map(iface => (
        <InterfacePoolBlock key={iface.interface} iface={iface} navigate={navigate} />
      ))}
    </div>
  );
};

// ─── Modal Zona ───────────────────────────────────────────────────────────────
const ZoneModal = ({ open, cellId, onClose, onSaved }) => {
  const [name, setName] = useState("");
  const [slotPort, setSlotPort] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (open) { setName(""); setSlotPort(""); } }, [open]);
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return toast.error("El nombre es obligatorio");
    setSaving(true);
    try {
      await api.post(`/cells/${cellId}/zones`, { name, slot_port: slotPort || null });
      toast.success("Zona creada");
      onSaved();
    } catch (err) { toast.error(err.response?.data?.detail || "Error al crear zona"); }
    finally { setSaving(false); }
  };
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-gray-900">Nueva Zona OLT</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg"><X className="w-4 h-4" /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <FieldText label="Nombre" name="name" value={name} onChange={e => setName(e.target.value)} placeholder="ej: Zona Norte" />
          <FieldText label="Slot/Puerto OLT" name="slot_port" value={slotPort} onChange={e => setSlotPort(e.target.value)} placeholder="ej: 0/1" />
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50">Cancelar</button>
            <button type="submit" disabled={saving} className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1.5">
              {saving ? <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
              Crear zona
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ─── Modal NAP ────────────────────────────────────────────────────────────────
const NapModal = ({ open, zoneId, zoneName, onClose, onSaved }) => {
  const [form, setForm] = useState({ name: "", total_ports: "8", address: "" });
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (open) setForm({ name: "", total_ports: "8", address: "" }); }, [open]);
  const handleChange = useCallback((e) => { setForm(prev => ({ ...prev, [e.target.name]: e.target.value })); }, []);
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return toast.error("El nombre es obligatorio");
    setSaving(true);
    try {
      await api.post(`/cells/zones/${zoneId}/naps`, {
        name: form.name, total_ports: parseInt(form.total_ports), address: form.address || null,
      });
      toast.success(`NAP creada en ${zoneName}`);
      onSaved();
    } catch (err) { toast.error(err.response?.data?.detail || "Error al crear NAP"); }
    finally { setSaving(false); }
  };
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <div><h3 className="font-bold text-gray-900">Nueva NAP</h3><p className="text-xs text-gray-500">Zona: {zoneName}</p></div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg"><X className="w-4 h-4" /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <FieldText label="Nombre" name="name" value={form.name} onChange={handleChange} placeholder="ej: NAP-01" />
          <FieldNumber label="Total puertos" name="total_ports" value={form.total_ports} onChange={handleChange} placeholder="8" />
          <FieldText label="Ubicación" name="address" value={form.address} onChange={handleChange} placeholder="ej: Poste frente #45" />
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50">Cancelar</button>
            <button type="submit" disabled={saving} className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1.5">
              {saving ? <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
              Crear NAP
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ─── ZoneRow ──────────────────────────────────────────────────────────────────
const ZoneRow = ({ zone, onAddNap }) => {
  const [open, setOpen] = useState(false);
  const [naps, setNaps] = useState([]);
  const [loadingNaps, setLoadingNaps] = useState(false);
  const loadNaps = async () => {
    if (open) { setOpen(false); return; }
    setOpen(true);
    if (naps.length > 0) return;
    setLoadingNaps(true);
    try {
      const res = await api.get(`/cells/zones/${zone.id}/cascade/naps`);
      setNaps(res.data);
    } catch { toast.error("Error al cargar NAPs"); }
    finally { setLoadingNaps(false); }
  };
  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 cursor-pointer hover:bg-gray-100" onClick={loadNaps}>
        <div className="flex items-center gap-3">
          {open ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
          <span className="font-semibold text-sm text-gray-800">{zone.name}</span>
          {zone.slot_port && <span className="text-xs text-gray-400 font-mono">Slot: {zone.slot_port}</span>}
        </div>
        <button onClick={(e) => { e.stopPropagation(); onAddNap(); }}
          className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100">
          <Plus className="w-3 h-3" /> NAP
        </button>
      </div>
      {open && (
        <div className="px-4 py-3 space-y-2 bg-white">
          {loadingNaps ? (
            <div className="flex justify-center py-4"><div className="w-5 h-5 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin" /></div>
          ) : naps.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-3">Sin NAPs en esta zona</p>
          ) : naps.map(nap => (
            <div key={nap.id} className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <Network className="w-3.5 h-3.5 text-gray-400" />
                <span className="text-sm font-medium text-gray-700">{nap.name}</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(nap.free_ports / nap.total_ports) * 100}%` }} />
                </div>
                <span className="text-xs text-gray-500">{nap.free_ports}/{nap.total_ports} libres</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ─── Botón Probar Conexión ────────────────────────────────────────────────────
const TestConnectionButton = ({ cellId }) => {
  const [status, setStatus] = useState(null);
  const [info, setInfo] = useState(null);

  const test = async () => {
    setStatus("loading");
    setInfo(null);
    try {
      const res = await api.get(`/mikrotik/test/${cellId}`);
      if (res.data.connected === false) {
        setStatus("error");
        setInfo(res.data.error || "No se pudo conectar");
      } else {
        setStatus("ok");
        setInfo(res.data);
      }
    } catch (err) {
      setStatus("error");
      setInfo(err.response?.data?.detail || "Error de conexión");
    }
  };

  return (
    <div className="mb-4">
      <button onClick={test} disabled={status === "loading"}
        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors">
        {status === "loading"
          ? <><div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Probando...</>
          : <><Router className="w-3.5 h-3.5" /> Probar conexión</>
        }
      </button>
      {status === "ok" && (
        <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm font-semibold text-green-700 flex items-center gap-1.5 mb-2">
            <CheckCircle2 className="w-4 h-4" /> Conexión exitosa
          </p>
          <div className="grid grid-cols-3 gap-3 text-xs text-green-800">
            {info.version    && <span><strong>Versión:</strong> {info.version}</span>}
            {info.uptime     && <span><strong>Uptime:</strong> {info.uptime}</span>}
            {info.cpu_load   && <span><strong>CPU:</strong> {info.cpu_load}%</span>}
            {info.board_name && <span><strong>Modelo:</strong> {info.board_name}</span>}
            {info.free_memory && <span><strong>RAM libre:</strong> {info.free_memory}</span>}
          </div>
        </div>
      )}
      {status === "error" && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm font-semibold text-red-700 flex items-center gap-1.5 mb-1">
            <XCircle className="w-4 h-4" /> Sin conexión
          </p>
          <p className="text-xs text-red-600 font-mono">{info}</p>
        </div>
      )}
    </div>
  );
};

// ─── Componente principal ──────────────────────────────────────────────────────
export default function CellDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [cell, setCell] = useState(null);
  const [loading, setLoading] = useState(true);
  const [plans, setPlans] = useState([]);
  const [zones, setZones] = useState([]);
  const [interfaces, setInterfaces] = useState([]);
  const [oltConfig, setOltConfig] = useState(null);
  const [open, setOpen] = useState({ general: true, mikrotik: false, red: false, olt: false, zonas: false, interfaces: false, planes: false, ipv4: false, queues: false, mikrotikLive: false });
  const [editing, setEditing] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [mkLive, setMkLive] = useState({ data: null, loading: false, loaded: false });

  const loadMkLive = async () => {
    if (mkLive.loaded) return;
    setMkLive(prev => ({ ...prev, loading: true }));
    try {
      const [ifacesRes, ipsRes, queuesRes, secretsRes] = await Promise.all([
        api.get(`/mikrotik/interfaces/${id}`),
        api.get(`/mikrotik/ip-addresses/${id}`),
        api.get(`/mikrotik/queues/${id}`),
        api.get(`/mikrotik/ppp-secrets/${id}`).catch(() => ({ data: [] })),
      ]);
      setMkLive({
        loading: false, loaded: true,
        data: {
          interfaces: Array.isArray(ifacesRes.data) ? ifacesRes.data : (ifacesRes.data?.interfaces || ifacesRes.data?.data || []),
          ips: Array.isArray(ipsRes.data) ? ipsRes.data : (ipsRes.data?.addresses || ipsRes.data?.data || []),
          queues: Array.isArray(queuesRes.data) ? queuesRes.data : (queuesRes.data?.queues || queuesRes.data?.data || []),
          secrets: Array.isArray(secretsRes.data) ? secretsRes.data : (secretsRes.data?.secrets || secretsRes.data?.data || []),
        }
      });
    } catch {
      toast.error("Error al leer MikroTik");
      setMkLive(prev => ({ ...prev, loading: false }));
    }
  };

  const [zoneModal, setZoneModal] = useState(false);
  const [napModal, setNapModal] = useState({ open: false, zoneId: null, zoneName: "" });

  useEffect(() => { window.scrollTo(0, 0); fetchAll(); }, [id]);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [cellRes, plansRes] = await Promise.all([
        api.get(`/cells/${id}`),
        api.get("/plans/", { params: { is_active: true } }),
      ]);
      const c = cellRes.data;
      setCell(c);
      setPlans(plansRes.data);
      if (c.cell_type === "fibra" || c.cell_type === "hifiber_ipoe") {
        const [zonesRes, oltRes] = await Promise.all([
          api.get(`/cells/${id}/zones`),
          api.get(`/cells/${id}/olt`).catch(() => ({ data: null })),
        ]);
        setZones(zonesRes.data);
        setOltConfig(oltRes.data);
      }
      if (c.cell_type === "antenas") {
        const ifaceRes = await api.get(`/cells/${id}/interfaces`);
        setInterfaces(ifaceRes.data);
      }
    } catch { toast.error("Error al cargar la célula"); }
    finally { setLoading(false); }
  };

  const toggleAccordion = (key) => setOpen(prev => ({ ...prev, [key]: !prev[key] }));
  const startEdit = (section) => { setEditing(section); setEditForm({ ...cell }); };
  const cancelEdit = () => { setEditing(null); setEditForm({}); };
  const handleFieldChange = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    setEditForm(prev => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  }, []);

  const saveSection = async (section) => {
    setSaving(true);
    try {
      let payload = {};
      if (section === "general") payload = { name: editForm.name, address: editForm.address || null, range_meters: editForm.range_meters ? parseInt(editForm.range_meters) : null, use_pcq: editForm.use_pcq };
      else if (section === "mikrotik") payload = { mikrotik_host: editForm.mikrotik_host || null, mikrotik_username_encrypted: editForm.mikrotik_username_encrypted || null, mikrotik_password_encrypted: editForm.mikrotik_password_encrypted || null, mikrotik_api_port: parseInt(editForm.mikrotik_api_port) || 8728, mikrotik_use_ssl: editForm.mikrotik_use_ssl };
      else if (section === "red") payload = { pppoe_service_ip: editForm.pppoe_service_ip || null, dhcp_pool_start: editForm.dhcp_pool_start || null, dhcp_pool_end: editForm.dhcp_pool_end || null, dhcp_gateway: editForm.dhcp_gateway || null, dhcp_dns1: editForm.dhcp_dns1 || null, dhcp_dns2: editForm.dhcp_dns2 || null, dhcp_lease_time: editForm.dhcp_lease_time || "1d", dhcp_interface: editForm.dhcp_interface || null };
      else if (section === "ipv4") payload = { ipv4_range: editForm.ipv4_range || null, ipv4_mask: editForm.ipv4_mask || null, ipv4_host_min: editForm.ipv4_host_min || null, ipv4_host_max: editForm.ipv4_host_max || null, ipv6_enabled: editForm.ipv6_enabled };
      else if (section === "queues") payload = { queue_total: editForm.queue_total || null, queue_upload: editForm.queue_upload || null, queue_download: editForm.queue_download || null };
      const res = await api.patch(`/cells/${id}`, payload);
      setCell(res.data);
      setEditing(null);
      toast.success("Guardado correctamente");
    } catch (err) { toast.error(err.response?.data?.detail || "Error al guardar"); }
    finally { setSaving(false); }
  };

  const toggleInterface = async (iface) => {
    try {
      const res = await api.patch(`/cells/interfaces/${iface.id}`, { connections_allowed: !iface.connections_allowed });
      setInterfaces(prev => prev.map(i => i.id === iface.id ? res.data : i));
    } catch { toast.error("Error al cambiar interfaz"); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" /></div>;
  if (!cell) return <div className="flex flex-col items-center justify-center h-64 text-gray-400"><XCircle className="w-10 h-10 mb-3" /><p>Célula no encontrada</p></div>;

  const isFibra = cell.cell_type === "fibra" || cell.cell_type === "hifiber_ipoe";
  const isAntena = cell.cell_type === "antenas";
  const isPPPoE = cell.assignment === "pppoe_distributed";
  const isDHCP = cell.assignment === "dhcp_pool";
  const typeInfo = CELL_TYPE_LABELS[cell.cell_type];
  const assignInfo = ASSIGNMENT_LABELS[cell.assignment];

  return (
    <div className="p-6 max-w-screen-lg mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button onClick={() => navigate("/celulas")} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-3">
          <ArrowLeft className="w-4 h-4" /> Volver a Células
        </button>
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm px-6 py-5">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-xl"><Server className="w-6 h-6 text-blue-600" /></div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h1 className="text-xl font-bold text-gray-900">{cell.name}</h1>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${typeInfo?.color}`}>{typeInfo?.label}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${assignInfo?.color}`}>{assignInfo?.label}</span>
                </div>
                <div className="flex items-center gap-4 text-sm text-gray-500">
                  {cell.mikrotik_host && <span className="flex items-center gap-1"><Router className="w-3.5 h-3.5" /><span className="font-mono">{cell.mikrotik_host}</span></span>}
                  {cell.address && <span>{cell.address}</span>}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {cell.is_active
                ? <span className="flex items-center gap-1.5 text-xs font-medium text-green-700 bg-green-50 border border-green-200 px-3 py-1.5 rounded-full"><span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" /> Activa</span>
                : <span className="flex items-center gap-1.5 text-xs font-medium text-gray-500 bg-gray-50 border border-gray-200 px-3 py-1.5 rounded-full"><span className="w-1.5 h-1.5 bg-gray-400 rounded-full" /> Inactiva</span>
              }
              {cell.is_initialized
                ? <span className="flex items-center gap-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 px-3 py-1.5 rounded-full"><CheckCircle2 className="w-3.5 h-3.5" /> Inicializada</span>
                : <span className="flex items-center gap-1.5 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-full"><AlertCircle className="w-3.5 h-3.5" /> Sin inicializar</span>
              }
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-3">

        {/* 2. MikroTik */}
        <Accordion title="Equipo MikroTik" icon={Router} iconColor="text-red-600" bgColor="bg-red-50"
          open={open.mikrotik} onToggle={() => toggleAccordion("mikrotik")} badge={cell.mikrotik_host || "Sin configurar"}>
          <div className="pt-4">
            {editing === "mikrotik" ? (
              <div className="grid grid-cols-2 gap-4">
                <FieldText label="IP / Host" name="mikrotik_host" value={editForm.mikrotik_host} onChange={handleFieldChange} placeholder="201.123.45.67" className="col-span-2" />
                <FieldText label="Usuario" name="mikrotik_username_encrypted" value={editForm.mikrotik_username_encrypted} onChange={handleFieldChange} placeholder="admin" />
                <FieldPassword label="Contraseña" name="mikrotik_password_encrypted" value={editForm.mikrotik_password_encrypted} onChange={handleFieldChange} />
                <FieldNumber label="Puerto API" name="mikrotik_api_port" value={editForm.mikrotik_api_port} onChange={handleFieldChange} placeholder="8728" />
                <div className="flex items-end pb-2"><FieldToggle label="SSL (8729)" name="mikrotik_use_ssl" checked={editForm.mikrotik_use_ssl} onChange={handleFieldChange} /></div>
                <div className="col-span-2"><EditBar editing={true} onSave={saveSection} onCancel={cancelEdit} saving={saving} section="mikrotik" /></div>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-3 gap-6 mb-4">
                  <InfoRow label="Host / IP" value={cell.mikrotik_host} mono />
                  <InfoRow label="Usuario" value={cell.mikrotik_username_encrypted ? "Configurado ✓" : null} />
                  <InfoRow label="Contraseña" value={cell.mikrotik_password_encrypted ? "Configurada ✓" : null} />
                  <InfoRow label="Puerto API" value={cell.mikrotik_api_port} />
                  <InfoRow label="SSL" value={cell.mikrotik_use_ssl ? "Activado" : "Desactivado"} />
                </div>
                <TestConnectionButton cellId={id} />
                <EditBar editing={false} onEdit={startEdit} section="mikrotik" />
              </>
            )}
          </div>
        </Accordion>

        {/* 3. Red */}
        <Accordion title={isPPPoE ? "Configuración PPPoE" : isDHCP ? "Configuración DHCP Pool" : "Configuración de Red"}
          icon={isPPPoE ? Zap : Globe} iconColor={isPPPoE ? "text-blue-600" : "text-green-600"} bgColor={isPPPoE ? "bg-blue-50" : "bg-green-50"}
          open={open.red} onToggle={() => toggleAccordion("red")}>
          <div className="pt-4">
            {editing === "red" ? (
              <div className="grid grid-cols-2 gap-4">
                {isPPPoE && <FieldText label="IP servicio PPPoE" name="pppoe_service_ip" value={editForm.pppoe_service_ip} onChange={handleFieldChange} placeholder="10.0.0.1" className="col-span-2" />}
                {isDHCP && <>
                  <FieldText label="Inicio del pool" name="dhcp_pool_start" value={editForm.dhcp_pool_start} onChange={handleFieldChange} placeholder="192.168.10.100" />
                  <FieldText label="Fin del pool" name="dhcp_pool_end" value={editForm.dhcp_pool_end} onChange={handleFieldChange} placeholder="192.168.10.200" />
                  <FieldText label="Gateway" name="dhcp_gateway" value={editForm.dhcp_gateway} onChange={handleFieldChange} placeholder="192.168.10.1" />
                  <FieldText label="Interfaz MikroTik" name="dhcp_interface" value={editForm.dhcp_interface} onChange={handleFieldChange} placeholder="bridge1" />
                  <FieldText label="DNS Primario" name="dhcp_dns1" value={editForm.dhcp_dns1} onChange={handleFieldChange} placeholder="8.8.8.8" />
                  <FieldText label="DNS Secundario" name="dhcp_dns2" value={editForm.dhcp_dns2} onChange={handleFieldChange} placeholder="8.8.4.4" />
                  <FieldSelect label="Tiempo de lease" name="dhcp_lease_time" value={editForm.dhcp_lease_time} onChange={handleFieldChange}
                    options={[{value:"1h",label:"1 hora"},{value:"6h",label:"6 horas"},{value:"12h",label:"12 horas"},{value:"1d",label:"1 día"},{value:"7d",label:"7 días"}]} />
                </>}
                <div className="col-span-2"><EditBar editing={true} onSave={saveSection} onCancel={cancelEdit} saving={saving} section="red" /></div>
              </div>
            ) : (
              <>
                {isPPPoE && <div className="grid grid-cols-3 gap-6 mb-4"><InfoRow label="IP servicio PPPoE" value={cell.pppoe_service_ip} mono /></div>}
                {isDHCP && <div className="grid grid-cols-3 gap-6 mb-4">
                  <InfoRow label="Inicio del pool" value={cell.dhcp_pool_start} mono />
                  <InfoRow label="Fin del pool" value={cell.dhcp_pool_end} mono />
                  <InfoRow label="Gateway" value={cell.dhcp_gateway} mono />
                  <InfoRow label="Interfaz" value={cell.dhcp_interface} mono />
                  <InfoRow label="DNS Primario" value={cell.dhcp_dns1} mono />
                  <InfoRow label="DNS Secundario" value={cell.dhcp_dns2} mono />
                  <InfoRow label="Tiempo de lease" value={cell.dhcp_lease_time} />
                </div>}
                {!isPPPoE && !isDHCP && <p className="text-sm text-gray-400 mb-4">Asignación estática — sin configuración de pool.</p>}
                <EditBar editing={false} onEdit={startEdit} section="red" />
              </>
            )}
          </div>
        </Accordion>

        {/* 4. IPv4 ── con IP Pool integrado */}
        <Accordion title="Rango IPv4" icon={Network} iconColor="text-indigo-600" bgColor="bg-indigo-50"
          open={open.ipv4} onToggle={() => toggleAccordion("ipv4")}
          badge={cell.ipv4_range ? `${cell.ipv4_range}${cell.ipv4_mask || ""}` : null}>
          <div className="pt-4">
            {editing === "ipv4" ? (
              <div className="grid grid-cols-2 gap-4">
                <FieldText label="Rango IP" name="ipv4_range" value={editForm.ipv4_range} onChange={handleFieldChange} placeholder="192.168.10.0" />
                <FieldSelect label="Máscara" name="ipv4_mask" value={editForm.ipv4_mask} onChange={handleFieldChange}
                  options={[{value:"",label:"Seleccionar..."},...["/8","/16","/24","/25","/26","/27","/28"].map(m=>({value:m,label:m}))]} />
                <FieldText label="Host mínimo" name="ipv4_host_min" value={editForm.ipv4_host_min} onChange={handleFieldChange} placeholder="192.168.10.1" />
                <FieldText label="Host máximo" name="ipv4_host_max" value={editForm.ipv4_host_max} onChange={handleFieldChange} placeholder="192.168.10.254" />
                <div className="col-span-2"><FieldToggle label="IPv6 habilitado" name="ipv6_enabled" checked={editForm.ipv6_enabled} onChange={handleFieldChange} /></div>
                <div className="col-span-2"><EditBar editing={true} onSave={saveSection} onCancel={cancelEdit} saving={saving} section="ipv4" /></div>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-3 gap-6 mb-4">
                  <InfoRow label="Rango" value={cell.ipv4_range} mono />
                  <InfoRow label="Máscara" value={cell.ipv4_mask} mono />
                  <InfoRow label="Host mínimo" value={cell.ipv4_host_min} mono />
                  <InfoRow label="Host máximo" value={cell.ipv4_host_max} mono />
                  <InfoRow label="IPv6" value={cell.ipv6_enabled ? "Habilitado" : "Deshabilitado"} />
                </div>
                <EditBar editing={false} onEdit={startEdit} section="ipv4" />

                {/* ── IP Pool visual ── */}
                {cell.ipv4_range && <IpPoolTable cellId={id} />}
              </>
            )}
          </div>
        </Accordion>

        {/* 5. Queues */}
        <Accordion title="Queues MikroTik" icon={Zap} iconColor="text-orange-600" bgColor="bg-orange-50"
          open={open.queues} onToggle={() => toggleAccordion("queues")}>
          <div className="pt-4">
            {editing === "queues" ? (
              <div className="grid grid-cols-3 gap-4">
                <FieldText label="Queue Total" name="queue_total" value={editForm.queue_total} onChange={handleFieldChange} placeholder="100M" />
                <FieldText label="Queue Upload" name="queue_upload" value={editForm.queue_upload} onChange={handleFieldChange} placeholder="50M" />
                <FieldText label="Queue Download" name="queue_download" value={editForm.queue_download} onChange={handleFieldChange} placeholder="100M" />
                <div className="col-span-3"><EditBar editing={true} onSave={saveSection} onCancel={cancelEdit} saving={saving} section="queues" /></div>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-3 gap-6 mb-4">
                  <InfoRow label="Queue Total" value={cell.queue_total} mono />
                  <InfoRow label="Queue Upload" value={cell.queue_upload} mono />
                  <InfoRow label="Queue Download" value={cell.queue_download} mono />
                </div>
                <EditBar editing={false} onEdit={startEdit} section="queues" />
              </>
            )}
          </div>
        </Accordion>

        {/* 6. OLT */}
        {isFibra && (
          <Accordion title="Configuración OLT" icon={Cable} iconColor="text-teal-600" bgColor="bg-teal-50"
            open={open.olt} onToggle={() => toggleAccordion("olt")} badge={oltConfig ? (oltConfig.brand || "Configurada") : "Sin configurar"}>
            <div className="pt-4">
              {!oltConfig ? (
                <div className="text-center py-6 text-gray-400">
                  <Cable className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                  <p className="text-sm font-medium">OLT no configurada</p>
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-6">
                  <InfoRow label="Marca" value={oltConfig.brand} />
                  <InfoRow label="Modelo" value={oltConfig.model_name} />
                  <InfoRow label="IP OLT" value={oltConfig.olt_ip} mono />
                  <InfoRow label="Puerto SSH" value={oltConfig.ssh_port} />
                  <InfoRow label="Puerto SNMP" value={oltConfig.snmp_port} />
                  <InfoRow label="Total puertos" value={oltConfig.total_ports} />
                  <InfoRow label="SSH" value={oltConfig.ssh_username_encrypted ? "Configurado ✓" : null} />
                  <InfoRow label="SNMP" value={oltConfig.snmp_community_read ? "Configurado ✓" : null} />
                  <InfoRow label="Estado" value={oltConfig.is_online ? "🟢 Online" : "🔴 Offline"} />
                </div>
              )}
            </div>
          </Accordion>
        )}

        {/* 7. Zonas y NAPs */}
        {isFibra && (
          <Accordion title="Zonas OLT y NAPs" icon={Network} iconColor="text-blue-600" bgColor="bg-blue-50"
            open={open.zonas} onToggle={() => toggleAccordion("zonas")} badge={`${zones.length} zona${zones.length !== 1 ? "s" : ""}`}>
            <div className="pt-4">
              <div className="flex justify-end mb-4">
                <button onClick={() => setZoneModal(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-blue-600 border border-blue-200 bg-blue-50 rounded-lg hover:bg-blue-100">
                  <Plus className="w-3.5 h-3.5" /> Nueva zona
                </button>
              </div>
              {zones.length === 0 ? (
                <div className="text-center py-8 text-gray-400"><Network className="w-8 h-8 mx-auto mb-2 text-gray-300" /><p className="text-sm">Sin zonas</p></div>
              ) : (
                <div className="space-y-3">
                  {zones.map(zone => <ZoneRow key={zone.id} zone={zone} onAddNap={() => setNapModal({ open: true, zoneId: zone.id, zoneName: zone.name })} />)}
                </div>
              )}
            </div>
          </Accordion>
        )}

        {/* 8. Interfaces */}
        {isAntena && (
          <Accordion title="Interfaces MikroTik" icon={Radio} iconColor="text-purple-600" bgColor="bg-purple-50"
            open={open.interfaces} onToggle={() => toggleAccordion("interfaces")} badge={`${interfaces.length} interfaces`}>
            <div className="pt-4">
              {interfaces.length === 0 ? (
                <div className="text-center py-8 text-gray-400"><Radio className="w-8 h-8 mx-auto mb-2 text-gray-300" /><p className="text-sm">Sin interfaces sincronizadas</p></div>
              ) : interfaces.map(iface => (
                <div key={iface.id} className="flex items-center justify-between px-4 py-3 bg-gray-50 rounded-lg border border-gray-200 mb-2">
                  <div className="flex items-center gap-3">
                    <Radio className="w-4 h-4 text-purple-500" />
                    <div>
                      <p className="font-mono font-semibold text-sm text-gray-800">{iface.interface_name}</p>
                      {iface.ip_address && <p className="text-xs text-gray-400 font-mono">{iface.ip_address}/{iface.subnet} · {iface.hosts} hosts</p>}
                    </div>
                  </div>
                  <button onClick={() => toggleInterface(iface)}
                    className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-full transition-colors ${iface.connections_allowed ? "bg-green-100 text-green-700 hover:bg-green-200" : "bg-gray-100 text-gray-500 hover:bg-gray-200"}`}>
                    {iface.connections_allowed ? <><ToggleRight className="w-3.5 h-3.5" /> Permitida</> : <><ToggleLeft className="w-3.5 h-3.5" /> Desactivada</>}
                  </button>
                </div>
              ))}
            </div>
          </Accordion>
        )}

        {/* Interfaces y Red MikroTik */}
        <Accordion title="Interfaces y Red MikroTik" icon={Activity} iconColor="text-emerald-600" bgColor="bg-emerald-50"
          open={open.mikrotikLive} onToggle={() => { toggleAccordion("mikrotikLive"); if (!mkLive.loaded) loadMkLive(); }}>
          <div className="pt-4">
            <div className="flex justify-end mb-4">
              <button onClick={() => { setMkLive({ data: null, loading: false, loaded: false }); loadMkLive(); }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-600 border border-emerald-200 bg-emerald-50 rounded-lg hover:bg-emerald-100">
                <RefreshCw className="w-3 h-3" /> Sincronizar
              </button>
            </div>

            {mkLive.loading && (
              <div className="flex items-center justify-center py-8">
                <div className="w-6 h-6 border-2 border-emerald-200 border-t-emerald-600 rounded-full animate-spin mr-3" />
                <span className="text-sm text-gray-500">Leyendo MikroTik...</span>
              </div>
            )}

            {mkLive.data && (
              <div className="space-y-5">
                {/* Interfaces */}
                <div>
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2">Interfaces</p>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100">
                        {["Nombre","Tipo","MAC","MTU","Estado"].map(h => (
                          <th key={h} className="text-left text-xs font-semibold text-gray-400 pb-2 pr-4">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {mkLive.data.interfaces.map((iface, i) => (
                        <tr key={i} className="border-b border-gray-50">
                          <td className="py-2 pr-4 font-mono font-semibold text-gray-800">{iface.name}</td>
                          <td className="py-2 pr-4 text-gray-500">{iface.type || "—"}</td>
                          <td className="py-2 pr-4 font-mono text-xs text-gray-500">{iface["mac-address"] || "—"}</td>
                          <td className="py-2 pr-4 text-gray-500">{iface.mtu || "—"}</td>
                          <td className="py-2">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${iface.running === "true" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                              {iface.running === "true" ? "● UP" : "○ DOWN"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* IPs */}
                <div>
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2">Direcciones IP</p>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100">
                        {["Dirección","Red","Interfaz","Estado"].map(h => (
                          <th key={h} className="text-left text-xs font-semibold text-gray-400 pb-2 pr-4">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {mkLive.data.ips.map((ip, i) => (
                        <tr key={i} className="border-b border-gray-50">
                          <td className="py-2 pr-4 font-mono font-semibold text-blue-600">{ip.address}</td>
                          <td className="py-2 pr-4 font-mono text-gray-500">{ip.network}</td>
                          <td className="py-2 pr-4 font-mono text-gray-700">{ip.interface}</td>
                          <td className="py-2">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${ip.disabled === "false" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
                              {ip.disabled === "false" ? "Activa" : "Disabled"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Queues */}
                {mkLive.data.queues.length > 0 && (
                  <div>
                    <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2">Queues activos ({mkLive.data.queues.length})</p>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-100">
                          {["Nombre","Target","Max-Limit","Estado"].map(h => (
                            <th key={h} className="text-left text-xs font-semibold text-gray-400 pb-2 pr-4">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {mkLive.data.queues.map((q, i) => (
                          <tr key={i} className="border-b border-gray-50">
                            <td className="py-2 pr-4 font-mono text-xs text-gray-800">{q.name}</td>
                            <td className="py-2 pr-4 font-mono text-xs text-gray-500">{q.target}</td>
                            <td className="py-2 pr-4 font-mono text-xs text-blue-600">{q["max-limit"]}</td>
                            <td className="py-2">
                              <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${q.disabled === "false" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
                                {q.disabled === "false" ? "Activo" : "Disabled"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* PPPoE Secrets */}
                {mkLive.data.secrets.length > 0 && (
                  <div>
                    <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2">PPPoE Secrets ({mkLive.data.secrets.length})</p>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-100">
                          {["Usuario","Perfil","IP","Estado"].map(h => (
                            <th key={h} className="text-left text-xs font-semibold text-gray-400 pb-2 pr-4">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {mkLive.data.secrets.map((s, i) => (
                          <tr key={i} className="border-b border-gray-50">
                            <td className="py-2 pr-4 font-mono font-semibold text-gray-800">{s.name}</td>
                            <td className="py-2 pr-4 text-gray-500">{s.profile}</td>
                            <td className="py-2 pr-4 font-mono text-xs text-blue-600">{s["remote-address"] || "—"}</td>
                            <td className="py-2">
                              <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${s.disabled === "false" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
                                {s.disabled === "false" ? "Activo" : "Disabled"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {!mkLive.loading && !mkLive.data && (
              <div className="text-center py-8 text-gray-400">
                <Activity className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                <p className="text-sm">Abre este panel para leer el MikroTik en tiempo real</p>
              </div>
            )}
          </div>
        </Accordion>

        {/* 9. Planes */}
        <Accordion title="Planes Asignados" icon={Wifi} open={open.planes} onToggle={() => toggleAccordion("planes")} badge={`${plans.length} disponibles`}>
          <div className="pt-4">
            <p className="text-sm text-gray-500 bg-gray-50 rounded-lg px-4 py-3 border border-gray-200">
              💡 Para asignar planes a esta célula, edítalos desde el módulo <strong>Planes de Servicio</strong>.
            </p>
          </div>
        </Accordion>
      </div>

      <ZoneModal open={zoneModal} cellId={id} onClose={() => setZoneModal(false)} onSaved={() => { setZoneModal(false); fetchAll(); }} />
      <NapModal open={napModal.open} zoneId={napModal.zoneId} zoneName={napModal.zoneName}
        onClose={() => setNapModal({ open: false, zoneId: null, zoneName: "" })}
        onSaved={() => { setNapModal({ open: false, zoneId: null, zoneName: "" }); fetchAll(); }} />
    </div>
  );
}
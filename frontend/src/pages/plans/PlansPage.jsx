/**
 * PlansPage.jsx
 * NetKeeper - Módulo Planes de Servicio
 * CRUD completo: listar, crear, editar, desactivar
 * Endpoint: /api/plans/
 */
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../api/axios";
import toast from "react-hot-toast";
import {
  Plus, Search, Pencil, Trash2, Wifi, ChevronDown, ChevronUp,
  ArrowUpDown, ArrowUp, ArrowDown, ToggleLeft, ToggleRight,
  Zap, DollarSign, Tag, Settings, X, Check, AlertTriangle
} from "lucide-react";

// ─── Constantes ──────────────────────────────────────────────────────────────
const PRIORITY_OPTIONS = ["Residencial", "Empresarial", "Premium", "Básico", "Escolar"];
const PLAN_TYPE_LABELS = { con_plan: "Con Plan", prepago: "Prepago" };
const PRIORITY_COLORS = {
  Residencial: "bg-blue-100 text-blue-700",
  Empresarial:  "bg-purple-100 text-purple-700",
  Premium:      "bg-yellow-100 text-yellow-800",
  Básico:       "bg-gray-100 text-gray-600",
  Escolar:      "bg-green-100 text-green-700",
};

// ─── Componentes de input FUERA del componente principal (evita pérdida de foco) ─
const TextInput = ({ label, name, value, onChange, required, placeholder, className = "" }) => (
  <div className={className}>
    <label className="block text-sm font-semibold text-gray-700 mb-1">
      {label} {required && <span className="text-red-500">*</span>}
    </label>
    <input
      type="text"
      name={name}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
    />
  </div>
);

const NumberInput = ({ label, name, value, onChange, required, min, placeholder, prefix, className = "" }) => (
  <div className={className}>
    <label className="block text-sm font-semibold text-gray-700 mb-1">
      {label} {required && <span className="text-red-500">*</span>}
    </label>
    <div className="relative">
      {prefix && (
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm font-medium">{prefix}</span>
      )}
      <input
        type="number"
        name={name}
        value={value}
        onChange={onChange}
        min={min}
        placeholder={placeholder}
        className={`w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${prefix ? "pl-7" : ""}`}
      />
    </div>
  </div>
);

const SelectInput = ({ label, name, value, onChange, options, className = "" }) => (
  <div className={className}>
    <label className="block text-sm font-semibold text-gray-700 mb-1">{label}</label>
    <select
      name={name}
      value={value}
      onChange={onChange}
      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
    >
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  </div>
);

const SpeedInput = ({ label, nameValue, nameUnit, value, unit, onChange, required, className = "" }) => (
  <div className={className}>
    <label className="block text-sm font-semibold text-gray-700 mb-1">
      {label} {required && <span className="text-red-500">*</span>}
    </label>
    <div className="flex gap-2">
      <input
        type="number"
        name={nameValue}
        value={value}
        onChange={onChange}
        min="1"
        placeholder="ej: 20"
        className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <select
        name={nameUnit}
        value={unit}
        onChange={onChange}
        className="w-20 border border-gray-300 rounded-lg px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
      >
        <option value="MB">MB</option>
        <option value="KB">KB</option>
        <option value="GB">GB</option>
      </select>
    </div>
  </div>
);

const ToggleInput = ({ label, name, checked, onChange, description }) => (
  <label className="flex items-center gap-3 cursor-pointer group">
    <div className="relative">
      <input type="checkbox" name={name} checked={checked} onChange={onChange} className="sr-only" />
      <div className={`w-10 h-5 rounded-full transition-colors ${checked ? "bg-blue-600" : "bg-gray-300"}`} />
      <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${checked ? "translate-x-5" : ""}`} />
    </div>
    <div>
      <span className="text-sm font-medium text-gray-700">{label}</span>
      {description && <p className="text-xs text-gray-400">{description}</p>}
    </div>
  </label>
);

// ─── Estado inicial del formulario ───────────────────────────────────────────
const EMPTY_FORM = {
  folio: "", name: "", plan_type: "con_plan", traffic_control: "Router Mikrotik",
  price: "", priority: "Residencial",
  reconnection_fee: false, restrict_by_tags: false, tags: "",
  upload_speed: "", upload_unit: "MB",
  download_speed: "", download_unit: "MB",
  burst_limit_upload: "", burst_limit_download: "",
  burst_threshold_upload: "", burst_threshold_download: "",
  burst_time_upload: "", burst_time_download: "",
};

// ─── Modal Crear/Editar ───────────────────────────────────────────────────────
const PlanModal = ({ open, onClose, onSaved, editPlan }) => {
  const [form, setForm] = useState(EMPTY_FORM);
  const [showBurst, setShowBurst] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (editPlan) {
      // Extraer solo el número de la velocidad (viene como "10M" → "10")
      const extractNum = (v) => v ? v.replace(/[^0-9.]/g, "") : "";
      const extractUnit = (v) => v ? v.replace(/[0-9.]/g, "") || "MB" : "MB";
      setForm({
        folio: editPlan.folio || "",
        name: editPlan.name || "",
        plan_type: editPlan.plan_type || "con_plan",
        traffic_control: editPlan.traffic_control || "Router Mikrotik",
        price: editPlan.price || "",
        priority: editPlan.priority || "Residencial",
        reconnection_fee: editPlan.reconnection_fee || false,
        restrict_by_tags: editPlan.restrict_by_tags || false,
        tags: editPlan.tags || "",
        upload_speed: extractNum(editPlan.upload_speed),
        upload_unit: editPlan.upload_unit || extractUnit(editPlan.upload_speed),
        download_speed: extractNum(editPlan.download_speed),
        download_unit: editPlan.download_unit || extractUnit(editPlan.download_speed),
        burst_limit_upload: editPlan.burst_limit_upload || "",
        burst_limit_download: editPlan.burst_limit_download || "",
        burst_threshold_upload: editPlan.burst_threshold_upload || "",
        burst_threshold_download: editPlan.burst_threshold_download || "",
        burst_time_upload: editPlan.burst_time_upload || "",
        burst_time_download: editPlan.burst_time_download || "",
      });
      const hasBurst = !!(editPlan.burst_limit_upload || editPlan.burst_limit_download);
      setShowBurst(hasBurst);
    } else {
      setForm(EMPTY_FORM);
      setShowBurst(false);
    }
  }, [open, editPlan]);

  const handleChange = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    setForm(prev => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  }, []);

  const buildPayload = () => {
    // Concatenar velocidad + unidad al formato que espera el backend ("10M", "512K")
    const fmtSpeed = (val, unit) => val ? `${val}${unit === "MB" ? "M" : unit === "KB" ? "K" : "G"}` : "";
    return {
      folio: form.folio || null,
      name: form.name,
      plan_type: form.plan_type,
      traffic_control: form.traffic_control,
      price: parseFloat(form.price),
      priority: form.priority,
      reconnection_fee: form.reconnection_fee,
      restrict_by_tags: form.restrict_by_tags,
      tags: form.tags || null,
      upload_speed: fmtSpeed(form.upload_speed, form.upload_unit),
      download_speed: fmtSpeed(form.download_speed, form.download_unit),
      upload_unit: form.upload_unit,
      download_unit: form.download_unit,
      burst_limit_upload: showBurst && form.burst_limit_upload ? fmtSpeed(form.burst_limit_upload, form.upload_unit) : null,
      burst_limit_download: showBurst && form.burst_limit_download ? fmtSpeed(form.burst_limit_download, form.download_unit) : null,
      burst_threshold_upload: showBurst && form.burst_threshold_upload ? fmtSpeed(form.burst_threshold_upload, form.upload_unit) : null,
      burst_threshold_download: showBurst && form.burst_threshold_download ? fmtSpeed(form.burst_threshold_download, form.download_unit) : null,
      burst_time_upload: showBurst && form.burst_time_upload ? form.burst_time_upload : null,
      burst_time_download: showBurst && form.burst_time_download ? form.burst_time_download : null,
    };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return toast.error("El nombre es obligatorio");
    if (!form.upload_speed || !form.download_speed) return toast.error("Las velocidades son obligatorias");
    if (!form.price || parseFloat(form.price) <= 0) return toast.error("El precio debe ser mayor a 0");

    setSaving(true);
    try {
      const payload = buildPayload();
      if (editPlan) {
        await api.patch(`/plans/${editPlan.id}`, payload);
        toast.success("Plan actualizado");
      } else {
        await api.post("/plans/", payload);
        toast.success("Plan creado");
      }
      onSaved();
    } catch (err) {
      const msg = err.response?.data?.detail || "Error al guardar";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-8 py-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Wifi className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">
                {editPlan ? "Editar Plan" : "Nuevo Plan de Servicio"}
              </h2>
              <p className="text-sm text-gray-500">{editPlan ? `ID: ${editPlan.id}` : "Completa los datos del plan"}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-8 py-6 space-y-6">
          {/* Sección: Datos generales */}
          <div>
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wide mb-4 flex items-center gap-2">
              <Tag className="w-4 h-4" /> Datos generales
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <TextInput label="Folio" name="folio" value={form.folio} onChange={handleChange} placeholder="ej: P-001" />
              <SelectInput label="Tipo de plan" name="plan_type" value={form.plan_type} onChange={handleChange}
                options={[{ value: "con_plan", label: "Con Plan" }, { value: "prepago", label: "Prepago" }]} />
              <TextInput label="Nombre del plan" name="name" value={form.name} onChange={handleChange}
                required placeholder="ej: Residencial 20MB" className="col-span-2" />
              <NumberInput label="Precio mensual" name="price" value={form.price} onChange={handleChange}
                required min="0" placeholder="299.00" prefix="$" />
              <SelectInput label="Prioridad" name="priority" value={form.priority} onChange={handleChange}
                options={PRIORITY_OPTIONS.map(p => ({ value: p, label: p }))} />
              <TextInput label="Control de tráfico" name="traffic_control" value={form.traffic_control}
                onChange={handleChange} placeholder="Router Mikrotik" />
            </div>
          </div>

          {/* Sección: Velocidades */}
          <div>
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wide mb-4 flex items-center gap-2">
              <Zap className="w-4 h-4" /> Velocidades
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <SpeedInput label="Bajada (Download)" nameValue="download_speed" nameUnit="download_unit"
                value={form.download_speed} unit={form.download_unit} onChange={handleChange} required />
              <SpeedInput label="Subida (Upload)" nameValue="upload_speed" nameUnit="upload_unit"
                value={form.upload_speed} unit={form.upload_unit} onChange={handleChange} required />
            </div>
          </div>

          {/* Sección: Burst (colapsable) */}
          <div className="border border-gray-200 rounded-xl overflow-hidden">
            <button type="button" onClick={() => setShowBurst(b => !b)}
              className="w-full flex items-center justify-between px-5 py-3 bg-gray-50 hover:bg-gray-100 transition-colors">
              <span className="text-sm font-bold text-gray-600 flex items-center gap-2">
                <Zap className="w-4 h-4 text-orange-500" /> Configuración Burst (MikroTik)
              </span>
              <span className="flex items-center gap-2">
                {showBurst
                  ? <><span className="text-xs text-blue-600 font-medium">Activado</span><ChevronUp className="w-4 h-4 text-gray-400" /></>
                  : <><span className="text-xs text-gray-400">Desactivado</span><ChevronDown className="w-4 h-4 text-gray-400" /></>
                }
              </span>
            </button>
            {showBurst && (
              <div className="px-5 py-4 space-y-4 bg-white">
                <p className="text-xs text-gray-500 bg-orange-50 border border-orange-200 rounded-lg px-3 py-2">
                  💡 El burst permite velocidad adicional por tiempo limitado. Se aplica en MikroTik Queue.
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <TextInput label="Burst Bajada" name="burst_limit_download" value={form.burst_limit_download}
                    onChange={handleChange} placeholder="ej: 30 (en MB)" />
                  <TextInput label="Burst Subida" name="burst_limit_upload" value={form.burst_limit_upload}
                    onChange={handleChange} placeholder="ej: 15 (en MB)" />
                  <TextInput label="Umbral Bajada" name="burst_threshold_download" value={form.burst_threshold_download}
                    onChange={handleChange} placeholder="ej: 15 (en MB)" />
                  <TextInput label="Umbral Subida" name="burst_threshold_upload" value={form.burst_threshold_upload}
                    onChange={handleChange} placeholder="ej: 8 (en MB)" />
                  <TextInput label="Tiempo Burst Bajada (seg)" name="burst_time_download" value={form.burst_time_download}
                    onChange={handleChange} placeholder="ej: 8" />
                  <TextInput label="Tiempo Burst Subida (seg)" name="burst_time_upload" value={form.burst_time_upload}
                    onChange={handleChange} placeholder="ej: 8" />
                </div>
              </div>
            )}
          </div>

          {/* Sección: Opciones */}
          <div>
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wide mb-4 flex items-center gap-2">
              <Settings className="w-4 h-4" /> Opciones
            </h3>
            <div className="space-y-3 mb-4">
              <ToggleInput label="Cargo por reconexión" name="reconnection_fee" checked={form.reconnection_fee}
                onChange={handleChange} description="Aplica cargo al reactivar servicio suspendido" />
              <ToggleInput label="Restringir por etiquetas" name="restrict_by_tags" checked={form.restrict_by_tags}
                onChange={handleChange} description="Solo asignar a equipos con las etiquetas indicadas" />
            </div>
            {form.restrict_by_tags && (
              <TextInput label="Etiquetas" name="tags" value={form.tags} onChange={handleChange}
                placeholder='ej: "Solo UBIQUITI", "Solo TP-Link"' />
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
            <button type="button" onClick={onClose}
              className="px-6 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
              Cancelar
            </button>
            <button type="submit" disabled={saving}
              className="px-6 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-2">
              {saving ? (
                <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Guardando...</>
              ) : (
                <><Check className="w-4 h-4" />{editPlan ? "Guardar cambios" : "Crear plan"}</>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ─── Modal Confirmar Desactivar ───────────────────────────────────────────────
const DeleteModal = ({ open, plan, onClose, onConfirm, loading }) => {
  if (!open || !plan) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
        <div className="flex items-center gap-4 mb-4">
          <div className="p-3 bg-red-100 rounded-full">
            <AlertTriangle className="w-6 h-6 text-red-600" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900">Desactivar plan</h3>
            <p className="text-sm text-gray-500">Esta acción se puede revertir</p>
          </div>
        </div>
        <p className="text-gray-700 mb-2">
          ¿Desactivar el plan <span className="font-semibold">"{plan.name}"</span>?
        </p>
        {plan.connection_count > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-4">
            <p className="text-sm text-amber-800 font-medium">
              ⚠️ Este plan tiene {plan.connection_count} conexiones activas. No se puede desactivar.
            </p>
          </div>
        )}
        <p className="text-sm text-gray-500 mb-6">
          Los planes desactivados no aparecen al crear nuevas conexiones.
        </p>
        <div className="flex justify-end gap-3">
          <button onClick={onClose}
            className="px-5 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">
            Cancelar
          </button>
          <button onClick={onConfirm} disabled={loading || plan.connection_count > 0}
            className="px-5 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center gap-2">
            {loading ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Trash2 className="w-4 h-4" />}
            Desactivar
          </button>
        </div>
      </div>
    </div>
  );
};

// ─── Componente principal ─────────────────────────────────────────────────────
export default function PlansPage() {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterPriority, setFilterPriority] = useState("");
  const [filterActive, setFilterActive] = useState("true");
  const [sortField, setSortField] = useState("id");
  const [sortDir, setSortDir] = useState("asc");

  // Modales
  const [modalOpen, setModalOpen] = useState(false);
  const [editPlan, setEditPlan] = useState(null);
  const [deleteModal, setDeleteModal] = useState({ open: false, plan: null });
  const [deleting, setDeleting] = useState(false);

  useEffect(() => { window.scrollTo(0, 0); }, []);
  useEffect(() => { fetchPlans(); }, [filterActive]);

  const fetchPlans = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterActive !== "") params.is_active = filterActive;
      const res = await api.get("/plans/", { params });


      setPlans(res.data);
    } catch {
      toast.error("Error al cargar planes");
    } finally {
      setLoading(false);
    }
  };

  // Filtrado y ordenamiento local
  const filtered = plans
    .filter(p => {
      const q = search.toLowerCase();
      if (q && !p.name.toLowerCase().includes(q) && !(p.folio || "").toLowerCase().includes(q)) return false;
      if (filterType && p.plan_type !== filterType) return false;
      if (filterPriority && p.priority !== filterPriority) return false;
      return true;
    })
    .sort((a, b) => {
      let va = a[sortField], vb = b[sortField];
      if (typeof va === "string") va = va.toLowerCase();
      if (typeof vb === "string") vb = vb.toLowerCase();
      if (va < vb) return sortDir === "asc" ? -1 : 1;
      if (va > vb) return sortDir === "asc" ? 1 : -1;
      return 0;
    });

  const handleSort = (field) => {
    if (sortField === field) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortField(field); setSortDir("asc"); }
  };

  const SortIcon = ({ field }) => {
    if (sortField !== field) return <ArrowUpDown className="w-3.5 h-3.5 text-gray-300" />;
    return sortDir === "asc"
      ? <ArrowUp className="w-3.5 h-3.5 text-blue-500" />
      : <ArrowDown className="w-3.5 h-3.5 text-blue-500" />;
  };

  const openCreate = () => { setEditPlan(null); setModalOpen(true); };
  const openEdit = (plan) => { setEditPlan(plan); setModalOpen(true); };
  const handleSaved = () => { setModalOpen(false); fetchPlans(); };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await api.delete(`/plans/${deleteModal.plan.id}`);
      toast.success("Plan desactivado");
      setDeleteModal({ open: false, plan: null });
      fetchPlans();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al desactivar");
    } finally {
      setDeleting(false);
    }
  };

  // Formatear velocidad para mostrar legible
  const fmtSpeed = (v) => v || "—";

  // Estadísticas rápidas
  const stats = {
    total: plans.length,
    active: plans.filter(p => p.is_active).length,
    connections: plans.reduce((s, p) => s + (p.connection_count || 0), 0),
    cells: [...new Set(plans.flatMap(p => p.cell_count || 0))].reduce((a, b) => a + b, 0),
  };

  return (
    <div className="p-6">
      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Planes de Servicio</h1>
          <p className="text-sm text-gray-500 mt-0.5">Gestiona los planes de internet del tenant</p>
        </div>
        <button onClick={openCreate}
          className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 shadow-sm transition-colors">
          <Plus className="w-4 h-4" /> Nuevo Plan
        </button>
      </div>

      {/* ── Stats Cards ── */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total planes", value: stats.total, icon: Wifi, color: "blue" },
          { label: "Planes activos", value: stats.active, icon: ToggleRight, color: "green" },
          { label: "Conexiones activas", value: stats.connections, icon: Zap, color: "purple" },
          { label: "Planes inactivos", value: stats.total - stats.active, icon: ToggleLeft, color: "gray" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-500">{label}</span>
              <div className={`p-1.5 rounded-lg bg-${color}-100`}>
                <Icon className={`w-3.5 h-3.5 text-${color}-600`} />
              </div>
            </div>
            <p className="text-2xl font-bold text-gray-900">{value}</p>
          </div>
        ))}
      </div>

      {/* ── Filtros ── */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 mb-4">
        <div className="flex flex-wrap gap-3 items-center">
          {/* Búsqueda */}
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por nombre o folio..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Tipo */}
          <select value={filterType} onChange={e => setFilterType(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white min-w-36">
            <option value="">Todos los tipos</option>
            <option value="con_plan">Con Plan</option>
            <option value="prepago">Prepago</option>
          </select>

          {/* Prioridad */}
          <select value={filterPriority} onChange={e => setFilterPriority(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white min-w-36">
            <option value="">Todas las prioridades</option>
            {PRIORITY_OPTIONS.map(p => <option key={p} value={p}>{p}</option>)}
          </select>

          {/* Estado */}
          <select value={filterActive} onChange={e => setFilterActive(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white min-w-32">
            <option value="true">Activos</option>
            <option value="false">Inactivos</option>
            <option value="">Todos</option>
          </select>

          {/* Limpiar */}
          {(search || filterType || filterPriority || filterActive !== "true") && (
            <button onClick={() => { setSearch(""); setFilterType(""); setFilterPriority(""); setFilterActive("true"); fetchPlans(); }}
              className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-500 hover:text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">
              <X className="w-3.5 h-3.5" /> Limpiar
            </button>
          )}

          <span className="ml-auto text-xs text-gray-400 font-medium">{filtered.length} plan{filtered.length !== 1 ? "es" : ""}</span>
        </div>
      </div>

      {/* ── Tabla ── */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-gray-400">
            <Wifi className="w-10 h-10 mb-3 text-gray-300" />
            <p className="font-medium">No hay planes</p>
            <p className="text-sm mt-1">Crea el primer plan de servicio</p>
            <button onClick={openCreate} className="mt-4 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              Crear plan
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  {[
                    { label: "Folio / Nombre", field: "name" },
                    { label: "Tipo", field: "plan_type" },
                    { label: "Bajada / Subida", field: "download_speed" },
                    { label: "Precio", field: "price" },
                    { label: "Prioridad", field: "priority" },
                    { label: "Conexiones", field: "connection_count" },
                    { label: "Células", field: "cell_count" },
                    { label: "Estado", field: "is_active" },
                    { label: "Acciones", field: null },
                  ].map(({ label, field }) => (
                    <th key={label}
                      onClick={() => field && handleSort(field)}
                      className={`px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide whitespace-nowrap ${field ? "cursor-pointer hover:bg-gray-100 select-none" : ""}`}>
                      <span className="flex items-center gap-1.5">
                        {label}
                        {field && <SortIcon field={field} />}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map(plan => (
                  <tr key={plan.id} className="hover:bg-gray-50 transition-colors group">
                    {/* Folio / Nombre */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-blue-50 rounded-lg group-hover:bg-blue-100 transition-colors">
                          <Wifi className="w-3.5 h-3.5 text-blue-600" />
                        </div>
                        <div>
                          <p className="font-semibold text-gray-900">{plan.name}</p>
                          {plan.folio && <p className="text-xs text-gray-400">{plan.folio}</p>}
                        </div>
                      </div>
                    </td>

                    {/* Tipo */}
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        plan.plan_type === "con_plan" ? "bg-blue-50 text-blue-700" : "bg-green-50 text-green-700"
                      }`}>
                        {PLAN_TYPE_LABELS[plan.plan_type]}
                      </span>
                    </td>

                    {/* Velocidades */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <ArrowDown className="w-3 h-3 text-blue-500" />
                        <span className="font-mono font-semibold text-gray-800">{fmtSpeed(plan.download_speed)}</span>
                        <span className="text-gray-300 mx-1">/</span>
                        <ArrowUp className="w-3 h-3 text-green-500" />
                        <span className="font-mono font-semibold text-gray-800">{fmtSpeed(plan.upload_speed)}</span>
                      </div>
                    </td>

                    {/* Precio */}
                    <td className="px-4 py-3">
                      <span className="font-bold text-gray-900">
                        ${Number(plan.price).toLocaleString("es-MX", { minimumFractionDigits: 2 })}
                      </span>
                    </td>

                    {/* Prioridad */}
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${PRIORITY_COLORS[plan.priority] || "bg-gray-100 text-gray-600"}`}>
                        {plan.priority}
                      </span>
                    </td>

                    {/* Conexiones */}
                    <td className="px-4 py-3">
                      <span className={`font-semibold ${plan.connection_count > 0 ? "text-gray-900" : "text-gray-400"}`}>
                        {plan.connection_count}
                      </span>
                    </td>

                    {/* Células */}
                    <td className="px-4 py-3">
                      <span className={`font-semibold ${plan.cell_count > 0 ? "text-gray-900" : "text-gray-400"}`}>
                        {plan.cell_count}
                      </span>
                    </td>

                    {/* Estado */}
                    <td className="px-4 py-3">
                      {plan.is_active
                        ? <span className="flex items-center gap-1.5 text-xs font-medium text-green-700"><span className="w-1.5 h-1.5 bg-green-500 rounded-full" />Activo</span>
                        : <span className="flex items-center gap-1.5 text-xs font-medium text-gray-400"><span className="w-1.5 h-1.5 bg-gray-400 rounded-full" />Inactivo</span>
                      }
                    </td>

                    {/* Acciones */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button onClick={() => openEdit(plan)} title="Editar"
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button onClick={() => setDeleteModal({ open: true, plan })} title="Desactivar"
                          disabled={!plan.is_active}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
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

      {/* ── Modales ── */}
      <PlanModal open={modalOpen} onClose={() => setModalOpen(false)} onSaved={handleSaved} editPlan={editPlan} />
      <DeleteModal open={deleteModal.open} plan={deleteModal.plan}
        onClose={() => setDeleteModal({ open: false, plan: null })}
        onConfirm={handleDelete} loading={deleting} />
    </div>
  );
}
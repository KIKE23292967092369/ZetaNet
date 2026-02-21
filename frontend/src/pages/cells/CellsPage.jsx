/**
 * CellsPage.jsx
 * NetKeeper - Módulo Células
 * Wizard: General → MikroTik → [OLT] → [DHCP] → Resumen
 */
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../api/axios";
import toast from "react-hot-toast";
import {
  Plus, Search, Radio, Wifi, Zap, Server,
  ArrowUpDown, ArrowUp, ArrowDown, X, ChevronRight,
  CheckCircle2, AlertCircle, Network, Router,
  ChevronLeft, Eye, EyeOff, ChevronDown, Cable,
} from "lucide-react";

const CELL_TYPE_LABELS = {
  fibra:        { label: "Fibra PPPoE", color: "bg-blue-100 text-blue-700",    icon: Wifi  },
  antenas:      { label: "Antenas",     color: "bg-purple-100 text-purple-700", icon: Radio },
  hifiber_ipoe: { label: "Fibra IPoE",  color: "bg-cyan-100 text-cyan-700",    icon: Zap   },
};
const ASSIGNMENT_LABELS = {
  pppoe_distributed: { label: "PPPoE",    color: "bg-blue-50 text-blue-600"     },
  static_addressing:  { label: "Estático", color: "bg-orange-50 text-orange-600" },
  dhcp_pool:          { label: "DHCP",    color: "bg-green-50 text-green-600"   },
};

const getStoredInterfaces = () => {
  try {
    const raw = localStorage.getItem("netkeeper_mk_interfaces");
    if (!raw) return null;
    return JSON.parse(raw);
  } catch { return null; }
};

const getCidrFromIface = (iface) => {
  if (!iface?.ips?.length) return null;
  return iface.ips[0]?.address || null;
};

const parseCidr = (cidr) => {
  if (!cidr) return null;
  try {
    const [ip, prefix] = cidr.split("/");
    const parts   = ip.split(".").map(Number);
    const red     = [...parts.slice(0, 3), 0].join(".");
    const mascara = `/${prefix}`;
    const hostMin = [...parts.slice(0, 3), 1].join(".");
    const total   = Math.pow(2, 32 - parseInt(prefix)) - 2;
    const hostMax = [...parts.slice(0, 3), Math.min(total, 254)].join(".");
    return { red, mascara, hostMin, hostMax };
  } catch { return null; }
};

const Field = ({ label, required, children, className = "" }) => (
  <div className={className}>
    <label className="block text-xs font-semibold text-gray-600 mb-1.5">
      {label} {required && <span className="text-red-500">*</span>}
    </label>
    {children}
  </div>
);

const TInput = ({ name, value, onChange, placeholder, mono, type = "text", disabled }) => (
  <input type={type} name={name} value={value} onChange={onChange} placeholder={placeholder}
    disabled={disabled}
    className={`w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400 ${mono ? "font-mono" : ""}`} />
);

const SInput = ({ name, value, onChange, options }) => (
  <select name={name} value={value} onChange={onChange}
    className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
    {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
  </select>
);

const Toggle = ({ label, name, checked, onChange, desc }) => (
  <label className="flex items-center gap-3 cursor-pointer">
    <div className="relative">
      <input type="checkbox" name={name} checked={checked} onChange={onChange} className="sr-only" />
      <div className={`w-10 h-5 rounded-full transition-colors ${checked ? "bg-blue-600" : "bg-gray-300"}`} />
      <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${checked ? "translate-x-5" : ""}`} />
    </div>
    <div>
      <span className="text-sm font-medium text-gray-700">{label}</span>
      {desc && <p className="text-xs text-gray-400">{desc}</p>}
    </div>
  </label>
);

const InterfaceDropdown = ({ value, onChange, storedMk, onClearStorage }) => {
  const [open, setOpen] = useState(false);
  if (!storedMk) {
    return (
      <>
        <TInput name="mikrotik_interface" value={value} onChange={onChange}
          placeholder="ej: bridge1, ether2" mono />
        <p className="text-xs text-amber-600 mt-1.5">
          💡 Conecta el MikroTik en <strong>Nodos de Red</strong> para seleccionar la interfaz automáticamente.
        </p>
      </>
    );
  }
  const withIp    = storedMk.interfaces.filter(i => i.ips?.length > 0);
  const withoutIp = storedMk.interfaces.filter(i => !i.ips?.length);
  const selected  = storedMk.interfaces.find(i => i.name === value);
  const cidr      = selected ? getCidrFromIface(selected) : null;
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-green-600 font-medium flex items-center gap-1">
          <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
          Cargadas desde {storedMk.host}
        </span>
        <button type="button" onClick={onClearStorage} className="text-xs text-gray-400 hover:text-red-500 transition-colors">Limpiar</button>
      </div>
      <div className="relative">
        <button type="button" onClick={() => setOpen(v => !v)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm text-left flex items-center justify-between focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white hover:border-blue-400 transition-colors">
          {value ? (
            <span className="font-mono font-semibold text-gray-800">
              {value}{cidr && <span className="text-indigo-500 ml-2 font-normal">{cidr}</span>}
            </span>
          ) : <span className="text-gray-400">Selecciona una interfaz...</span>}
          <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`} />
        </button>
        {open && (
          <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
            {withIp.length > 0 && (<>
              <div className="px-3 py-1.5 bg-gray-50 border-b border-gray-100">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Con IP configurada</span>
              </div>
              {withIp.map(iface => {
                const ifaceCidr = getCidrFromIface(iface);
                return (
                  <button key={iface.name} type="button"
                    onClick={() => { onChange({ target: { name: "mikrotik_interface", value: iface.name } }); setOpen(false); }}
                    className={`w-full px-4 py-3 text-left hover:bg-blue-50 transition-colors flex items-center justify-between ${value === iface.name ? "bg-blue-50 border-l-2 border-blue-500" : ""}`}>
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${iface.running ? "bg-green-500" : "bg-gray-300"}`} />
                      <span className="font-mono font-semibold text-gray-800">{iface.name}</span>
                      <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">{iface.type || "ether"}</span>
                    </div>
                    {ifaceCidr && <span className="font-mono text-sm text-indigo-600 font-semibold">{ifaceCidr}</span>}
                  </button>
                );
              })}
            </>)}
            {withoutIp.length > 0 && (<>
              <div className="px-3 py-1.5 bg-gray-50 border-t border-b border-gray-100">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Sin IP (WAN / trunk)</span>
              </div>
              {withoutIp.map(iface => (
                <button key={iface.name} type="button"
                  onClick={() => { onChange({ target: { name: "mikrotik_interface", value: iface.name } }); setOpen(false); }}
                  className={`w-full px-4 py-2.5 text-left hover:bg-gray-50 transition-colors flex items-center gap-2 ${value === iface.name ? "bg-blue-50 border-l-2 border-blue-500" : ""}`}>
                  <span className={`w-2 h-2 rounded-full ${iface.running ? "bg-green-400" : "bg-gray-300"}`} />
                  <span className="font-mono text-sm text-gray-500">{iface.name}</span>
                  <span className="text-xs text-gray-300 ml-auto">{iface.type || "—"}</span>
                </button>
              ))}
            </>)}
          </div>
        )}
      </div>
    </div>
  );
};

const getSuggestedAssignment = (t) => {
  if (t === "fibra")        return "pppoe_distributed";
  if (t === "hifiber_ipoe") return "dhcp_pool";
  return "static_addressing";
};

const getAssignmentOptions = (t) => {
  if (t === "fibra")        return [{ value: "pppoe_distributed", label: "PPPoE Distribuido" }, { value: "dhcp_pool", label: "DHCP Pool (IPoE)" }];
  if (t === "antenas")      return [{ value: "static_addressing", label: "Estático" }, { value: "dhcp_pool", label: "DHCP Pool" }];
  if (t === "hifiber_ipoe") return [{ value: "dhcp_pool", label: "DHCP Pool" }];
  return [];
};

// Modelos OLT soportados
const OLT_MODELS = [
  { value: "ZXA10 C300", label: "ZXA10 C300 (ZTE)",  brand: "zte",  ports: 16 },
  { value: "ZXA10 C320", label: "ZXA10 C320 (ZTE)",  brand: "zte",  ports: 32 },
  { value: "ZXA10 C600", label: "ZXA10 C600 (ZTE)",  brand: "zte",  ports: 64 },
  { value: "VSOL V1600", label: "VSOL V1600 (VSOL)", brand: "vsol", ports: 16 },
  { value: "VSOL V2800", label: "VSOL V2800 (VSOL)", brand: "vsol", ports: 32 },
];

const EMPTY = {
  name: "", cell_type: "fibra", assignment: "pppoe_distributed",
  address: "", range_meters: "", use_pcq: false,
  mikrotik_host: "", mikrotik_username_encrypted: "",
  mikrotik_password_encrypted: "", mikrotik_api_port: "8728",
  mikrotik_use_ssl: false, mikrotik_interface: "",
  pppoe_service_ip: "",
  dhcp_pool_start: "", dhcp_pool_end: "", dhcp_gateway: "",
  dhcp_dns1: "8.8.8.8", dhcp_dns2: "8.8.4.4",
  dhcp_lease_time: "1d", dhcp_interface: "",
  ipv4_range: "", ipv4_mask: "", ipv4_host_min: "", ipv4_host_max: "",
  // OLT
  olt_model: "ZXA10 C300", olt_brand: "zte", olt_total_ports: "16",
  olt_ip: "", olt_ssh_port: "8022", olt_ssh_username: "", olt_ssh_password: "",
};

const StepIndicator = ({ current, steps }) => (
  <div className="flex items-center gap-2 mb-6">
    {steps.map((s, i) => (
      <div key={i} className="flex items-center gap-2">
        <div className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold transition-all
          ${i < current ? "bg-green-500 text-white" : i === current ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-400"}`}>
          {i < current ? <CheckCircle2 className="w-4 h-4" /> : i + 1}
        </div>
        <span className={`text-xs font-medium ${i === current ? "text-blue-600" : i < current ? "text-green-600" : "text-gray-400"}`}>{s}</span>
        {i < steps.length - 1 && <div className={`w-8 h-px ${i < current ? "bg-green-400" : "bg-gray-200"}`} />}
      </div>
    ))}
  </div>
);

const CellCreateModal = ({ open, onClose, onSaved }) => {
  const [step, setStep]             = useState(0);
  const [form, setForm]             = useState(EMPTY);
  const [saving, setSaving]         = useState(false);
  const [showPass, setShowPass]     = useState(false);
  const [showOltPass, setShowOltPass] = useState(false);
  const [storedMk, setStoredMk]     = useState(null);

  const isFibra = form.cell_type === "fibra" || form.cell_type === "hifiber_ipoe";
  const isDHCP  = form.assignment === "dhcp_pool";

  useEffect(() => {
    if (open) {
      setStep(0); setForm(EMPTY); setShowPass(false); setShowOltPass(false);
      const mk = getStoredInterfaces();
      setStoredMk(mk);
      if (mk?.host) setForm(prev => ({ ...prev, mikrotik_host: mk.host }));
    }
  }, [open]);

  useEffect(() => {
    setForm(prev => ({ ...prev, assignment: getSuggestedAssignment(prev.cell_type) }));
  }, [form.cell_type]);

  const handleChange = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    if (name === "olt_model") {
      const model = OLT_MODELS.find(m => m.value === value);
      setForm(prev => ({ ...prev, olt_model: value, olt_brand: model?.brand || "zte", olt_total_ports: String(model?.ports || 16) }));
      return;
    }
    setForm(prev => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  }, []);

  const handleInterfaceChange = useCallback((e) => {
    const ifaceName = e.target.value;
    if (!storedMk) { setForm(prev => ({ ...prev, mikrotik_interface: ifaceName })); return; }
    const iface  = storedMk.interfaces.find(i => i.name === ifaceName);
    const cidr   = getCidrFromIface(iface);
    const parsed = parseCidr(cidr);
    if (parsed) {
      setForm(prev => ({ ...prev, mikrotik_interface: ifaceName, ipv4_range: parsed.red, ipv4_mask: parsed.mascara, ipv4_host_min: parsed.hostMin, ipv4_host_max: parsed.hostMax }));
    } else {
      setForm(prev => ({ ...prev, mikrotik_interface: ifaceName }));
    }
  }, [storedMk]);

  const handleClearStorage = () => {
    localStorage.removeItem("netkeeper_mk_interfaces");
    setStoredMk(null);
    toast("Interfaces limpiadas — escribe manualmente", { icon: "🗑️" });
  };

  const getSteps = () => {
    const s = ["General", "MikroTik"];
    if (isFibra) s.push("OLT");
    if (isDHCP)  s.push("DHCP");
    s.push("Resumen");
    return s;
  };
  const steps           = getSteps();
  const totalSteps      = steps.length;
  const currentStepName = steps[step];

  const validateStep = () => {
    if (currentStepName === "General" && !form.name.trim()) { toast.error("El nombre es obligatorio"); return false; }
    if (currentStepName === "MikroTik" && !form.mikrotik_host.trim()) { toast.error("La IP del MikroTik es obligatoria"); return false; }
    if (currentStepName === "MikroTik" && !form.mikrotik_interface.trim()) { toast.error("La interfaz es obligatoria"); return false; }
    if (currentStepName === "OLT" && !form.olt_ip.trim()) { toast.error("La IP de la OLT es obligatoria"); return false; }
    return true;
  };

  const nextStep = () => { if (validateStep()) setStep(s => s + 1); };
  const prevStep = () => setStep(s => s - 1);

  const handleSubmit = async () => {
    setSaving(true);
    try {
      const isPPPoE = form.assignment === "pppoe_distributed";
      const payload = {
        name: form.name, cell_type: form.cell_type, assignment: form.assignment,
        address: form.address || null,
        range_meters: form.range_meters ? parseInt(form.range_meters) : null,
        use_pcq: form.use_pcq,
        mikrotik_host: form.mikrotik_host,
        mikrotik_username_encrypted: form.mikrotik_username_encrypted || null,
        mikrotik_password_encrypted: form.mikrotik_password_encrypted || null,
        mikrotik_api_port: parseInt(form.mikrotik_api_port) || 8728,
        mikrotik_use_ssl: form.mikrotik_use_ssl,
        mikrotik_interface: form.mikrotik_interface || null,
        pppoe_service_ip: isPPPoE ? form.pppoe_service_ip || null : null,
        dhcp_pool_start: isDHCP ? form.dhcp_pool_start || null : null,
        dhcp_pool_end:   isDHCP ? form.dhcp_pool_end   || null : null,
        dhcp_gateway:    isDHCP ? form.dhcp_gateway    || null : null,
        dhcp_dns1:       isDHCP ? form.dhcp_dns1       || null : null,
        dhcp_dns2:       isDHCP ? form.dhcp_dns2       || null : null,
        dhcp_lease_time: isDHCP ? form.dhcp_lease_time || "1d" : null,
        dhcp_interface:  isDHCP ? form.dhcp_interface  || null : null,
        ipv4_range: form.ipv4_range || null, ipv4_mask: form.ipv4_mask || null,
        ipv4_host_min: form.ipv4_host_min || null, ipv4_host_max: form.ipv4_host_max || null,
        plan_ids: [],
      };

      // 1. Crear célula
      const res = await api.post("/cells/", payload);
      const cellId = res.data.id;

      // 2. Si es fibra → crear config OLT
      if (isFibra && form.olt_ip.trim()) {
        try {
          await api.post(`/cells/${cellId}/olt`, {
            brand:                  form.olt_brand,
            model_name:             form.olt_model,
            total_ports:            parseInt(form.olt_total_ports),
            olt_ip:                 form.olt_ip,
            ssh_port:               parseInt(form.olt_ssh_port) || 22,
            ssh_username_encrypted: form.olt_ssh_username || null,
            ssh_password_encrypted: form.olt_ssh_password || null,
          });
        } catch {
          toast.error("Célula creada, pero error guardando OLT. Configúrala desde la ficha.");
          onSaved(); return;
        }
      }

      toast.success("Célula creada correctamente ✅");
      onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al crear célula");
    } finally { setSaving(false); }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between px-8 py-5 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg"><Server className="w-5 h-5 text-blue-600" /></div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Nueva Célula</h2>
              <p className="text-xs text-gray-500">Paso {step + 1} de {totalSteps} — {currentStepName}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg"><X className="w-5 h-5 text-gray-500" /></button>
        </div>

        <div className="px-8 py-6">
          <StepIndicator current={step} steps={steps} />

          {/* General */}
          {currentStepName === "General" && (
            <div className="space-y-4">
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wide flex items-center gap-2">
                <Network className="w-4 h-4" /> Datos generales
              </h3>
              <Field label="Nombre de la célula" required>
                <TInput name="name" value={form.name} onChange={handleChange} placeholder="ej: Nodo Centro, Torre Norte" />
              </Field>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Tipo de célula" required>
                  <SInput name="cell_type" value={form.cell_type} onChange={handleChange}
                    options={[{ value: "fibra", label: "Fibra PPPoE" }, { value: "antenas", label: "Antenas" }, { value: "hifiber_ipoe", label: "Fibra IPoE" }]} />
                </Field>
                <Field label="Asignación de IPs" required>
                  <SInput name="assignment" value={form.assignment} onChange={handleChange} options={getAssignmentOptions(form.cell_type)} />
                </Field>
              </div>
              <Field label="Dirección física">
                <TInput name="address" value={form.address} onChange={handleChange} placeholder="ej: Av. Principal #123, Colonia Centro" />
              </Field>
              <div className="grid grid-cols-2 gap-4">
                <Field label={`Rango (metros) ~${form.cell_type === "antenas" ? "4,000" : "15,000"}`}>
                  <TInput name="range_meters" value={form.range_meters} onChange={handleChange}
                    placeholder={form.cell_type === "antenas" ? "4000" : "15000"} type="number" />
                </Field>
                <div className="flex items-end pb-1">
                  <Toggle label="Usar PCQ" name="use_pcq" checked={form.use_pcq} onChange={handleChange} desc="Per Connection Queue en MikroTik" />
                </div>
              </div>
              {isFibra && (
                <div className="bg-teal-50 border border-teal-200 rounded-xl px-4 py-3 text-xs text-teal-700 flex items-center gap-2">
                  <Cable className="w-4 h-4 flex-shrink-0" />
                  Célula de fibra — en el siguiente paso configurarás la OLT.
                </div>
              )}
            </div>
          )}

          {/* MikroTik */}
          {currentStepName === "MikroTik" && (
            <div className="space-y-4">
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wide flex items-center gap-2">
                <Router className="w-4 h-4" /> Conexión MikroTik
              </h3>
              <Field label="IP / Host MikroTik" required>
                <TInput name="mikrotik_host" value={form.mikrotik_host} onChange={handleChange}
                  placeholder="ej: 172.168.10.1" mono disabled={!!storedMk?.host} />
                {storedMk?.host && <p className="text-xs text-green-600 mt-1">✅ Host cargado desde Nodos de Red</p>}
              </Field>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Usuario">
                  <TInput name="mikrotik_username_encrypted" value={form.mikrotik_username_encrypted} onChange={handleChange} placeholder="admin" />
                </Field>
                <Field label="Contraseña">
                  <div className="relative">
                    <input type={showPass ? "text" : "password"} name="mikrotik_password_encrypted"
                      value={form.mikrotik_password_encrypted} onChange={handleChange} placeholder="••••••••"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2.5 pr-9 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    <button type="button" onClick={() => setShowPass(v => !v)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                      {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </Field>
                <Field label="Puerto API">
                  <TInput name="mikrotik_api_port" value={form.mikrotik_api_port} onChange={handleChange} placeholder="8728" type="number" mono />
                </Field>
                <div className="flex items-end pb-1">
                  <Toggle label="Usar SSL (8729)" name="mikrotik_use_ssl" checked={form.mikrotik_use_ssl} onChange={handleChange} />
                </div>
              </div>
              <Field label="Interfaz de esta célula" required>
                <InterfaceDropdown value={form.mikrotik_interface} onChange={handleInterfaceChange} storedMk={storedMk} onClearStorage={handleClearStorage} />
              </Field>
              <div className="border-t border-gray-100 pt-4">
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wide flex items-center gap-2 mb-4">
                  <Network className="w-4 h-4" /> Rango IPv4
                  {storedMk && form.mikrotik_interface && form.ipv4_range && <span className="text-green-600 font-normal normal-case ml-1">✅ Autocompletado</span>}
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Red"><TInput name="ipv4_range" value={form.ipv4_range} onChange={handleChange} placeholder="192.168.10.0" mono /></Field>
                  <Field label="Máscara">
                    <SInput name="ipv4_mask" value={form.ipv4_mask} onChange={handleChange}
                      options={[{ value: "", label: "Seleccionar..." }, ...["/8","/16","/24","/25","/26","/27","/28"].map(m => ({ value: m, label: m }))]} />
                  </Field>
                  <Field label="Host mínimo"><TInput name="ipv4_host_min" value={form.ipv4_host_min} onChange={handleChange} placeholder="192.168.10.1" mono /></Field>
                  <Field label="Host máximo"><TInput name="ipv4_host_max" value={form.ipv4_host_max} onChange={handleChange} placeholder="192.168.10.254" mono /></Field>
                </div>
              </div>
            </div>
          )}

          {/* OLT — solo para Fibra */}
          {currentStepName === "OLT" && (
            <div className="space-y-4">
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wide flex items-center gap-2">
                <Cable className="w-4 h-4 text-teal-500" /> Configuración OLT
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Modelo OLT" required className="col-span-2">
                  <SInput name="olt_model" value={form.olt_model} onChange={handleChange}
                    options={OLT_MODELS.map(m => ({ value: m.value, label: m.label }))} />
                </Field>
                <Field label="Total puertos">
                  <SInput name="olt_total_ports" value={form.olt_total_ports} onChange={handleChange}
                    options={[{ value: "8", label: "8 puertos" }, { value: "16", label: "16 puertos" }, { value: "32", label: "32 puertos" }, { value: "64", label: "64 puertos" }]} />
                </Field>
                <Field label="Puerto SSH">
                  <TInput name="olt_ssh_port" value={form.olt_ssh_port} onChange={handleChange} placeholder="8022" type="number" mono />
                </Field>
              </div>
              <Field label="IP / Host OLT" required>
                <TInput name="olt_ip" value={form.olt_ip} onChange={handleChange} placeholder="ej: 38.124.210.94" mono />
              </Field>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Usuario SSH">
                  <TInput name="olt_ssh_username" value={form.olt_ssh_username} onChange={handleChange} placeholder="iwisp" />
                </Field>
                <Field label="Contraseña SSH">
                  <div className="relative">
                    <input type={showOltPass ? "text" : "password"} name="olt_ssh_password"
                      value={form.olt_ssh_password} onChange={handleChange} placeholder="••••••••"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2.5 pr-9 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    <button type="button" onClick={() => setShowOltPass(v => !v)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                      {showOltPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </Field>
              </div>
              <div className="bg-teal-50 border border-teal-200 rounded-xl px-4 py-3 text-xs text-teal-700 flex items-center gap-2">
                <Cable className="w-4 h-4 flex-shrink-0" />
                Estas credenciales se usan al crear Zonas para ver los slots/puertos PON disponibles.
              </div>
            </div>
          )}

          {/* DHCP */}
          {currentStepName === "DHCP" && (
            <div className="space-y-4">
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wide flex items-center gap-2">
                <Zap className="w-4 h-4 text-green-500" /> Configuración DHCP Pool
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Inicio del pool"><TInput name="dhcp_pool_start" value={form.dhcp_pool_start} onChange={handleChange} placeholder="192.168.10.100" mono /></Field>
                <Field label="Fin del pool"><TInput name="dhcp_pool_end" value={form.dhcp_pool_end} onChange={handleChange} placeholder="192.168.10.200" mono /></Field>
                <Field label="Gateway"><TInput name="dhcp_gateway" value={form.dhcp_gateway} onChange={handleChange} placeholder="192.168.10.1" mono /></Field>
                <Field label="Interfaz DHCP"><TInput name="dhcp_interface" value={form.dhcp_interface} onChange={handleChange} placeholder="bridge1, ether2..." mono /></Field>
                <Field label="DNS Primario"><TInput name="dhcp_dns1" value={form.dhcp_dns1} onChange={handleChange} placeholder="8.8.8.8" mono /></Field>
                <Field label="DNS Secundario"><TInput name="dhcp_dns2" value={form.dhcp_dns2} onChange={handleChange} placeholder="8.8.4.4" mono /></Field>
                <Field label="Tiempo de lease">
                  <SInput name="dhcp_lease_time" value={form.dhcp_lease_time} onChange={handleChange}
                    options={[{ value: "1h", label: "1 hora" }, { value: "6h", label: "6 horas" }, { value: "12h", label: "12 horas" }, { value: "1d", label: "1 día" }, { value: "7d", label: "7 días" }]} />
                </Field>
              </div>
            </div>
          )}

          {/* Resumen */}
          {currentStepName === "Resumen" && (
            <div className="space-y-4">
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2">Resumen de la célula</h3>
              <div className="bg-gray-50 rounded-xl p-4 border border-gray-200 space-y-2">
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">General</p>
                {[
                  { label: "Nombre", value: form.name },
                  { label: "Tipo", value: CELL_TYPE_LABELS[form.cell_type]?.label },
                  { label: "Asignación", value: ASSIGNMENT_LABELS[form.assignment]?.label },
                  { label: "Dirección", value: form.address || "—" },
                ].map(({ label, value }) => (
                  <div key={label} className="flex justify-between text-sm">
                    <span className="text-gray-500">{label}</span>
                    <span className="font-medium text-gray-800">{value}</span>
                  </div>
                ))}
              </div>
              <div className="bg-gray-50 rounded-xl p-4 border border-gray-200 space-y-2">
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">MikroTik</p>
                {[
                  { label: "IP", value: form.mikrotik_host },
                  { label: "Interfaz", value: form.mikrotik_interface || "—" },
                  { label: "Rango IPv4", value: form.ipv4_range ? `${form.ipv4_range}${form.ipv4_mask}` : "—" },
                  { label: "Hosts", value: form.ipv4_host_min && form.ipv4_host_max ? `${form.ipv4_host_min} → ${form.ipv4_host_max}` : "—" },
                ].map(({ label, value }) => (
                  <div key={label} className="flex justify-between text-sm">
                    <span className="text-gray-500">{label}</span>
                    <span className="font-mono font-medium text-gray-800">{value}</span>
                  </div>
                ))}
              </div>
              {isFibra && form.olt_ip && (
                <div className="bg-teal-50 rounded-xl p-4 border border-teal-200 space-y-2">
                  <p className="text-xs font-bold text-teal-600 uppercase tracking-wide mb-3">OLT</p>
                  {[
                    { label: "Modelo",    value: form.olt_model },
                    { label: "Puertos",   value: `${form.olt_total_ports} puertos` },
                    { label: "IP OLT",    value: form.olt_ip },
                    { label: "Puerto SSH",value: form.olt_ssh_port },
                    { label: "Usuario",   value: form.olt_ssh_username || "—" },
                  ].map(({ label, value }) => (
                    <div key={label} className="flex justify-between text-sm">
                      <span className="text-teal-700">{label}</span>
                      <span className="font-mono font-medium text-teal-900">{value}</span>
                    </div>
                  ))}
                </div>
              )}
              {isDHCP && form.dhcp_pool_start && (
                <div className="bg-green-50 rounded-xl p-4 border border-green-200 space-y-2">
                  <p className="text-xs font-bold text-green-600 uppercase tracking-wide mb-3">DHCP Pool</p>
                  {[
                    { label: "Rango",   value: `${form.dhcp_pool_start} → ${form.dhcp_pool_end}` },
                    { label: "Gateway", value: form.dhcp_gateway },
                    { label: "DNS",     value: `${form.dhcp_dns1} / ${form.dhcp_dns2}` },
                  ].map(({ label, value }) => (
                    <div key={label} className="flex justify-between text-sm">
                      <span className="text-green-700">{label}</span>
                      <span className="font-mono font-medium text-green-900">{value}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Footer */}
          <div className="flex justify-between gap-3 pt-6 mt-6 border-t border-gray-200">
            <button type="button" onClick={step === 0 ? onClose : prevStep}
              className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">
              <ChevronLeft className="w-4 h-4" />{step === 0 ? "Cancelar" : "Atrás"}
            </button>
            {step < totalSteps - 1 ? (
              <button type="button" onClick={nextStep}
                className="flex items-center gap-2 px-6 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">
                Siguiente <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button type="button" onClick={handleSubmit} disabled={saving}
                className="flex items-center gap-2 px-6 py-2.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50">
                {saving ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Creando...</> : <><CheckCircle2 className="w-4 h-4" /> Crear Célula</>}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default function CellsPage() {
  const navigate = useNavigate();
  const [cells, setCells]                       = useState([]);
  const [loading, setLoading]                   = useState(true);
  const [search, setSearch]                     = useState("");
  const [filterType, setFilterType]             = useState("");
  const [filterAssignment, setFilterAssignment] = useState("");
  const [sortField, setSortField]               = useState("id");
  const [sortDir, setSortDir]                   = useState("asc");
  const [modalOpen, setModalOpen]               = useState(false);

  useEffect(() => { window.scrollTo(0, 0); }, []);
  useEffect(() => { fetchCells(); }, [filterType]);

  const fetchCells = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterType) params.cell_type = filterType;
      const res = await api.get("/cells/", { params });
      setCells(res.data);
    } catch { toast.error("Error al cargar células"); }
    finally { setLoading(false); }
  };

  const filtered = cells
    .filter(c => {
      const q = search.toLowerCase();
      if (q && !c.name.toLowerCase().includes(q) && !(c.mikrotik_host || "").includes(q)) return false;
      if (filterAssignment && c.assignment !== filterAssignment) return false;
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
    return sortDir === "asc" ? <ArrowUp className="w-3.5 h-3.5 text-blue-500" /> : <ArrowDown className="w-3.5 h-3.5 text-blue-500" />;
  };

  const stats = {
    total:       cells.length,
    fibra:       cells.filter(c => c.cell_type === "fibra" || c.cell_type === "hifiber_ipoe").length,
    antenas:     cells.filter(c => c.cell_type === "antenas").length,
    initialized: cells.filter(c => c.is_initialized).length,
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Células de Red</h1>
          <p className="text-sm text-gray-500 mt-0.5">Nodos MikroTik — cerebro de cada conexión</p>
        </div>
        <button onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 shadow-sm transition-colors">
          <Plus className="w-4 h-4" /> Nueva Célula
        </button>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total células", value: stats.total,       icon: Server,       color: "blue"   },
          { label: "Fibra",         value: stats.fibra,       icon: Wifi,         color: "blue"   },
          { label: "Antenas",       value: stats.antenas,     icon: Radio,        color: "purple" },
          { label: "Inicializadas", value: stats.initialized, icon: CheckCircle2, color: "green"  },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-500">{label}</span>
              <div className={`p-1.5 rounded-lg bg-${color}-100`}><Icon className={`w-3.5 h-3.5 text-${color}-600`} /></div>
            </div>
            <p className="text-2xl font-bold text-gray-900">{value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 mb-4">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input type="text" placeholder="Buscar por nombre o IP MikroTik..."
              value={search} onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <select value={filterType} onChange={e => setFilterType(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white min-w-40">
            <option value="">Todos los tipos</option>
            <option value="fibra">Fibra PPPoE</option>
            <option value="antenas">Antenas</option>
            <option value="hifiber_ipoe">Fibra IPoE</option>
          </select>
          <select value={filterAssignment} onChange={e => setFilterAssignment(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white min-w-40">
            <option value="">Todas las asignaciones</option>
            <option value="pppoe_distributed">PPPoE</option>
            <option value="static_addressing">Estático</option>
            <option value="dhcp_pool">DHCP</option>
          </select>
          {(search || filterType || filterAssignment) && (
            <button onClick={() => { setSearch(""); setFilterType(""); setFilterAssignment(""); }}
              className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-500 border border-gray-300 rounded-lg hover:bg-gray-50">
              <X className="w-3.5 h-3.5" /> Limpiar
            </button>
          )}
          <span className="ml-auto text-xs text-gray-400 font-medium">{filtered.length} célula{filtered.length !== 1 ? "s" : ""}</span>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-gray-400">
            <Server className="w-10 h-10 mb-3 text-gray-300" />
            <p className="font-medium">No hay células configuradas</p>
            <p className="text-sm mt-1">Crea la primera célula de red</p>
            <button onClick={() => setModalOpen(true)} className="mt-4 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">Nueva célula</button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  {[
                    { label: "Célula",       field: "name"            },
                    { label: "Tipo",         field: "cell_type"       },
                    { label: "Asignación",   field: "assignment"      },
                    { label: "MikroTik IP",  field: "mikrotik_host"   },
                    { label: "Conexiones",   field: "has_connections"  },
                    { label: "Estado",       field: "is_active"       },
                    { label: "Inicializada", field: "is_initialized"  },
                    { label: "",             field: null               },
                  ].map(({ label, field }) => (
                    <th key={label} onClick={() => field && handleSort(field)}
                      className={`px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide whitespace-nowrap ${field ? "cursor-pointer hover:bg-gray-100 select-none" : ""}`}>
                      <span className="flex items-center gap-1.5">{label} {field && <SortIcon field={field} />}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map(cell => {
                  const typeInfo   = CELL_TYPE_LABELS[cell.cell_type];
                  const TypeIcon   = typeInfo?.icon || Server;
                  const assignInfo = ASSIGNMENT_LABELS[cell.assignment];
                  return (
                    <tr key={cell.id} onClick={() => navigate(`/celulas/${cell.id}`)}
                      className="hover:bg-blue-50/40 transition-colors cursor-pointer group">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 bg-blue-50 rounded-lg group-hover:bg-blue-100 transition-colors">
                            <TypeIcon className="w-3.5 h-3.5 text-blue-600" />
                          </div>
                          <div>
                            <p className="font-semibold text-gray-900">{cell.name}</p>
                            {cell.address && <p className="text-xs text-gray-400 truncate max-w-40">{cell.address}</p>}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${typeInfo?.color || "bg-gray-100 text-gray-600"}`}>
                          {typeInfo?.label || cell.cell_type}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${assignInfo?.color || "bg-gray-100 text-gray-600"}`}>
                          {assignInfo?.label || cell.assignment}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {cell.mikrotik_host ? <span className="font-mono text-sm text-gray-700">{cell.mikrotik_host}</span> : <span className="text-gray-300 text-xs">Sin configurar</span>}
                      </td>
                      <td className="px-4 py-3">
                        {cell.has_connections
                          ? <span className="flex items-center gap-1 text-xs font-medium text-blue-600"><CheckCircle2 className="w-3.5 h-3.5" /> Con conexiones</span>
                          : <span className="text-xs text-gray-400">Sin conexiones</span>}
                      </td>
                      <td className="px-4 py-3">
                        {cell.is_active
                          ? <span className="flex items-center gap-1.5 text-xs font-medium text-green-700"><span className="w-1.5 h-1.5 bg-green-500 rounded-full" /> Activa</span>
                          : <span className="flex items-center gap-1.5 text-xs font-medium text-gray-400"><span className="w-1.5 h-1.5 bg-gray-400 rounded-full" /> Inactiva</span>}
                      </td>
                      <td className="px-4 py-3">
                        {cell.is_initialized
                          ? <span className="flex items-center gap-1 text-xs font-medium text-green-600"><CheckCircle2 className="w-3.5 h-3.5" /> Sí</span>
                          : <span className="flex items-center gap-1 text-xs font-medium text-amber-500"><AlertCircle className="w-3.5 h-3.5" /> Pendiente</span>}
                      </td>
                      <td className="px-4 py-3">
                        <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-blue-400 transition-colors" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <CellCreateModal open={modalOpen} onClose={() => setModalOpen(false)}
        onSaved={() => { setModalOpen(false); fetchCells(); }} />
    </div>
  );
}
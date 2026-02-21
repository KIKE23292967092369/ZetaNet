import { useState, useEffect, useCallback } from "react";
import { X, Wifi, Zap, Radio, Plus, ChevronRight } from "lucide-react";
import api from "../../api/axios";
import toast from "react-hot-toast";

const FieldText = ({ label, name, value, onChange, placeholder, required, className = "" }) => (
  <div className={className}>
    <label className="block text-xs font-semibold text-gray-500 mb-1">{label}{required && <span className="text-red-500 ml-0.5">*</span>}</label>
    <input type="text" name={name} value={value || ""} onChange={onChange} placeholder={placeholder}
      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
  </div>
);

const FieldSelect = ({ label, name, value, onChange, options, required, disabled, className = "" }) => (
  <div className={className}>
    <label className="block text-xs font-semibold text-gray-500 mb-1">{label}{required && <span className="text-red-500 ml-0.5">*</span>}</label>
    <select name={name} value={value || ""} onChange={onChange} disabled={disabled}
      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white disabled:bg-gray-50 disabled:text-gray-400">
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  </div>
);

const FieldPassword = ({ label, name, value, onChange, className = "" }) => (
  <div className={className}>
    <label className="block text-xs font-semibold text-gray-500 mb-1">{label}</label>
    <input type="password" name={name} value={value || ""} onChange={onChange} placeholder="••••••••"
      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
  </div>
);

const SectionTitle = ({ icon: Icon, title, color = "text-blue-600", bg = "bg-blue-50" }) => (
  <div className="flex items-center gap-2 mb-3 mt-5">
    <div className={`p-1.5 ${bg} rounded-lg`}><Icon className={`w-3.5 h-3.5 ${color}`} /></div>
    <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">{title}</span>
  </div>
);

export default function CreateConnectionModal({ onClose, onSaved, preClientId = null }) {
  const [saving, setSaving] = useState(false);

  // Datos base
  const [clients, setClients] = useState([]);
  const [cells, setCells] = useState([]);
  const [plans, setPlans] = useState([]);
  const [onus, setOnus] = useState([]);
  const [cpes, setCpes] = useState([]);
  const [ipPool, setIpPool] = useState([]);

  // Cascada FIBRA
  const [zones, setZones] = useState([]);
  const [naps, setNaps] = useState([]);
  const [ports, setPorts] = useState([]);

  // Célula seleccionada (para saber tipo)
  const [selectedCell, setSelectedCell] = useState(null);

  const [form, setForm] = useState({
    client_id: preClientId || "",
    cell_id: "",
    plan_id: "",
    // Ubicación
    locality: "",
    address: "",
    street_between_1: "",
    street_between_2: "",
    contract_date: new Date().toISOString().split("T")[0],
    is_free: false,
    // FIBRA
    olt_zone_id: "",
    nap_id: "",
    nap_port_id: "",
    ip_address: "",
    pppoe_profile: "default-encryption",
    pppoe_username: "",
    pppoe_password_encrypted: "",
    onu_id: "",
    mode: "router",
    // ANTENA
    cpe_id: "",
    router_id: "",
    ip_additional: "",
    generate_month_charge: true,
  });

  // Cargar datos iniciales
  useEffect(() => {
    const load = async () => {
      try {
        const [clientsRes, cellsRes] = await Promise.all([
  api.get("/clients/", { params: { per_page: 200 } }),
  api.get("/cells/"),
]);
setClients(clientsRes.data.clients || clientsRes.data || []);
setCells(cellsRes.data.cells || cellsRes.data || []);
      } catch { toast.error("Error al cargar datos"); }
    };
    load();
  }, []);

  // Al cambiar célula → detectar tipo + cargar planes + cargar equipos
  useEffect(() => {
    if (!form.cell_id) { setSelectedCell(null); setPlans([]); return; }
    const cell = cells.find(c => c.id === parseInt(form.cell_id));
    setSelectedCell(cell || null);

    // Reset cascada
    setForm(prev => ({ ...prev, plan_id: "", olt_zone_id: "", nap_id: "", nap_port_id: "", onu_id: "", cpe_id: "" }));
    setZones([]); setNaps([]); setPorts([]); setIpPool([]);

    const loadCellData = async () => {
      try {
        const [plansRes] = await Promise.all([
          api.get("/plans/", { params: { cell_id: form.cell_id, is_active: true } }),
        ]);
        setPlans(plansRes.data.plans || plansRes.data || []);
        const poolRes = await api.get(`/cells/${form.cell_id}/ip-pool`);
        setIpPool(poolRes.data?.free_ips || []);


        if (cell?.cell_type === "fibra" || cell?.cell_type === "hifiber_ipoe") {
          const [zonesRes, onusRes] = await Promise.all([
            api.get(`/cells/${form.cell_id}/zones`),
            api.get("/inventory/onus", { params: { available: true } }),
          ]);
          setZones(zonesRes.data);
          setOnus(onusRes.data);
        } else if (cell?.cell_type === "antenas") {
          const cpesRes = await api.get("/inventory/cpes", { params: { available: true } });
          setCpes(cpesRes.data);
        }
      } catch { toast.error("Error al cargar datos de célula"); }
    };
    loadCellData();
  }, [form.cell_id, cells]);

  // Al cambiar zona → cargar NAPs
  useEffect(() => {
    if (!form.olt_zone_id) { setNaps([]); setPorts([]); return; }
    setForm(prev => ({ ...prev, nap_id: "", nap_port_id: "" }));
    api.get(`/cells/zones/${form.olt_zone_id}/cascade/naps`)
      .then(res => setNaps(res.data))
      .catch(() => toast.error("Error al cargar NAPs"));
  }, [form.olt_zone_id]);

  // Al cambiar NAP → cargar puertos libres
  useEffect(() => {
    if (!form.nap_id) { setPorts([]); return; }
    setForm(prev => ({ ...prev, nap_port_id: "" }));
    api.get(`/cells/naps/${form.nap_id}/cascade/ports`)
      .then(res => setPorts(res.data.filter(p => !p.is_occupied)))
      .catch(() => toast.error("Error al cargar puertos"));
  }, [form.nap_id]);

  const handleChange = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    setForm(prev => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  }, []);

  const isFibra = selectedCell?.cell_type === "fibra" || selectedCell?.cell_type === "hifiber_ipoe";
  const isAntena = selectedCell?.cell_type === "antenas";

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.client_id) return toast.error("Selecciona un cliente");
    if (!form.cell_id) return toast.error("Selecciona una célula");
    if (!form.plan_id) return toast.error("Selecciona un plan");

    setSaving(true);
    try {
      if (isFibra) {
        if (!form.olt_zone_id || !form.nap_id || !form.nap_port_id) return toast.error("Selecciona zona, NAP y puerto");
        if (!form.ip_address || !form.pppoe_username || !form.pppoe_password_encrypted) return toast.error("Completa los datos PPPoE");
        if (!form.onu_id) return toast.error("Selecciona una ONU");

        await api.post("/connections/fiber", {
          client_id: parseInt(form.client_id),
          cell_id: parseInt(form.cell_id),
          plan_id: parseInt(form.plan_id),
          locality: form.locality || null,
          address: form.address || null,
          street_between_1: form.street_between_1 || null,
          street_between_2: form.street_between_2 || null,
          contract_date: form.contract_date || null,
          is_free: form.is_free,
          olt_zone_id: parseInt(form.olt_zone_id),
          nap_id: parseInt(form.nap_id),
          nap_port_id: parseInt(form.nap_port_id),
          ip_address: form.ip_address,
          pppoe_profile: form.pppoe_profile || "default-encryption",
          pppoe_username: form.pppoe_username,
          pppoe_password_encrypted: form.pppoe_password_encrypted,
          onu_id: parseInt(form.onu_id),
          mode: form.mode,
        });
        toast.success("Conexión FIBRA creada ✅");
      } else {
        if (!form.ip_address) return toast.error("Ingresa la IP");
        if (!form.cpe_id) return toast.error("Selecciona un CPE");

        await api.post("/connections/antenna", {
          client_id: parseInt(form.client_id),
          cell_id: parseInt(form.cell_id),
          plan_id: parseInt(form.plan_id),
          locality: form.locality || null,
          address: form.address || null,
          street_between_1: form.street_between_1 || null,
          street_between_2: form.street_between_2 || null,
          contract_date: form.contract_date || null,
          is_free: form.is_free,
          generate_month_charge: form.generate_month_charge,
          ip_address: form.ip_address,
          ip_additional: form.ip_additional || null,
          cpe_id: parseInt(form.cpe_id),
          router_id: form.router_id ? parseInt(form.router_id) : null,
        });
        toast.success("Conexión ANTENA creada ✅");
      }
      onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al crear conexión");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 rounded-lg"><Wifi className="w-5 h-5 text-blue-600" /></div>
            <div>
              <h3 className="font-bold text-gray-900">Nueva Conexión</h3>
              <p className="text-xs text-gray-500">
                {isFibra ? "🔵 Fibra PPPoE" : isAntena ? "🟣 Antena" : "Selecciona una célula"}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg"><X className="w-4 h-4" /></button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="overflow-y-auto px-6 py-4 flex-1">

          {/* DATOS BÁSICOS */}
          <SectionTitle icon={Wifi} title="Datos básicos" />
          <div className="grid grid-cols-2 gap-3">
            {preClientId ? (
  <div className="col-span-2">
    <label className="block text-xs font-semibold text-gray-500 mb-1">Cliente</label>
    <div className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-700 font-medium">
      {clients.find(c => c.id === parseInt(preClientId))?.first_name} {clients.find(c => c.id === parseInt(preClientId))?.last_name}
    </div>
  </div>
) : (
  <FieldSelect label="Cliente" name="client_id" value={form.client_id} onChange={handleChange} required
    className="col-span-2"
    options={[
      { value: "", label: "Seleccionar cliente..." },
      ...clients.map(c => ({ value: c.id, label: `${c.first_name} ${c.last_name}` }))
    ]} />
)}
            <FieldSelect label="Célula" name="cell_id" value={form.cell_id} onChange={handleChange} required
              className="col-span-2"
              options={[
                { value: "", label: "Seleccionar célula..." },
                ...cells.map(c => ({ value: c.id, label: `${c.name} (${c.cell_type === "fibra" ? "Fibra" : c.cell_type === "antenas" ? "Antena" : "IPoE"})` }))
              ]} />
            <FieldSelect label="Plan" name="plan_id" value={form.plan_id} onChange={handleChange} required
              disabled={!form.cell_id}
              options={[
                { value: "", label: plans.length === 0 ? "— Selecciona célula primero —" : "Seleccionar plan..." },
                ...plans.map(p => ({ value: p.id, label: `${p.name} — ${p.download_speed}/${p.upload_speed}` }))
              ]} />
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Fecha contrato</label>
              <input type="date" name="contract_date" value={form.contract_date} onChange={handleChange}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>

          {/* FIBRA — Cascada */}
          {isFibra && (
            <>
              <SectionTitle icon={Zap} title="Cascada de red FIBRA" color="text-blue-600" bg="bg-blue-50" />
              <div className="grid grid-cols-3 gap-3 mb-3">
                <FieldSelect label="Zona OLT" name="olt_zone_id" value={form.olt_zone_id} onChange={handleChange} required
                  options={[
                    { value: "", label: "Seleccionar zona..." },
                    ...zones.map(z => ({ value: z.id, label: z.name }))
                  ]} />
                <FieldSelect label="NAP" name="nap_id" value={form.nap_id} onChange={handleChange} required
                  disabled={!form.olt_zone_id}
                  options={[
                    { value: "", label: form.olt_zone_id ? "Seleccionar NAP..." : "— Zona primero —" },
                    ...naps.map(n => ({ value: n.id, label: `${n.name} (${n.free_ports} libres)` }))
                  ]} />
                <FieldSelect label="Puerto" name="nap_port_id" value={form.nap_port_id} onChange={handleChange} required
                  disabled={!form.nap_id}
                  options={[
                    { value: "", label: form.nap_id ? "Seleccionar puerto..." : "— NAP primero —" },
                    ...ports.map(p => ({ value: p.id, label: `Puerto ${p.port_number}` }))
                  ]} />
              </div>

              <SectionTitle icon={Zap} title="Red PPPoE" color="text-blue-600" bg="bg-blue-50" />
<div className="grid grid-cols-2 gap-3">
  <div>
    <label className="block text-xs font-semibold text-gray-500 mb-1">
      IP asignada <span className="text-red-500">*</span>
    </label>
    {ipPool.length > 0 ? (
      <select name="ip_address" value={form.ip_address} onChange={handleChange}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white font-mono">
        <option value="">Seleccionar IP libre...</option>
        {ipPool.map(ip => <option key={ip} value={ip}>{ip}</option>)}
      </select>
    ) : (
      <input type="text" name="ip_address" value={form.ip_address || ""} onChange={handleChange}
        placeholder="10.0.0.5"
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono" />
    )}
  </div>
  <FieldText label="Perfil PPPoE" name="pppoe_profile" value={form.pppoe_profile} onChange={handleChange}
    placeholder="default-encryption" />
  <FieldText label="Usuario PPPoE" name="pppoe_username" value={form.pppoe_username} onChange={handleChange}
    placeholder="jperez.fibra" required />
  <FieldPassword label="Contraseña PPPoE" name="pppoe_password_encrypted" value={form.pppoe_password_encrypted} onChange={handleChange} />
  <FieldSelect label="ONU (inventario)" name="onu_id" value={form.onu_id} onChange={handleChange} required
    options={[
      { value: "", label: "Seleccionar ONU..." },
      ...onus.map(o => ({ value: o.id, label: `${o.serial_number} — ${o.mac_address}` }))
    ]} />
  <FieldSelect label="Modo" name="mode" value={form.mode} onChange={handleChange}
    options={[
      { value: "router", label: "Router" },
      { value: "bridge", label: "Bridge" },
    ]} />
</div>
            </>
          )}

          {/* ANTENA */}
{isAntena && (
  <>
    <SectionTitle icon={Radio} title="Red Antena" color="text-purple-600" bg="bg-purple-50" />
    <div className="grid grid-cols-2 gap-3">
      <div>
        <label className="block text-xs font-semibold text-gray-500 mb-1">
          IP asignada <span className="text-red-500">*</span>
        </label>
        {ipPool.length > 0 ? (
          <select name="ip_address" value={form.ip_address} onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white font-mono">
            <option value="">Seleccionar IP libre...</option>
            {ipPool.map(ip => <option key={ip} value={ip}>{ip}</option>)}
          </select>
        ) : (
          <input type="text" name="ip_address" value={form.ip_address || ""} onChange={handleChange}
            placeholder="192.168.10.50"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono" />
        )}
      </div>
      <FieldText label="IPs adicionales" name="ip_additional" value={form.ip_additional} onChange={handleChange}
        placeholder="Opcional" />
      <FieldSelect label="CPE (inventario)" name="cpe_id" value={form.cpe_id} onChange={handleChange} required
        className="col-span-2"
        options={[
          { value: "", label: "Seleccionar CPE..." },
          ...cpes.map(c => ({ value: c.id, label: `${c.serial_number} — ${c.mac_address}` }))
        ]} />
    </div>
  </>
)}

          {/* UBICACIÓN */}
          {(isFibra || isAntena) && (
            <>
              <SectionTitle icon={Wifi} title="Ubicación" color="text-gray-500" bg="bg-gray-100" />
              <div className="grid grid-cols-2 gap-3">
                <FieldText label="Localidad" name="locality" value={form.locality} onChange={handleChange} placeholder="ej: Col. Centro" />
                <FieldText label="Domicilio" name="address" value={form.address} onChange={handleChange} placeholder="Calle #123" />
                <FieldText label="Entre calle 1" name="street_between_1" value={form.street_between_1} onChange={handleChange} placeholder="Entre..." />
                <FieldText label="Entre calle 2" name="street_between_2" value={form.street_between_2} onChange={handleChange} placeholder="Y..." />
              </div>
            </>
          )}

          {/* Sin célula seleccionada */}
          {!selectedCell && form.cell_id === "" && (
            <div className="text-center py-8 text-gray-400">
              <Wifi className="w-10 h-10 mx-auto mb-2 text-gray-300" />
              <p className="text-sm">Selecciona una célula para continuar</p>
            </div>
          )}
        </form>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-gray-100">
          <button type="button" onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50">
            Cancelar
          </button>
          <button onClick={handleSubmit} disabled={saving || !selectedCell}
            className="flex items-center gap-2 px-5 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {saving
              ? <><div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Creando...</>
              : <><Plus className="w-3.5 h-3.5" /> Crear conexión</>
            }
          </button>
        </div>
      </div>
    </div>
  );
}
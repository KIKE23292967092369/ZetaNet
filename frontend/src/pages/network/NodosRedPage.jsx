/**
 * NodosRedPage.jsx
 * NetKeeper - Nodos de Red
 * Tab MikroTik: conectar, estado en vivo, tráfico, interfaces + IP pool ocupadas/libres
 * Tab OLT: conectar directamente con credenciales SSH
 */
import { useState, useEffect, useRef, useCallback } from "react";
import api from "../../api/axios";
import toast from "react-hot-toast";
import {
  Router, Activity, X, ChevronDown, ChevronUp,
  Cpu, MemoryStick, Clock, Zap, Network, ArrowUp, ArrowDown,
  Eye, EyeOff, Cable, AlertCircle, CheckCircle2, RefreshCw,
  CircleDot,
} from "lucide-react";

// ─── Helpers ──────────────────────────────────────────────────────────────────
const formatBytes = (bytes) => {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

const formatMbps = (bps) => {
  if (!bps || bps <= 0) return "0 Mbps";
  const mbps = bps / 1_000_000;
  if (mbps >= 1000) return `${(mbps / 1000).toFixed(2)} Gbps`;
  if (mbps >= 1) return `${mbps.toFixed(2)} Mbps`;
  return `${(bps / 1000).toFixed(2)} Kbps`;
};

const calcPct = (used, total) =>
  total > 0 ? Math.round((used / total) * 100) : 0;

const ProgressBar = ({ pct, colorClass }) => (
  <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
    <div
      className={`h-full rounded-full transition-all duration-500 ${colorClass}`}
      style={{ width: `${Math.min(pct, 100)}%` }}
    />
  </div>
);

const trafficColor = (mbps) => {
  if (mbps > 500) return "bg-red-500";
  if (mbps > 100) return "bg-amber-400";
  return "bg-emerald-500";
};

const poolBarColor = (pct) => {
  if (pct >= 90) return "bg-red-500";
  if (pct >= 70) return "bg-amber-400";
  return "bg-indigo-500";
};

const statusBadge = (status) => {
  if (status === "active")    return "bg-green-100 text-green-700";
  if (status === "suspended") return "bg-amber-100 text-amber-700";
  return "bg-gray-100 text-gray-500";
};

const statusLabel = (status) => {
  if (status === "active")    return "Activo";
  if (status === "suspended") return "Suspendido";
  return status;
};

// ─── Formulario conexión MikroTik ─────────────────────────────────────────────
const ConnectForm = ({ onConnect, connecting }) => {
  const [form, setForm] = useState({
    host: "", username: "admin", password: "", port: "8728", use_ssl: false,
  });
  const [showPass, setShowPass] = useState(false);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm(prev => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.host.trim()) return toast.error("Ingresa la IP del MikroTik");
    if (!form.username.trim()) return toast.error("Ingresa el usuario");
    if (!form.password.trim()) return toast.error("Ingresa la contraseña");
    onConnect({ ...form, port: parseInt(form.port) || 8728 });
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-red-50 rounded-xl">
          <Router className="w-6 h-6 text-red-600" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-gray-900">Conectar al MikroTik</h2>
          <p className="text-sm text-gray-500">Ingresa las credenciales del router</p>
        </div>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-gray-500 mb-1">
            IP / Host <span className="text-red-500">*</span>
          </label>
          <input type="text" name="host" value={form.host} onChange={handleChange}
            placeholder="ej: 172.168.10.1"
            className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 font-mono" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Usuario</label>
            <input type="text" name="username" value={form.username} onChange={handleChange}
              placeholder="admin"
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Contraseña</label>
            <div className="relative">
              <input type={showPass ? "text" : "password"} name="password"
                value={form.password} onChange={handleChange} placeholder="••••••••"
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 pr-9 text-sm focus:outline-none focus:ring-2 focus:ring-red-500" />
              <button type="button" onClick={() => setShowPass(v => !v)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Puerto API</label>
            <input type="number" name="port" value={form.port} onChange={handleChange}
              placeholder="8728"
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 font-mono" />
          </div>
          <div className="flex items-end pb-2.5">
            <label className="flex items-center gap-2 cursor-pointer">
              <div className="relative">
                <input type="checkbox" name="use_ssl" checked={form.use_ssl}
                  onChange={handleChange} className="sr-only" />
                <div className={`w-9 h-5 rounded-full transition-colors ${form.use_ssl ? "bg-red-600" : "bg-gray-300"}`} />
                <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${form.use_ssl ? "translate-x-4" : ""}`} />
              </div>
              <span className="text-sm text-gray-600">SSL (8729)</span>
            </label>
          </div>
        </div>
        <button type="submit" disabled={connecting}
          className="w-full flex items-center justify-center gap-2 py-3 bg-red-600 text-white text-sm font-semibold rounded-xl hover:bg-red-700 disabled:opacity-50 transition-colors mt-2">
          {connecting
            ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Conectando...</>
            : <><Router className="w-4 h-4" /> Conectar</>}
        </button>
      </form>
    </div>
  );
};

// ─── Tarjeta sistema MikroTik ─────────────────────────────────────────────────
const SystemCard = ({ info, onDisconnect }) => {
  const cpuPct   = parseInt(info.cpu_load) || 0;
  const freeRam  = parseInt(info.free_memory) || 0;
  const totalRam = parseInt(info.total_memory) || 1;
  const usedRam  = totalRam - freeRam;
  const ramPct   = calcPct(usedRam, totalRam);

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
      <div className="flex items-start justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-red-50 rounded-xl">
            <Router className="w-6 h-6 text-red-600" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-gray-900">{info.identity}</h2>
              <span className="flex items-center gap-1 text-xs font-medium text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" /> Conectado
              </span>
            </div>
            <p className="text-sm text-gray-500 font-mono mt-0.5">{info.host} · {info.board_name}</p>
          </div>
        </div>
        <button onClick={onDisconnect}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-500 border border-gray-300 rounded-lg hover:bg-gray-50">
          <X className="w-3.5 h-3.5" /> Desconectar
        </button>
      </div>
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-blue-500" />
            <span className="text-xs font-semibold text-gray-500">Versión</span>
          </div>
          <p className="text-sm font-bold text-gray-800 font-mono">{info.version || "—"}</p>
        </div>
        <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-purple-500" />
            <span className="text-xs font-semibold text-gray-500">Uptime</span>
          </div>
          <p className="text-sm font-bold text-gray-800">{info.uptime || "—"}</p>
        </div>
        <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-orange-500" />
              <span className="text-xs font-semibold text-gray-500">CPU</span>
            </div>
            <span className={`text-xs font-bold ${cpuPct > 80 ? "text-red-600" : cpuPct > 60 ? "text-amber-500" : "text-green-600"}`}>
              {cpuPct}%
            </span>
          </div>
          <ProgressBar pct={cpuPct}
            colorClass={cpuPct > 80 ? "bg-red-500" : cpuPct > 60 ? "bg-amber-400" : "bg-green-500"} />
        </div>
        <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <MemoryStick className="w-4 h-4 text-indigo-500" />
              <span className="text-xs font-semibold text-gray-500">RAM</span>
            </div>
            <span className={`text-xs font-bold ${ramPct > 80 ? "text-red-600" : ramPct > 60 ? "text-amber-500" : "text-green-600"}`}>
              {ramPct}%
            </span>
          </div>
          <ProgressBar pct={ramPct}
            colorClass={ramPct > 80 ? "bg-red-500" : ramPct > 60 ? "bg-amber-400" : "bg-indigo-500"} />
          <p className="text-xs text-gray-400 mt-1">
            {formatBytes(freeRam)} libre / {formatBytes(totalRam)}
          </p>
        </div>
      </div>
    </div>
  );
};

// ─── Tráfico en tiempo real ───────────────────────────────────────────────────
const TrafficMonitor = ({ creds }) => {
  const [traffic, setTraffic] = useState({});
  const [rates, setRates]     = useState({});
  const prevRef               = useRef({});
  const prevTimeRef           = useRef(null);
  const intervalRef           = useRef(null);

  const fetchTraffic = useCallback(async () => {
    try {
      const res = await api.post("/mikrotik/traffic-snapshot", creds);
      const now = Date.now();
      const newData = {};
      res.data.interfaces.forEach(iface => {
        newData[iface.name] = { tx: iface.tx_byte, rx: iface.rx_byte, running: iface.running };
      });

      const newRates = {};
      if (prevTimeRef.current && now - prevTimeRef.current > 0) {
        const dt = (now - prevTimeRef.current) / 1000;
        Object.keys(newData).forEach(name => {
          const p = prevRef.current[name];
          const n = newData[name];
          if (p) {
            newRates[name] = {
              txBps:   Math.max(0, (n.tx - p.tx) / dt),
              rxBps:   Math.max(0, (n.rx - p.rx) / dt),
              running: n.running,
            };
          }
        });
      }
      prevRef.current     = newData;
      prevTimeRef.current = now;
      setTraffic(newData);
      setRates(newRates);
    } catch { /* silencioso */ }
  }, [creds]);

  useEffect(() => {
    fetchTraffic();
    intervalRef.current = setInterval(fetchTraffic, 3000);
    return () => clearInterval(intervalRef.current);
  }, [fetchTraffic]);

  const ifaceNames = Object.keys(traffic);
  if (ifaceNames.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
      <div className="flex items-center gap-2 mb-5">
        <Activity className="w-5 h-5 text-emerald-600" />
        <h3 className="font-bold text-gray-800">Tráfico en Tiempo Real</h3>
        <span className="ml-auto flex items-center gap-1 text-xs text-emerald-600">
          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" /> Live · 3s
        </span>
      </div>
      <div className="space-y-3">
        {ifaceNames.map(name => {
          const r      = rates[name];
          const txMbps = r ? r.txBps / 1_000_000 : 0;
          const rxMbps = r ? r.rxBps / 1_000_000 : 0;
          const maxMbps = Math.max(txMbps, rxMbps, 1);
          const running = traffic[name]?.running;
          return (
            <div key={name} className="border border-gray-100 rounded-xl p-4 hover:border-gray-200 transition-colors">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${running ? "bg-green-500 animate-pulse" : "bg-gray-300"}`} />
                  <span className="font-mono font-semibold text-sm text-gray-800">{name}</span>
                </div>
                {r ? (
                  <div className="flex items-center gap-4 text-xs">
                    <span className="flex items-center gap-1 text-blue-600 font-medium">
                      <ArrowUp className="w-3 h-3" /> {formatMbps(r.txBps)}
                    </span>
                    <span className="flex items-center gap-1 text-green-600 font-medium">
                      <ArrowDown className="w-3 h-3" /> {formatMbps(r.rxBps)}
                    </span>
                  </div>
                ) : (
                  <span className="text-xs text-gray-400">Calculando...</span>
                )}
              </div>
              {r && (
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400 w-4">↑</span>
                    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full transition-all duration-700 ${trafficColor(txMbps)}`}
                        style={{ width: `${Math.min((txMbps / maxMbps) * 100, 100)}%` }} />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400 w-4">↓</span>
                    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full transition-all duration-700"
                        style={{ width: `${Math.min((rxMbps / maxMbps) * 100, 100)}%` }} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ─── Bloque expandible por interfaz con IP pool ───────────────────────────────
const InterfaceIpBlock = ({ iface, poolIface }) => {
  const [open, setOpen]                   = useState(false);
  const [showAll, setShowAll]             = useState(false);
  const [filterOccupied, setFilterOccupied] = useState("all"); // "all" | "occupied" | "free"

  const ips       = iface.ips || [];
  const hasPool   = poolIface?.has_pool && poolIface?.cidrs?.length > 0;
  const firstPool = hasPool ? poolIface.cidrs[0] : null;

  const allIps = firstPool?.ips || [];
  const filteredIps = allIps.filter(ip => {
    if (filterOccupied === "occupied") return ip.occupied;
    if (filterOccupied === "free")     return !ip.occupied;
    return true;
  });
  const visibleIps = showAll ? filteredIps : filteredIps.slice(0, 20);

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-4 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={() => setOpen(v => !v)}
      >
        <div className="flex items-center gap-3">
          <span className={`w-2.5 h-2.5 rounded-full ${iface.running ? "bg-green-500" : "bg-gray-300"}`} />
          <span className="font-mono font-bold text-gray-800">{iface.name}</span>
          <span className="text-xs text-gray-400 bg-gray-200 px-2 py-0.5 rounded font-mono">
            {iface.type || "ether"}
          </span>
          {iface.comment && (
            <span className="text-xs text-gray-500 italic">"{iface.comment}"</span>
          )}
        </div>

        <div className="flex items-center gap-4">
          {/* CIDRs de la interfaz */}
          {ips.length > 0
            ? ips.map(ip => (
                <span key={ip.address} className="font-mono text-sm text-indigo-600 font-semibold">
                  {ip.address}
                </span>
              ))
            : <span className="text-xs text-gray-400">Sin IP</span>
          }

          {/* Mini resumen del pool si está disponible */}
          {hasPool && (
            <div className="flex items-center gap-2 text-xs">
              <span className="flex items-center gap-1 text-red-600 font-semibold">
                <CircleDot className="w-3 h-3" /> {firstPool.occupied} ocupadas
              </span>
              <span className="text-gray-300">·</span>
              <span className="flex items-center gap-1 text-green-600 font-semibold">
                {firstPool.free} libres
              </span>
              <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${
                firstPool.pct_used >= 90 ? "bg-red-100 text-red-700" :
                firstPool.pct_used >= 70 ? "bg-amber-100 text-amber-700" :
                "bg-indigo-100 text-indigo-700"
              }`}>
                {firstPool.pct_used}%
              </span>
            </div>
          )}

          {open
            ? <ChevronUp className="w-4 h-4 text-gray-400" />
            : <ChevronDown className="w-4 h-4 text-gray-400" />
          }
        </div>
      </div>

      {/* Contenido expandido */}
      {open && (
        <div className="bg-white">
          {!hasPool ? (
            <div className="px-5 py-6 text-sm text-gray-400 italic text-center">
              Sin rango IPv4 configurado en esta interfaz
            </div>
          ) : (
            <>
              {/* Barra de uso + filtros */}
              <div className="px-5 py-4 border-b border-gray-100">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-gray-500">
                    {firstPool.cidr} — {firstPool.total} IPs totales
                  </span>
                  <span className="text-xs text-gray-400">
                    {firstPool.occupied} usadas · {firstPool.free} libres
                  </span>
                </div>
                <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${poolBarColor(firstPool.pct_used)}`}
                    style={{ width: `${firstPool.pct_used}%` }}
                  />
                </div>

                {/* Filtros */}
                <div className="flex items-center gap-2 mt-3">
                  {[
                    { value: "all",      label: `Todas (${allIps.length})`        },
                    { value: "occupied", label: `Ocupadas (${firstPool.occupied})` },
                    { value: "free",     label: `Libres (${firstPool.free})`       },
                  ].map(f => (
                    <button key={f.value}
                      onClick={(e) => { e.stopPropagation(); setFilterOccupied(f.value); setShowAll(false); }}
                      className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                        filterOccupied === f.value
                          ? "bg-indigo-600 text-white"
                          : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                      }`}>
                      {f.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tabla de IPs */}
              <div className="max-h-80 overflow-y-auto">
                {/* Header tabla */}
                <div className="grid grid-cols-12 bg-gray-50 border-b border-gray-100 px-5 py-2 sticky top-0">
                  <span className="col-span-3 text-xs font-semibold text-gray-400">IP</span>
                  <span className="col-span-1 text-xs font-semibold text-gray-400">Estado</span>
                  <span className="col-span-4 text-xs font-semibold text-gray-400">Cliente</span>
                  <span className="col-span-2 text-xs font-semibold text-gray-400">Servicio</span>
                  <span className="col-span-2 text-xs font-semibold text-gray-400">PPPoE / Tipo</span>
                </div>

                {/* Filas */}
                {visibleIps.map((ip, i) => (
                  <div key={i}
                    className={`grid grid-cols-12 px-5 py-2.5 border-b border-gray-50 text-xs
                      ${ip.occupied ? "hover:bg-red-50/30" : "hover:bg-green-50/30"} transition-colors`}>
                    <span className="col-span-3 font-mono font-semibold text-gray-800">{ip.ip}</span>
                    <span className="col-span-1">
                      {ip.occupied
                        ? <span className="w-2 h-2 bg-red-500 rounded-full inline-block" />
                        : <span className="w-2 h-2 bg-green-400 rounded-full inline-block" />
                      }
                    </span>
                    <span className="col-span-4 font-medium text-gray-700 truncate">
                      {ip.occupied
                        ? ip.client_name
                        : <span className="text-gray-300 italic">—</span>
                      }
                    </span>
                    <span className="col-span-2">
                      {ip.occupied && (
                        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${statusBadge(ip.status)}`}>
                          {statusLabel(ip.status)}
                        </span>
                      )}
                    </span>
                    <span className="col-span-2 text-gray-400 font-mono truncate">
                      {ip.occupied
                        ? (ip.pppoe_username || (ip.connection_type === "fiber" ? "Fibra" : "Antena"))
                        : null
                      }
                    </span>
                  </div>
                ))}

                {/* Ver más */}
                {!showAll && filteredIps.length > 20 && (
                  <div className="px-5 py-3 text-center border-t border-gray-100">
                    <button
                      onClick={(e) => { e.stopPropagation(); setShowAll(true); }}
                      className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">
                      Ver {filteredIps.length - 20} IPs más...
                    </button>
                  </div>
                )}

                {filteredIps.length === 0 && (
                  <div className="px-5 py-6 text-center text-xs text-gray-400 italic">
                    No hay IPs en este filtro
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

// ─── Panel de interfaces ──────────────────────────────────────────────────────
const InterfacesPanel = ({ interfaces, poolData, loadingPool }) => {
  const withIp    = interfaces.filter(i => i.ips?.length > 0);
  const withoutIp = interfaces.filter(i => !i.ips?.length);

  // Mapa rápido nombre → datos de pool
  const poolMap = {};
  (poolData?.interfaces || []).forEach(p => { poolMap[p.name] = p; });

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
      <div className="flex items-center gap-2 mb-5">
        <Network className="w-5 h-5 text-indigo-600" />
        <h3 className="font-bold text-gray-800">Interfaces del Router</h3>
        <span className="ml-2 px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs font-medium">
          {interfaces.length} interfaces
        </span>

        {/* Spinner mientras carga el pool */}
        {loadingPool && (
          <span className="flex items-center gap-1.5 text-xs text-indigo-500 ml-2">
            <div className="w-3 h-3 border-2 border-indigo-200 border-t-indigo-500 rounded-full animate-spin" />
            Cargando pool de IPs...
          </span>
        )}

        <div className="ml-auto flex items-center gap-3 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-green-500 rounded-full" /> Con IP: {withIp.length}
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-gray-300 rounded-full" /> Sin IP: {withoutIp.length}
          </span>
        </div>
      </div>

      <div className="space-y-2">
        {withIp.map(iface => (
          <InterfaceIpBlock
            key={iface.name}
            iface={iface}
            poolIface={poolMap[iface.name]}
          />
        ))}

        {withoutIp.length > 0 && (
          <div className="mt-4">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2 px-1">Sin dirección IP</p>
            <div className="grid grid-cols-3 gap-2">
              {withoutIp.map(iface => (
                <div key={iface.name} className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-100">
                  <span className={`w-2 h-2 rounded-full ${iface.running ? "bg-green-400" : "bg-gray-300"}`} />
                  <span className="font-mono text-sm text-gray-600">{iface.name}</span>
                  <span className="text-xs text-gray-400 ml-auto">{iface.type || "—"}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Tab OLT ──────────────────────────────────────────────────────────────────
const OltConnectForm = ({ onConnect, connecting }) => {
  const [form, setForm] = useState({
    host: "", ssh_username: "admin", ssh_password: "",
    ssh_port: "22", brand: "zte",
  });
  const [showPass, setShowPass] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.host.trim())         return toast.error("Ingresa la IP de la OLT");
    if (!form.ssh_username.trim()) return toast.error("Ingresa el usuario SSH");
    if (!form.ssh_password.trim()) return toast.error("Ingresa la contraseña SSH");
    if (!form.brand)               return toast.error("Selecciona la marca");
    onConnect({ ...form, ssh_port: parseInt(form.ssh_port) || 22 });
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-teal-50 rounded-xl">
          <Cable className="w-6 h-6 text-teal-600" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-gray-900">Conectar a la OLT</h2>
          <p className="text-sm text-gray-500">Ingresa las credenciales SSH de la OLT</p>
        </div>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-gray-500 mb-1">
            IP / Host OLT <span className="text-red-500">*</span>
          </label>
          <input type="text" name="host" value={form.host} onChange={handleChange}
            placeholder="ej: 192.168.1.10"
            className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 font-mono" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Usuario SSH</label>
            <input type="text" name="ssh_username" value={form.ssh_username} onChange={handleChange}
              placeholder="admin"
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Contraseña SSH</label>
            <div className="relative">
              <input type={showPass ? "text" : "password"} name="ssh_password"
                value={form.ssh_password} onChange={handleChange} placeholder="••••••••"
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 pr-9 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500" />
              <button type="button" onClick={() => setShowPass(v => !v)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Puerto SSH</label>
            <input type="number" name="ssh_port" value={form.ssh_port} onChange={handleChange}
              placeholder="22"
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 font-mono" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">
              Marca <span className="text-red-500">*</span>
            </label>
            <select name="brand" value={form.brand} onChange={handleChange}
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white">
              <option value="zte">ZTE</option>
              <option value="vsol">VSOL</option>
              <option value="huawei">Huawei</option>
              <option value="fiberhome">FiberHome</option>
            </select>
          </div>
        </div>
        <button type="submit" disabled={connecting}
          className="w-full flex items-center justify-center gap-2 py-3 bg-teal-600 text-white text-sm font-semibold rounded-xl hover:bg-teal-700 disabled:opacity-50 transition-colors mt-2">
          {connecting
            ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Conectando...</>
            : <><Cable className="w-4 h-4" /> Conectar OLT</>}
        </button>
      </form>
    </div>
  );
};

const OltSystemCard = ({ info, onDisconnect, authMode, onAuthModeChange }) => (
  <div className="bg-white rounded-2xl border border-green-200 shadow-sm p-6">
    <div className="flex items-start justify-between mb-5">
      <div className="flex items-center gap-3">
        <div className="p-3 bg-teal-50 rounded-xl">
          <Cable className="w-6 h-6 text-teal-600" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-gray-900">
              {info.brand?.toUpperCase()} — {info.model || info.board_name || "OLT"}
            </h2>
            <span className="flex items-center gap-1 text-xs font-medium text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" /> Conectada
            </span>
          </div>
          <p className="text-sm text-gray-500 font-mono mt-0.5">{info.host}</p>
        </div>
      </div>
      <button onClick={onDisconnect}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-500 border border-gray-300 rounded-lg hover:bg-gray-50">
        <X className="w-3.5 h-3.5" /> Desconectar
      </button>
    </div>
    <div className="grid grid-cols-4 gap-4">
      {[
        { label: "Versión", value: info.version     || "—" },
        { label: "Uptime",  value: info.uptime      || "—" },
        { label: "Puertos", value: info.total_ports || "—" },
      ].map(({ label, value }) => (
        <div key={label} className="bg-gray-50 rounded-xl p-4 border border-gray-100">
          <p className="text-xs font-semibold text-gray-400 mb-1">{label}</p>
          <p className="text-sm font-bold text-gray-800">{value}</p>
        </div>
      ))}
      <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
        <p className="text-xs font-semibold text-gray-400 mb-2">Auth ONUs</p>
        <div className="flex gap-1">
          {["manual", "auto"].map(mode => (
            <button key={mode} onClick={() => onAuthModeChange(mode)}
              className={`flex-1 text-xs font-semibold py-1 rounded-lg transition-colors ${
                authMode === mode
                  ? mode === "manual" ? "bg-amber-500 text-white" : "bg-green-500 text-white"
                  : "bg-gray-200 text-gray-500 hover:bg-gray-300"
              }`}>
              {mode === "manual" ? "Manual" : "Auto"}
            </button>
          ))}
        </div>
      </div>
    </div>
  </div>
);

const OltTab = () => {
  const [oltInfo, setOltInfo]         = useState(null);
  const [creds, setCreds]             = useState(null);
  const [connecting, setConnecting]   = useState(false);
  const [unauthOnus, setUnauthOnus]   = useState([]);
  const [loadingOnus, setLoadingOnus] = useState(false);
  const [authMode, setAuthMode]       = useState("manual");

  const handleConnect = async (formCreds) => {
    setConnecting(true);
    try {
      const res = await api.post("/olt/connect-direct", formCreds);
      if (!res.data.connected) {
        toast.error(res.data.error || "No se pudo conectar a la OLT");
        return;
      }
      setOltInfo(res.data);
      setCreds(formCreds);
      setUnauthOnus(res.data.unauthorized_onus || []);
      toast.success(`OLT conectada — ${res.data.total_unauthorized} ONUs pendientes`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al conectar OLT");
    } finally { setConnecting(false); }
  };

  const handleDisconnect = () => {
    setOltInfo(null);
    setCreds(null);
    setUnauthOnus([]);

  };

  const handleRefreshOnus = async () => {
    if (!creds) return;
    setLoadingOnus(true);
    try {
      const res = await api.post("/olt/connect-direct", creds);
      setUnauthOnus(res.data.unauthorized_onus || []);
      toast.success("ONUs actualizadas");
    } catch { toast.error("Error al actualizar ONUs"); }
    finally { setLoadingOnus(false); }
  };

  if (!oltInfo) {
    return (
      <div>
        <OltConnectForm onConnect={handleConnect} connecting={connecting} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <OltSystemCard
        info={oltInfo}
        onDisconnect={handleDisconnect}
        authMode={authMode}
        onAuthModeChange={setAuthMode}
      />
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center gap-2 mb-4">
          <AlertCircle className="w-5 h-5 text-amber-500" />
          <h3 className="font-bold text-gray-800">
            {authMode === "manual" ? "ONUs No Autorizadas" : "ONUs Detectadas (Auto-provisioning)"}
          </h3>
          {unauthOnus.length > 0 && (
            <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full text-xs font-bold">
              {unauthOnus.length} {authMode === "manual" ? "esperando" : "detectadas"}
            </span>
          )}
          <button onClick={handleRefreshOnus} disabled={loadingOnus}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-teal-600 border border-teal-200 bg-teal-50 rounded-lg hover:bg-teal-100">
            <RefreshCw className={`w-3 h-3 ${loadingOnus ? "animate-spin" : ""}`} />
            Actualizar
          </button>
        </div>

        {authMode === "auto" && (
          <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 mb-4 text-xs text-green-700">
            ✅ Esta OLT tiene <strong>auto-provisioning activo</strong> — las ONUs se autorizan
            automáticamente al conectarse. Solo necesitas registrar el serial en la conexión del cliente.
          </div>
        )}

        {loadingOnus ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-6 h-6 border-2 border-teal-200 border-t-teal-600 rounded-full animate-spin mr-3" />
            <span className="text-sm text-gray-500">Buscando ONUs...</span>
          </div>
        ) : unauthOnus.length === 0 ? (
          <div className="text-center py-8">
            <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-green-400" />
            <p className="text-sm font-medium text-green-600">Sin ONUs pendientes</p>
            <p className="text-xs text-gray-400 mt-1">
              {authMode === "manual"
                ? "Todas las ONUs están autorizadas"
                : "No hay nuevas ONUs detectadas"}
            </p>
          </div>
        ) : (
          <div className="border border-gray-200 rounded-xl overflow-hidden">
            <div className="grid grid-cols-12 bg-gray-50 border-b border-gray-200 px-4 py-2">
              <span className="col-span-4 text-xs font-semibold text-gray-500">Serial</span>
              <span className="col-span-2 text-xs font-semibold text-gray-500">Slot</span>
              <span className="col-span-2 text-xs font-semibold text-gray-500">PON Port</span>
              <span className="col-span-3 text-xs font-semibold text-gray-500">Modelo</span>
              <span className="col-span-1 text-xs font-semibold text-gray-500">Estado</span>
            </div>
            <div className="divide-y divide-gray-100">
              {unauthOnus.map((onu, i) => (
                <div key={i} className="grid grid-cols-12 px-4 py-3 hover:bg-amber-50/40 transition-colors">
                  <span className="col-span-4 font-mono text-sm font-semibold text-gray-800">{onu.serial_number}</span>
                  <span className="col-span-2 text-sm text-gray-600">{onu.slot}</span>
                  <span className="col-span-2 text-sm text-gray-600">{onu.pon_port}</span>
                  <span className="col-span-3 text-sm text-gray-500">{onu.model || "—"}</span>
                  <span className="col-span-1">
                    <span className="flex items-center gap-1 text-xs font-medium text-amber-600">
                      <span className="w-1.5 h-1.5 bg-amber-500 rounded-full animate-pulse" />
                      {authMode === "manual" ? "Pendiente" : "Detectada"}
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Componente principal ──────────────────────────────────────────────────────
export default function NodosRedPage() {
  const [activeTab, setActiveTab]     = useState("mikrotik");
  const [creds, setCreds]             = useState(null);
  const [connecting, setConnecting]   = useState(false);
  const [sysInfo, setSysInfo]         = useState(null);
  const [poolData, setPoolData]       = useState(null);
  const [loadingPool, setLoadingPool] = useState(false);

  useEffect(() => { window.scrollTo(0, 0); }, []);

  const handleConnect = async (formCreds) => {
    setConnecting(true);
    try {
      // 1. System info — CPU, RAM, interfaces básicas
      const res = await api.post("/mikrotik/system-info", {
        host:     formCreds.host,
        username: formCreds.username,
        password: formCreds.password,
        port:     formCreds.port,
        use_ssl:  formCreds.use_ssl,
      });
      setSysInfo(res.data);
      setCreds(formCreds);
      toast.success(`Conectado a ${res.data.identity || formCreds.host}`);

      // localstorage
localStorage.setItem("netkeeper_mk_interfaces", JSON.stringify({
  host: formCreds.host,
  interfaces: res.data.interfaces,
}));

      // 2. IP pool en vivo — en paralelo, no bloquea la UI
      setLoadingPool(true);
      api.post("/mikrotik/ip-pool-live", {
        host:     formCreds.host,
        username: formCreds.username,
        password: formCreds.password,
        port:     formCreds.port,
        use_ssl:  formCreds.use_ssl,
      })
        .then(r => setPoolData(r.data))
        .catch(() => { /* silencioso — pool es complementario */ })
        .finally(() => setLoadingPool(false));

    } catch (err) {
      toast.error(err.response?.data?.detail || "No se pudo conectar al MikroTik");
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = () => {
    setCreds(null);
    setSysInfo(null);
    setPoolData(null);
    localStorage.removeItem("netkeeper_mk_interfaces"); 

  };

  const tabs = [
    { id: "mikrotik", label: "MikroTik",  icon: Router, color: "text-red-600",  bg: "bg-red-50"  },
    { id: "olt",      label: "OLT Fibra", icon: Cable,  color: "text-teal-600", bg: "bg-teal-50" },
  ];

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Nodos de Red</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Gestiona el equipamiento de red — MikroTik y OLT de fibra
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-gray-200">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}>
              <Icon className={`w-4 h-4 ${activeTab === tab.id ? "text-blue-600" : ""}`} />
              {tab.label}
              {tab.id === "mikrotik" && sysInfo && (
                <span className="w-2 h-2 bg-green-500 rounded-full" />
              )}
            </button>
          );
        })}
      </div>

      {/* Tab MikroTik */}
      {activeTab === "mikrotik" && (
        <>
          {!sysInfo ? (
            <div>
              <ConnectForm onConnect={handleConnect} connecting={connecting} />
            </div>
          ) : (
            <div className="space-y-4">
              <SystemCard info={sysInfo} onDisconnect={handleDisconnect} />
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-1">
                  <TrafficMonitor creds={creds} />
                </div>
                <div className="col-span-2">
                  <InterfacesPanel
                    interfaces={sysInfo.interfaces || []}
                    poolData={poolData}
                    loadingPool={loadingPool}
                  />
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Tab OLT */}
      {activeTab === "olt" && <OltTab />}
    </div>
  );
}
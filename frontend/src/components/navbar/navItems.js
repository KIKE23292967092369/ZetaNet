/**
 * Estructura de navegación del navbar
 * Replica la estructura de iWisp: Clientes, Operaciones, Finanzas, Tickets, Inventario
 */
export const navItems = [
  {
  id: 'clientes',
  label: 'Clientes',
  children: [
    { label: 'Listado', path: '/clientes' },
    { label: 'Prospectos', path: '/prospectos' },
    { label: 'Localidades', path: '/localidades' },
  ],
},
 {
  id: 'operaciones',
  label: 'Operaciones',
  children: [
    { label: 'Conexiones',         path: '/conexiones' },
    { label: 'Células',            path: '/celulas' },
    { label: 'Planes de Servicio', path: '/planes' },
    { label: 'Nodos de Red',       path: '/nodos-red' },  // ← nuevo
  ],
},
  {
    id: 'finanzas',
    label: 'Finanzas',
    children: [
      { label: 'Facturación', path: '/facturacion' },
      { label: 'Grupos de Facturación', path: '/facturacion/grupos' },
    ],
  },
  {
    id: 'tickets',
    label: 'Tickets',
    path: '/tickets',
  },
  {
    id: 'inventario',
    label: 'Inventario',
    path: '/inventario',
  },
  {
    id: 'whatsapp',
    label: 'WhatsApp',
    path: '/whatsapp',
  },
]
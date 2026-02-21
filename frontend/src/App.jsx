import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import MainLayout from './layouts/MainLayout'
import ProtectedRoute from './routes/ProtectedRoute'
import LoginPage from './pages/auth/LoginPage'
import DashboardPage from './pages/dashboard/DashboardPage'
import ClientsPage from './pages/clients/ClientsPage'
import ClientCreatePage from './pages/clients/ClientCreatePage'
import BillingGroupsPage from './pages/billing/BillingGroupsPage'
import ProspectsPage from './pages/prospects/ProspectsPage'
import ProspectCreatePage from './pages/prospects/ProspectCreatePage'
import ProspectDetailPage from './pages/prospects/ProspectDetailPage'
import LocalitiesPage from './pages/localities/LocalitiesPage'
import ClientDetailPage from './pages/clients/ClientDetailPage'
import PlansPage from "./pages/plans/PlansPage";
import CellsPage from "./pages/cells/CellsPage";
import CellDetailPage from "./pages/cells/CellDetailPage";
import ConnectionsPage from "./pages/connections/ConnectionsPage";
import ConnectionDetailPage from "./pages/connections/ConnectionDetailPage";
import NodosRedPage from "./pages/network/NodosRedPage";



// Páginas placeholder para módulos futuros
const PlaceholderPage = ({ title }) => (
  <div className="flex items-center justify-center h-64">
    <div className="text-center">
      <h2 className="text-2xl font-bold text-gray-400 mb-2">{title}</h2>
      <p className="text-gray-400">Próximamente</p>
    </div>
  </div>
)

export default function App() {
  const { isAuthenticated } = useAuth()

  return (
    <Routes>
      {/* Ruta pública */}
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />}
      />

      {/* Rutas protegidas */}
      <Route element={<ProtectedRoute />}>
        <Route element={<MainLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />

          {/* Clientes — /nuevo ANTES de /:id para evitar conflicto */}
          <Route path="/clientes" element={<ClientsPage />} />
          <Route path="/clientes/nuevo" element={<ClientCreatePage />} />
          <Route path="/clientes/:id" element={<ClientDetailPage />} />
          
          {/* Conexiones */}
          <Route path="/conexiones" element={<ConnectionsPage />} />
          <Route path="/conexiones/nueva" element={<ConnectionsPage />} />
          <Route path="/conexiones/:id" element={<ConnectionDetailPage />} />

          {/* Prospectos — /nuevo ANTES de /:id */}
          <Route path="/prospectos" element={<ProspectsPage />} />
          <Route path="/prospectos/nuevo" element={<ProspectCreatePage />} />
          <Route path="/prospectos/:id" element={<ProspectDetailPage />} />

          {/* Operaciones */}
          <Route path="/conexiones" element={<ConnectionsPage />} />
          <Route path="/conexiones/:id" element={<ConnectionDetailPage />} />
          <Route path="/celulas" element={<CellsPage />} />
          <Route path="/planes" element={<PlansPage />} />
          <Route path="/celulas/:id" element={<CellDetailPage />} />
          <Route path="/nodos-red" element={<NodosRedPage />} />

        

          {/* Finanzas */}
          <Route path="/facturacion" element={<PlaceholderPage title="Facturación" />} />
          <Route path="/facturacion/grupos" element={<BillingGroupsPage />} />

          {/* Tickets */}
          <Route path="/tickets" element={<PlaceholderPage title="Tickets" />} />

          {/* Inventario */}
          <Route path="/inventario" element={<PlaceholderPage title="Inventario" />} />

          {/* WhatsApp */}
          <Route path="/whatsapp" element={<PlaceholderPage title="WhatsApp" />} />
          
           {/* localidades */}
          <Route path="/localidades" element={<LocalitiesPage />} />

          {/* Configuración */}
          <Route path="/configuracion" element={<PlaceholderPage title="Configuración" />} />
        </Route>
      </Route>

      {/* Redirect default */}
      <Route path="*" element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />} />
    </Routes>
  )
}
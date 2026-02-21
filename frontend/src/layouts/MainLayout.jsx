import { Outlet } from 'react-router-dom'
import Navbar from '../components/navbar/Navbar'

export default function MainLayout() {
  return (
    <div className="min-h-screen bg-gray-100" style={{ zoom: '220%' }}>
      <Navbar />
      <main className="px-8 py-6">
        <Outlet />
      </main>
    </div>
  )
}
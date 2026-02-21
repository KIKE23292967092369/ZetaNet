import { useState, useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import { AuthContext } from '../../context/AuthContext'
import { Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useContext(AuthContext)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email || !password) {
      toast.error('Ingresa correo y contraseña')
      return
    }

    setLoading(true)
    try {
      const success = await login(email, password)
      if (success) navigate('/dashboard')
    } catch (err) {
      const detail = err.response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : 'Credenciales incorrectas')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{ zoom: 2.8 }}
      className="fixed inset-0 flex flex-col overflow-hidden"
    >
      {/* ── Mitad superior: blanco ── */}
      <div className="flex-1 bg-white" />

      {/* ── Mitad inferior: azul gradiente ── */}
      <div className="flex-1 bg-gradient-to-b from-blue-500 to-blue-700" />

      {/* ── Card centrada (superpuesta) ── */}
      <div className="absolute inset-0 flex flex-col items-center justify-center px-4">
        {/* Logo */}
        <img
          src="/zetanet-logo.png"
          alt="ZetaNet"
          className="h-28 mb-2"
        />

        {/* Bienvenido */}
        <p className="text-gray-500 text-sm mb-6">Bienvenido</p>

        {/* Card de login */}
        <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-1">Iniciar sesión</h2>
          <p className="text-sm text-gray-500 mb-6">Ingresa tus credenciales para acceder</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Correo electrónico
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@miISP.com"
                autoComplete="email"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Contraseña
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
              />
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? 'Ingresando...' : 'Ingresar'}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-blue-100 text-xs mt-6">
          ZetaNet v1.0 — Plataforma SaaS Multi-Tenant
        </p>
      </div>
    </div>
  )
}
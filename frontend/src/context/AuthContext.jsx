import { createContext, useState, useCallback, useEffect } from 'react'
import api from '../api/axios'
import toast from 'react-hot-toast'

export const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user')
    return saved ? JSON.parse(saved) : null
  })
  const [loading, setLoading] = useState(false)

  const isAuthenticated = !!user && !!localStorage.getItem('access_token')

  const login = useCallback(async (email, password) => {
    setLoading(true)
    try {
      const { data } = await api.post('/auth/login', { email, password })

      localStorage.setItem('access_token', data.access_token)
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token)
      }

      // Obtener datos del usuario desde la respuesta
      const u = data.user || {}
      const userInfo = {
        id: u.id || data.user_id,
        email: u.email || email,
        name: u.full_name || u.name || email.split('@')[0],
        role: u.role || 'admin',
        tenant_id: u.tenant_id || data.tenant_id,
        tenant_name: data.tenant_name || 'Mi ISP',
      }

      localStorage.setItem('user', JSON.stringify(userInfo))
      setUser(userInfo)
      toast.success(`¡Bienvenido, ${userInfo.name}!`)
      return true
    } catch (error) {
      const detail = error.response?.data?.detail
      const message = typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map(e => e.msg).join(', ')
          : 'Credenciales incorrectas'
      toast.error(message)
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    setUser(null)
    toast.success('Sesión cerrada')
  }, [])

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token && user) {
      setUser(null)
    }
  }, [user])

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
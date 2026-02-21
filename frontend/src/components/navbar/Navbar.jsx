import { useState, useRef, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  Bell, ChevronDown, LogOut, User, Settings,
  Menu, X
} from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { navItems } from './navItems'

export default function Navbar() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [openMenu, setOpenMenu] = useState(null)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const navRef = useRef(null)
  const userRef = useRef(null)

  // Cerrar menús al hacer click fuera
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (navRef.current && !navRef.current.contains(e.target)) {
        setOpenMenu(null)
      }
      if (userRef.current && !userRef.current.contains(e.target)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Cerrar menús al cambiar de ruta
  useEffect(() => {
    setOpenMenu(null)
    setUserMenuOpen(false)
    setMobileMenuOpen(false)
  }, [location.pathname])

  const toggleMenu = (menuId) => {
    setOpenMenu(openMenu === menuId ? null : menuId)
  }

  const isActive = (item) => {
    if (item.path) return location.pathname === item.path
    if (item.children) {
      return item.children.some((child) => location.pathname === child.path)
    }
    return false
  }

  return (
    <nav className="bg-brand-700 shadow-lg relative z-50">
      <div className="max-w-full mx-auto px-4">
        <div className="flex items-center h-16">
          {/* Logo */}
          <Link to="/dashboard" className="shrink-0">
            <img src="/logo-white.png" alt="ZetaNet" className="h-12" />
          </Link>

          {/* Menú Desktop */}
          <div ref={navRef} className="hidden lg:flex items-center gap-2 ml-4">
            {navItems.map((item) => (
              <div key={item.id} className="relative">
                {item.children ? (
                  /* Item con dropdown */
                  <button
                    onClick={() => toggleMenu(item.id)}
                    className={`flex items-center gap-1 px-4 py-2.5 rounded-md text-[15px] font-medium transition-colors
                      ${isActive(item)
                        ? 'bg-brand-800 text-white'
                        : 'text-blue-100 hover:bg-brand-600 hover:text-white'
                      }`}
                  >
                    {item.label}
                    <ChevronDown
                      size={14}
                      className={`transition-transform ${openMenu === item.id ? 'rotate-180' : ''}`}
                    />
                  </button>
                ) : (
                  /* Item sin dropdown */
                  <Link
                    to={item.path}
                    className={`flex items-center px-4 py-2.5 rounded-md text-[15px] font-medium transition-colors
                      ${isActive(item)
                        ? 'bg-brand-800 text-white'
                        : 'text-blue-100 hover:bg-brand-600 hover:text-white'
                      }`}
                  >
                    {item.label}
                  </Link>
                )}

                {/* Dropdown */}
                {item.children && openMenu === item.id && (
                  <div className="absolute top-full left-0 mt-1 w-52 bg-gray-800 rounded-lg shadow-xl py-1 dropdown-enter">
                    {item.children.map((child) => (
                      <Link
                        key={child.path}
                        to={child.path}
                        className={`block px-4 py-2.5 text-sm transition-colors
                          ${location.pathname === child.path
                            ? 'bg-brand-600 text-white'
                            : 'text-gray-200 hover:bg-gray-700 hover:text-white'
                          }`}
                      >
                        {child.label}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Lado derecho */}
          <div className="flex items-center gap-3 ml-auto">
            {/* Notificaciones */}
            <button className="relative text-blue-100 hover:text-white p-1.5 rounded hover:bg-brand-600 transition-colors">
              <Bell size={20} />
              <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                3
              </span>
            </button>

            {/* Menú usuario */}
            <div ref={userRef} className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 text-blue-100 hover:text-white px-2 py-1.5 rounded hover:bg-brand-600 transition-colors"
              >
                <div className="w-7 h-7 bg-brand-500 rounded-full flex items-center justify-center">
                  <User size={14} className="text-white" />
                </div>
                <span className="text-sm font-medium hidden md:block">
                  {user?.name || 'Usuario'}
                </span>
                <ChevronDown size={14} />
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 top-full mt-1 w-56 bg-white rounded-lg shadow-xl border border-gray-200 py-1 dropdown-enter">
                  <div className="px-4 py-3 border-b border-gray-100">
                    <p className="text-sm font-semibold text-gray-900">{user?.name}</p>
                    <p className="text-xs text-gray-500">{user?.email}</p>
                    <p className="text-xs text-brand-600 font-medium mt-0.5">
                      {user?.tenant_name}
                    </p>
                  </div>
                  <Link
                    to="/configuracion"
                    className="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
                  >
                    <Settings size={16} />
                    Configuración
                  </Link>
                  <button
                    onClick={logout}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 w-full"
                  >
                    <LogOut size={16} />
                    Cerrar sesión
                  </button>
                </div>
              )}
            </div>

            {/* Botón mobile */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden text-blue-100 hover:text-white p-1.5"
            >
              {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>
      </div>

      {/* Menú Mobile */}
      {mobileMenuOpen && (
        <div className="lg:hidden bg-brand-800 border-t border-brand-600 py-2 px-4">
          {navItems.map((item) => (
            <div key={item.id}>
              {item.children ? (
                <>
                  <button
                    onClick={() => toggleMenu(item.id)}
                    className="flex items-center justify-between w-full px-3 py-2.5 text-sm text-blue-100 hover:text-white rounded"
                  >
                    {item.label}
                    <ChevronDown
                      size={14}
                      className={`transition-transform ${openMenu === item.id ? 'rotate-180' : ''}`}
                    />
                  </button>
                  {openMenu === item.id && (
                    <div className="ml-4 border-l-2 border-brand-500 pl-3">
                      {item.children.map((child) => (
                        <Link
                          key={child.path}
                          to={child.path}
                          className="block px-3 py-2 text-sm text-blue-200 hover:text-white"
                        >
                          {child.label}
                        </Link>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <Link
                  to={item.path}
                  className="block px-3 py-2.5 text-sm text-blue-100 hover:text-white rounded"
                >
                  {item.label}
                </Link>
              )}
            </div>
          ))}
        </div>
      )}
    </nav>
  )
}
import { NavLink, Outlet } from 'react-router-dom'
import { BarChart2, Clock, Bell, Users, AlertTriangle } from 'lucide-react'

const nav = [
  { to: '/',          label: '用量总览',   icon: BarChart2 },
  { to: '/workspace', label: '工作目录',   icon: Clock },
  { to: '/spend',     label: '支出管理',   icon: Users },
  { to: '/alerts',    label: '告警配置',   icon: Bell },
  { to: '/events',    label: '告警历史',   icon: AlertTriangle },
]

export default function Layout() {
  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-5 py-4 border-b border-gray-100">
          <span className="text-lg font-bold text-brand-600">Cursor Admin</span>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-50 text-brand-600'
                    : 'text-gray-600 hover:bg-gray-100'
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-3 border-t border-gray-100 text-xs text-gray-400">
          Cursor Team Admin
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto bg-gray-50">
        <Outlet />
      </main>
    </div>
  )
}

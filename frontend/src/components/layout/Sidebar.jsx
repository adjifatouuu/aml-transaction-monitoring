import { NavLink } from 'react-router-dom';
import {
  BellAlertIcon,
  MagnifyingGlassIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';

const NAV_ITEMS = [
  { to: '/alertes',       label: 'Alertes',       Icon: BellAlertIcon },
  { to: '/investigation', label: 'Investigation',  Icon: MagnifyingGlassIcon },
  { to: '/dashboard',     label: 'Dashboard',      Icon: ChartBarIcon },
  { to: '/parametres',    label: 'Paramètres',     Icon: Cog6ToothIcon },
];

export default function Sidebar() {
  return (
    <aside className="fixed top-0 left-0 h-screen w-[240px] bg-slate-800 flex flex-col z-30">
      {/* Logo */}
      <div className="h-16 flex items-center gap-2.5 px-4 border-b border-slate-700 flex-shrink-0">
        <ShieldCheckIcon className="w-6 h-6 text-brand-500 flex-shrink-0" />
        <span className="text-white font-bold text-lg tracking-tight">AML Monitor</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto scrollbar-thin px-3 py-4 space-y-1">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 mb-3">
          Navigation
        </p>
        {NAV_ITEMS.map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${
                isActive
                  ? 'bg-brand-500 text-white'
                  : 'text-slate-400 hover:bg-slate-700 hover:text-white'
              }`
            }
          >
            <Icon className="w-5 h-5 flex-shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-700 p-4 flex-shrink-0">
        <p className="text-xs text-slate-500">v0.1.0 — Sprint 1</p>
      </div>
    </aside>
  );
}

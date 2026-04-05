import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Logo from "@/components/Logo";
import {
  LayoutDashboard,
  List,
  PlusCircle,
  Upload,
  FlaskConical,
  BarChart3,
  Tags,
  Download,
} from "lucide-react";

const navItems = [
  { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/admin/questions", label: "Questions", icon: List },
  { to: "/admin/create", label: "Create", icon: PlusCircle },
  { to: "/admin/batch", label: "Batch Import", icon: Upload },
  { to: "/admin/simulate", label: "Simulator", icon: FlaskConical },
  { to: "/admin/coverage", label: "Coverage", icon: BarChart3 },
  { to: "/admin/themes", label: "Themes", icon: Tags },
  { to: "/admin/export", label: "Export", icon: Download },
];

const AdminLayout: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 bg-legacy-navy text-white flex flex-col shrink-0">
        <div className="p-4 border-b border-white/10">
          <Logo className="text-white" />
          <p className="text-xs text-gray-300 mt-1">Admin Tool</p>
        </div>

        <nav className="flex-1 py-2">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                  isActive
                    ? "bg-legacy-purple text-white"
                    : "text-gray-300 hover:bg-white/10 hover:text-white"
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-white/10 text-xs text-gray-400">
          {user?.email}
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
};

export default AdminLayout;

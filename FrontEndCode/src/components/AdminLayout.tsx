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
  LogOut,
  ClipboardList,
  Settings,
  MessageSquare,
  Mail,
} from "lucide-react";

interface NavItem {
  to: string;
  label: string;
  icon: React.ElementType;
  end?: boolean;
}

interface NavSection {
  header: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    header: "QUESTIONS",
    items: [
      { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
      { to: "/admin/questions", label: "Browse", icon: List },
      { to: "/admin/create", label: "Create", icon: PlusCircle },
      { to: "/admin/batch", label: "Batch Import", icon: Upload },
      { to: "/admin/coverage", label: "Coverage", icon: BarChart3 },
      { to: "/admin/themes", label: "Themes", icon: Tags },
      { to: "/admin/simulate", label: "Simulator", icon: FlaskConical },
      { to: "/admin/export", label: "Export", icon: Download },
    ],
  },
  {
    header: "ASSESSMENTS",
    items: [
      { to: "/admin/assessments", label: "Manage", icon: ClipboardList },
    ],
  },
  {
    header: "FEEDBACK",
    items: [
      { to: "/admin/feedback", label: "Bugs & Requests", icon: MessageSquare },
    ],
  },
  {
    header: "BILLING",
    items: [
      { to: "/admin/coupons", label: "Coupons", icon: Tags },
    ],
  },
  {
    header: "MARKETING",
    items: [
      { to: "/admin/email-capture", label: "Email Capture", icon: Mail },
    ],
  },
  {
    header: "SYSTEM",
    items: [
      { to: "/admin/settings", label: "Settings", icon: Settings },
    ],
  },
];

const AdminLayout: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 bg-legacy-navy text-white flex flex-col shrink-0">
        <div className="p-4 border-b border-white/10">
          <Logo className="text-white" />
          <p className="text-xs text-gray-300 mt-1">Admin Tool</p>
          <div className="flex items-center justify-between mt-3">
            <p className="text-xs text-gray-400 truncate">{user?.email}</p>
            <button
              onClick={logout}
              className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors shrink-0 ml-2"
            >
              <LogOut className="h-3.5 w-3.5" />
              Log out
            </button>
          </div>
        </div>

        <nav className="flex-1 py-2 overflow-y-auto">
          {navSections.map((section) => (
            <div key={section.header}>
              <p className="text-[10px] uppercase tracking-wider text-gray-500 px-4 pt-4 pb-1">
                {section.header}
              </p>
              {section.items.map(({ to, label, icon: Icon, end }) => (
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
            </div>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
};

export default AdminLayout;

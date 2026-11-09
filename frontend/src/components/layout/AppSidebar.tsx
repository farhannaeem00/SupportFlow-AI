
import {
  Activity,
  BarChart3,
  BookOpen,
  Bot,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Code2,
  Download,
  LayoutDashboard,
  MessageSquare,
  Users,
  Webhook,
  X,
  Building2,
  UserRound,
  Sparkles,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

interface AppSidebarProps {
  collapsed: boolean
  mobileOpen: boolean
  onToggle: () => void
  onClose: () => void
}

const navigationGroups = [
  {
    label: 'WORKSPACE',
    items: [
      { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
      { label: 'Conversations', path: '/conversations', icon: MessageSquare },
      { label: 'Customers', path: '/customers', icon: Users },
      { label: 'AI Insights', path: '/ai-insights', icon: Sparkles },
    ],
  },
  {
    label: 'KNOWLEDGE & AI',
    items: [
      { label: 'Knowledge Base', path: '/knowledge-base', icon: BookOpen },
      { label: 'AI Settings', path: '/ai-settings', icon: Bot },
      { label: 'Support Widget', path: '/widget', icon: Code2 },
    ],
  },
  {
    label: 'MANAGEMENT',
    items: [
      { label: 'Team Members', path: '/team', icon: Users },
      { label: 'Organization', path: '/organization', icon: Building2 },
      { label: 'Usage & Limits', path: '/usage', icon: Activity },
      { label: 'Audit Logs', path: '/audit-logs', icon: ClipboardList },
      { label: 'Webhooks', path: '/webhooks', icon: Webhook },
      { label: 'Analytics', path: '/analytics', icon: BarChart3 },
      { label: 'Data Export', path: '/data-export', icon: Download },
    ],
  },
]

export default function AppSidebar({
  collapsed,
  mobileOpen,
  onToggle,
  onClose,
}: AppSidebarProps) {
  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          className="sidebar-backdrop"
          onClick={onClose}
        />
      )}

      <aside
        className={[
          'app-sidebar',
          collapsed ? 'app-sidebar--collapsed' : '',
          mobileOpen ? 'app-sidebar--mobile-open' : '',
        ].join(' ')}
      >
        <div className="sidebar-brand">
          <div className="brand-mark">
            <Bot size={23} strokeWidth={2.2} />
          </div>

          {!collapsed && (
            <div className="brand-copy">
              <span className="brand-name">SupportFlow</span>
              <span className="brand-label">AI WORKSPACE</span>
            </div>
          )}

          <button
            type="button"
            className="sidebar-mobile-close"
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <X size={19} />
          </button>
        </div>

        <div className="sidebar-organization">
          <div className="organization-avatar">S</div>
          {!collapsed && (
            <div className="organization-copy">
              <span className="organization-name">Your Organization</span>
              <span className="organization-plan">Workspace</span>
            </div>
          )}
          {!collapsed && <ChevronRight size={15} className="organization-chevron" />}
        </div>

        <nav className="sidebar-navigation">
          {navigationGroups.map((group) => (
            <section className="navigation-group" key={group.label}>
              {!collapsed && (
                <p className="navigation-group-label">{group.label}</p>
              )}

              {group.items.map((item) => {
                const Icon = item.icon

                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.path === '/dashboard'}
                    title={collapsed ? item.label : undefined}
                    onClick={onClose}
                    className={({ isActive }) =>
                      `sidebar-link ${isActive ? 'sidebar-link--active' : ''}`
                    }
                  >
                    <Icon size={19} strokeWidth={1.8} />
                    {!collapsed && <span>{item.label}</span>}
                    {item.label === 'Conversations' && !collapsed && (
                      <span className="sidebar-link-count">12</span>
                    )}
                  </NavLink>
                )
              })}
            </section>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-help">
            <div className="help-icon">
              <Sparkles size={17} />
            </div>
            {!collapsed && (
              <div className="help-copy">
                <strong>Need a hand?</strong>
                <span>Explore the help center</span>
              </div>
            )}
          </div>

          <div className="sidebar-profile">
            <div className="profile-avatar">FN</div>
            {!collapsed && (
              <div className="profile-copy">
                <strong>Workspace Admin</strong>
                <span>Administrator</span>
              </div>
            )}
            {!collapsed && <UserRound size={17} className="profile-menu-icon" />}
          </div>
        </div>

        <button
          type="button"
          className="sidebar-collapse-button"
          onClick={onToggle}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={17} /> : <ChevronLeft size={17} />}
        </button>
      </aside>
    </>
  )
}

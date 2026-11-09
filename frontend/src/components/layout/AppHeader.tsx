
import {
  Bell,
  ChevronDown,
  Menu,
  Search,
  Settings,
} from 'lucide-react'

interface AppHeaderProps {
  title: string
  description?: string
  onMenuClick: () => void
}

export default function AppHeader({
  title,
  description,
  onMenuClick,
}: AppHeaderProps) {
  return (
    <header className="app-header">
      <div className="header-heading">
        <button
          type="button"
          className="header-mobile-menu"
          onClick={onMenuClick}
          aria-label="Open navigation"
        >
          <Menu size={21} />
        </button>

        <div>
          <h1>{title}</h1>
          {description && <p>{description}</p>}
        </div>
      </div>

      <div className="header-actions">
        <button
          type="button"
          className="header-search"
          aria-label="Search"
          onClick={() => {
            // Global search will be connected in a later step.
          }}
        >
          <Search size={18} />
          <span>Search</span>
          <kbd>⌘ K</kbd>
        </button>

        <button
          type="button"
          className="header-icon-button"
          aria-label="Notifications"
        >
          <Bell size={19} />
          <span className="notification-indicator" />
        </button>

        <button
          type="button"
          className="header-icon-button"
          aria-label="Settings"
        >
          <Settings size={19} />
        </button>

        <div className="header-divider" />

        <button type="button" className="header-user">
          <span className="header-user-avatar">FN</span>
          <span className="header-user-name">Admin</span>
          <ChevronDown size={15} />
        </button>
      </div>
    </header>
  )
}

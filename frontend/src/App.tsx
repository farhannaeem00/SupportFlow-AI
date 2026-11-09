
import { useState } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import AppSidebar from './components/layout/AppSidebar'
import AppHeader from './components/layout/AppHeader'
import DashboardPage from './features/dashboard/DashboardPage'
import './App.css'

const pageDetails: Record<string, { title: string; description: string }> = {
  '/dashboard': {
    title: 'Dashboard',
    description: 'Monitor your customer support workspace.',
  },
  '/conversations': {
    title: 'Conversations',
    description: 'Manage and respond to customer conversations.',
  },
  '/customers': {
    title: 'Customers',
    description: 'View and manage your customer relationships.',
  },
  '/ai-insights': {
    title: 'AI Insights',
    description: 'Explore AI-powered conversation insights.',
  },
  '/knowledge-base': {
    title: 'Knowledge Base',
    description: 'Manage your support knowledge and documents.',
  },
  '/ai-settings': {
    title: 'AI Settings',
    description: 'Configure your AI assistant.',
  },
  '/widget': {
    title: 'Support Widget',
    description: 'Manage your website support widget.',
  },
  '/team': {
    title: 'Team Members',
    description: 'Manage your organization team.',
  },
  '/organization': {
    title: 'Organization',
    description: 'Manage your organization settings.',
  },
  '/usage': {
    title: 'Usage & Limits',
    description: 'Monitor resource usage and organization limits.',
  },
  '/audit-logs': {
    title: 'Audit Logs',
    description: 'Review organization activity and security events.',
  },
  '/webhooks': {
    title: 'Webhooks',
    description: 'Manage external integrations and webhook deliveries.',
  },
  '/analytics': {
    title: 'Analytics',
    description: 'Understand your customer support performance.',
  },
  '/data-export': {
    title: 'Data Export',
    description: 'Export your organization data.',
  },
}

function ComingSoonPage({ title }: { title: string }) {
  return (
    <section className="coming-soon-page">
      <div className="coming-soon-icon">
        <span>✦</span>
      </div>
      <h2>{title}</h2>
      <p>This workspace section is being built.</p>
      <span className="coming-soon-label">IN DEVELOPMENT</span>
    </section>
  )
}

function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  const currentPage =
    pageDetails[location.pathname] ?? pageDetails['/dashboard']

  return (
    <div className="app-shell">
      <AppSidebar
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onToggle={() => setCollapsed((previous) => !previous)}
        onClose={() => setMobileOpen(false)}
      />

      <div className="app-main">
        <AppHeader
          title={currentPage.title}
          description={currentPage.description}
          onMenuClick={() => setMobileOpen(true)}
        />

        <main className="app-content">
          <Routes>
            <Route path="/dashboard" element={<DashboardPage />} />
            {Object.keys(pageDetails)
              .filter((path) => path !== '/dashboard')
              .map((path) => (
                <Route
                  key={path}
                  path={path}
                  element={
                    <ComingSoonPage title={pageDetails[path].title} />
                  }
                />
              ))}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return <AppLayout />
}

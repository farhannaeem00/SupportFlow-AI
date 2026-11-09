
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Clock3,
  MessageSquare,
  MoreHorizontal,
  Sparkles,
  Users,
  Zap,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const activityData = [
  { day: 'Mon', conversations: 32 },
  { day: 'Tue', conversations: 45 },
  { day: 'Wed', conversations: 38 },
  { day: 'Thu', conversations: 61 },
  { day: 'Fri', conversations: 53 },
  { day: 'Sat', conversations: 76 },
  { day: 'Sun', conversations: 68 },
]

const recentConversations = [
  {
    initials: 'JD',
    name: 'James Davidson',
    subject: 'Unable to access my account',
    time: '2 min ago',
    status: 'Open',
    statusClass: 'status-open',
    color: 'avatar-purple',
  },
  {
    initials: 'SM',
    name: 'Sarah Mitchell',
    subject: 'Question about subscription plans',
    time: '14 min ago',
    status: 'Pending',
    statusClass: 'status-pending',
    color: 'avatar-blue',
  },
  {
    initials: 'RK',
    name: 'Robert King',
    subject: 'Payment confirmation request',
    time: '32 min ago',
    status: 'Resolved',
    statusClass: 'status-resolved',
    color: 'avatar-green',
  },
  {
    initials: 'EW',
    name: 'Emily Wilson',
    subject: 'How can I update my profile?',
    time: '48 min ago',
    status: 'Open',
    statusClass: 'status-open',
    color: 'avatar-orange',
  },
]

const metrics = [
  {
    label: 'Total conversations',
    value: '1,284',
    change: '+12.8%',
    direction: 'up',
    icon: MessageSquare,
    iconClass: 'metric-icon-purple',
    note: 'vs. previous period',
  },
  {
    label: 'Active customers',
    value: '856',
    change: '+8.2%',
    direction: 'up',
    icon: Users,
    iconClass: 'metric-icon-blue',
    note: 'vs. previous period',
  },
  {
    label: 'AI resolution rate',
    value: '78.4%',
    change: '+5.4%',
    direction: 'up',
    icon: Sparkles,
    iconClass: 'metric-icon-green',
    note: 'vs. previous period',
  },
  {
    label: 'Avg. response time',
    value: '2m 34s',
    change: '-14.2%',
    direction: 'down',
    icon: Clock3,
    iconClass: 'metric-icon-orange',
    note: 'vs. previous period',
  },
]

export default function DashboardPage() {
  return (
    <div className="dashboard-page">
      <section className="dashboard-welcome">
        <div>
          <div className="welcome-eyebrow">
            <span className="welcome-eyebrow-dot" />
            WORKSPACE OVERVIEW
          </div>
          <h2>Good morning, Admin <span>✦</span></h2>
          <p>Here&apos;s what&apos;s happening with your support team today.</p>
        </div>

        <div className="dashboard-date">
          <span className="dashboard-date-dot" />
          Last 7 days
          <span className="dashboard-date-chevron">⌄</span>
        </div>
      </section>

      <section className="metrics-grid">
        {metrics.map((metric) => {
          const Icon = metric.icon
          const ChangeIcon =
            metric.direction === 'up' ? ArrowUpRight : ArrowDownRight

          return (
            <article className="metric-card" key={metric.label}>
              <div className="metric-card-top">
                <span className="metric-label">{metric.label}</span>
                <span className={`metric-icon ${metric.iconClass}`}>
                  <Icon size={19} />
                </span>
              </div>

              <div className="metric-value">{metric.value}</div>

              <div className="metric-footer">
                <span className="metric-change">
                  <ChangeIcon size={15} />
                  {metric.change}
                </span>
                <span className="metric-note">{metric.note}</span>
              </div>
            </article>
          )
        })}
      </section>

      <section className="dashboard-main-grid">
        <article className="dashboard-card activity-card">
          <div className="card-heading">
            <div>
              <h3>Conversation activity</h3>
              <p>Conversation volume over the last 7 days</p>
            </div>
            <button
              type="button"
              className="card-more-button"
              aria-label="More activity options"
            >
              <MoreHorizontal size={20} />
            </button>
          </div>

          <div className="chart-summary">
            <strong>373</strong>
            <span>Total conversations</span>
            <span className="chart-summary-change">
              <ArrowUpRight size={14} /> 12.8%
            </span>
          </div>

          <div className="activity-chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={activityData}
                margin={{ top: 12, right: 8, left: -20, bottom: 0 }}
              >
                <defs>
                  <linearGradient
                    id="conversationGradient"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="0%"
                      stopColor="#6954e8"
                      stopOpacity={0.2}
                    />
                    <stop
                      offset="100%"
                      stopColor="#6954e8"
                      stopOpacity={0}
                    />
                  </linearGradient>
                </defs>

                <CartesianGrid
                  stroke="#eff0f5"
                  strokeDasharray="4 4"
                  vertical={false}
                />
                <XAxis
                  dataKey="day"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#9699aa', fontSize: 12 }}
                  dy={10}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#9699aa', fontSize: 12 }}
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={{
                    border: '1px solid #eeeef4',
                    borderRadius: 10,
                    boxShadow: '0 8px 24px rgba(25, 25, 55, 0.08)',
                    fontSize: 12,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="conversations"
                  stroke="#6954e8"
                  strokeWidth={2.5}
                  fill="url(#conversationGradient)"
                  activeDot={{ r: 5, strokeWidth: 0 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="dashboard-card resolution-card">
          <div className="card-heading">
            <div>
              <h3>AI performance</h3>
              <p>Automated support overview</p>
            </div>
            <span className="ai-live-label">
              <span /> AI ACTIVE
            </span>
          </div>

          <div className="resolution-visual">
            <div className="resolution-ring">
              <div className="resolution-ring-inner">
                <Sparkles size={21} />
                <strong>78.4%</strong>
                <span>AI resolved</span>
              </div>
            </div>
          </div>

          <div className="resolution-legend">
            <div>
              <span className="legend-dot legend-purple" />
              <span>AI resolved</span>
              <strong>78.4%</strong>
            </div>
            <div>
              <span className="legend-dot legend-gray" />
              <span>Needs human support</span>
              <strong>21.6%</strong>
            </div>
          </div>

          <div className="resolution-insight">
            <Zap size={16} />
            <span>Your AI assistant is handling most incoming conversations.</span>
          </div>
        </article>
      </section>

      <section className="dashboard-card conversations-card">
        <div className="card-heading">
          <div>
            <h3>Recent conversations</h3>
            <p>Stay up to date with your latest customer interactions</p>
          </div>
          <button type="button" className="view-all-button">
            View all <ArrowRight size={15} />
          </button>
        </div>

        <div className="conversation-table-wrap">
          <table className="conversation-table">
            <thead>
              <tr>
                <th>Customer</th>
                <th>Conversation</th>
                <th>Last activity</th>
                <th>Status</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {recentConversations.map((conversation) => (
                <tr key={conversation.name}>
                  <td>
                    <div className="conversation-customer">
                      <span className={`customer-avatar ${conversation.color}`}>
                        {conversation.initials}
                      </span>
                      <strong>{conversation.name}</strong>
                    </div>
                  </td>
                  <td className="conversation-subject">
                    {conversation.subject}
                  </td>
                  <td className="conversation-time">{conversation.time}</td>
                  <td>
                    <span className={`conversation-status ${conversation.statusClass}`}>
                      {conversation.status}
                    </span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="table-more-button"
                      aria-label={`More options for ${conversation.name}`}
                    >
                      <MoreHorizontal size={19} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <p className="dashboard-demo-note">
        Dashboard preview · Sample data for interface development
      </p>
    </div>
  )
}

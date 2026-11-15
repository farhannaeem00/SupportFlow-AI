
import type { ReactNode } from 'react'
import { Bot, ShieldCheck, Sparkles } from 'lucide-react'
import './AuthPage.css'

interface AuthLayoutProps {
  title: string
  description: string
  children: ReactNode
  footer: ReactNode
}

export default function AuthLayout({
  title,
  description,
  children,
  footer,
}: AuthLayoutProps) {
  return (
    <main className="auth-page">
      <section className="auth-showcase">
        <div className="auth-showcase-brand">
          <div className="auth-brand-mark">
            <Bot size={25} />
          </div>
          <span>SupportFlow <strong>AI</strong></span>
        </div>

        <div className="auth-showcase-content">
          <span className="auth-showcase-eyebrow">
            <Sparkles size={14} />
            INTELLIGENT CUSTOMER SUPPORT
          </span>

          <h1>
            Every conversation.
            <br />
            <span>One smarter workspace.</span>
          </h1>

          <p>
            Bring your conversations, knowledge, team, and AI-powered
            support workflows together in one place.
          </p>

          <div className="auth-showcase-feature">
            <div className="auth-feature-icon">
              <ShieldCheck size={20} />
            </div>
            <div>
              <strong>Built for secure collaboration</strong>
              <span>Your team and customer data stay organized.</span>
            </div>
          </div>
        </div>

        <div className="auth-showcase-bottom">
          <span>SUPPORTFLOW AI WORKSPACE</span>
          <span>© 2026 SupportFlow AI</span>
        </div>
      </section>

      <section className="auth-form-panel">
        <div className="auth-form-container">
          <div className="auth-mobile-brand">
            <div className="auth-brand-mark">
              <Bot size={22} />
            </div>
            <span>SupportFlow <strong>AI</strong></span>
          </div>

          <div className="auth-form-heading">
            <span className="auth-form-eyebrow">YOUR WORKSPACE</span>
            <h2>{title}</h2>
            <p>{description}</p>
          </div>

          {children}

          <div className="auth-form-footer">{footer}</div>

          <p className="auth-security-note">
            <ShieldCheck size={14} />
            Secure access to your workspace
          </p>
        </div>
      </section>
    </main>
  )
}


import { useState } from 'react'
import {
  Code2,
  Copy,
  ExternalLink,
  Globe,
  MessageCircle,
  ShieldCheck,
  Check,
  Info,
  ArrowUpRight,
} from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import './WidgetSettings.css'

type CopyTarget = 'url' | 'embed'

export default function WidgetSettingsPage() {
  const { organization } = useAuth()
  const [copied, setCopied] = useState<CopyTarget | null>(null)
  const [copyError, setCopyError] = useState('')

  const publicKey = organization?.public_key ?? ''

  const widgetUrl = publicKey
    ? `${window.location.origin}/widget/${encodeURIComponent(publicKey)}`
    : ''

  const embedCode = widgetUrl
    ? `<iframe
  src="${widgetUrl}"
  title="${organization?.name ?? 'Customer Support'}"
  width="420"
  height="680"
  style="border: 0; max-width: 100%;"
  loading="lazy"
></iframe>`
    : ''

  const handleCopy = async (
    value: string,
    target: CopyTarget,
  ) => {
    setCopyError('')

    try {
      await navigator.clipboard.writeText(value)
      setCopied(target)

      window.setTimeout(() => {
        setCopied((current) =>
          current === target ? null : current,
        )
      }, 2000)
    } catch {
      setCopyError(
        'Unable to access the clipboard. Please copy the text manually.',
      )
    }
  }

  const openWidget = () => {
    if (!widgetUrl) return
    window.open(widgetUrl, '_blank', 'noopener,noreferrer')
  }

  if (!organization) {
    return (
      <section className="widget-settings-page">
        <div className="widget-settings-empty">
          <Globe size={30} />
          <h2>No organization selected</h2>
          <p>
            Select or create an organization before configuring
            your support widget.
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="widget-settings-page">
      <header className="widget-settings-heading">
        <div>
          <div className="widget-settings-eyebrow">
            <Code2 size={14} />
            CUSTOMER EXPERIENCE
          </div>
          <h1>Support Widget</h1>
          <p>
            Connect your website visitors with your
            {` ${organization.name}`} support team.
          </p>
        </div>

        <button
          type="button"
          className="widget-primary-button"
          onClick={openWidget}
        >
          <ExternalLink size={16} />
          Preview widget
        </button>
      </header>

      <div className="widget-status-card">
        <div className="widget-status-icon">
          <MessageCircle size={23} />
        </div>

        <div className="widget-status-copy">
          <strong>Your support widget is ready</strong>
          <span>
            Your public customer chat widget is available
            for website integration.
          </span>
        </div>

        <span className="widget-status-badge">
          <span />
          Configured
        </span>
      </div>

      <div className="widget-settings-grid">
        <div className="widget-settings-main">
          <article className="widget-settings-card">
            <div className="widget-card-heading">
              <div className="widget-card-icon">
                <Globe size={19} />
              </div>
              <div>
                <h2>Public widget URL</h2>
                <p>
                  Share this link to let visitors contact
                  your support team.
                </p>
              </div>
            </div>

            <label className="widget-field-label">
              Your widget link
            </label>

            <div className="widget-copy-field">
              <input
                type="text"
                value={widgetUrl}
                readOnly
                aria-label="Public widget URL"
              />
              <button
                type="button"
                onClick={() => void handleCopy(widgetUrl, 'url')}
              >
                {copied === 'url' ? (
                  <Check size={16} />
                ) : (
                  <Copy size={16} />
                )}
                {copied === 'url' ? 'Copied' : 'Copy link'}
              </button>
            </div>

            <button
              type="button"
              className="widget-text-link"
              onClick={openWidget}
            >
              Open public widget
              <ArrowUpRight size={15} />
            </button>
          </article>

          <article className="widget-settings-card">
            <div className="widget-card-heading">
              <div className="widget-card-icon">
                <Code2 size={19} />
              </div>
              <div>
                <h2>Install on your website</h2>
                <p>
                  Embed your support widget into any website
                  that supports HTML.
                </p>
              </div>
            </div>

            <div className="widget-install-steps">
              <div className="widget-step">
                <span>1</span>
                <p>Copy the embed code below.</p>
              </div>
              <div className="widget-step">
                <span>2</span>
                <p>
                  Open your website's HTML or page editor.
                </p>
              </div>
              <div className="widget-step">
                <span>3</span>
                <p>
                  Paste the code where you want the chat
                  widget to appear.
                </p>
              </div>
            </div>

            <div className="widget-code-header">
              <span>
                <Code2 size={14} />
                HTML EMBED CODE
              </span>
              <button
                type="button"
                onClick={() => void handleCopy(embedCode, 'embed')}
              >
                {copied === 'embed' ? (
                  <Check size={15} />
                ) : (
                  <Copy size={15} />
                )}
                {copied === 'embed' ? 'Copied' : 'Copy code'}
              </button>
            </div>

            <pre className="widget-code-block">
              <code>{embedCode}</code>
            </pre>

            <div className="widget-info-note">
              <Info size={17} />
              <p>
                The embedded widget loads from your SupportFlow
                application. Your website must be able to access
                the deployed application URL.
              </p>
            </div>
          </article>

          {copyError && (
            <div className="widget-copy-error">
              {copyError}
            </div>
          )}
        </div>

        <aside className="widget-settings-side">
          <article className="widget-settings-card widget-preview-card">
            <div className="widget-card-heading">
              <div className="widget-card-icon">
                <MessageCircle size={19} />
              </div>
              <div>
                <h2>Widget preview</h2>
                <p>See your customer chat experience.</p>
              </div>
            </div>

            <div className="widget-preview-visual">
              <div className="widget-preview-browser">
                <div className="widget-preview-browser-top">
                  <span />
                  <span />
                  <span />
                </div>
                <div className="widget-preview-content">
                  <div className="widget-preview-line wide" />
                  <div className="widget-preview-line" />
                  <div className="widget-preview-line short" />
                  <div className="widget-preview-chat">
                    <MessageCircle size={23} />
                  </div>
                </div>
              </div>
            </div>

            <button
              type="button"
              className="widget-preview-button"
              onClick={openWidget}
            >
              Open live preview
              <ExternalLink size={15} />
            </button>
          </article>

          <article className="widget-security-card">
            <div className="widget-security-icon">
              <ShieldCheck size={20} />
            </div>
            <h3>Public access, protected workspace</h3>
            <p>
              Visitors can use the public widget without a
              dashboard account. Your internal workspace
              remains protected by authentication and
              organization permissions.
            </p>
          </article>

          <div className="widget-organization-info">
            <span>CONNECTED ORGANIZATION</span>
            <strong>{organization.name}</strong>
            <span className="widget-key-label">
              Public key
            </span>
            <code>{publicKey}</code>
          </div>
        </aside>
      </div>
    </section>
  )
}

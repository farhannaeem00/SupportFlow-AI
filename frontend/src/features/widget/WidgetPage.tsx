
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from 'react'
import { useParams } from 'react-router-dom'
import {
  Headphones,
  LoaderCircle,
  MessageCircle,
  Send,
  X,
} from 'lucide-react'
import axios from 'axios'

import {
  widgetApiService,
  type WidgetMessage,
} from './widgetApi'

import './Widget.css'

interface VisitorForm {
  full_name: string
  email: string
  subject: string
  message: string
}

const emptyForm: VisitorForm = {
  full_name: '',
  email: '',
  subject: 'Website support request',
  message: '',
}

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail

    if (typeof detail === 'string') {
      return detail
    }

    if (Array.isArray(detail)) {
      return detail
        .map((item: { msg?: string }) => item.msg)
        .filter(Boolean)
        .join(', ')
    }

    if (!error.response) {
      return 'Unable to connect to support. Please try again.'
    }
  }

  return 'Something went wrong. Please try again.'
}

function isCustomerMessage(message: WidgetMessage) {
  return message.sender_type.toLowerCase() === 'customer'
}

export default function WidgetPage() {
  const { publicKey = '' } = useParams<{ publicKey: string }>()

  const [organizationName, setOrganizationName] = useState('Support')
  const [isOpen, setIsOpen] = useState(true)
  const [isLoading, setIsLoading] = useState(true)
  const [isSending, setIsSending] = useState(false)
  const [sessionToken, setSessionToken] = useState('')
  const [messages, setMessages] = useState<WidgetMessage[]>([])
  const [conversationStarted, setConversationStarted] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [reply, setReply] = useState('')
  const [error, setError] = useState('')

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const sessionStorageKey = `supportflow_widget_${publicKey}`

  const loadConversation = useCallback(
    async (token: string) => {
      const conversation = await widgetApiService.getConversation(
        publicKey,
        token
      )

      setMessages(conversation.messages)
      setConversationStarted(true)
    },
    [publicKey]
  )

  // Initialize public widget and restore the visitor's session.
  useEffect(() => {
    let cancelled = false

    async function initialize() {
      try {
        setIsLoading(true)
        setError('')

        const config = await widgetApiService.getConfig(publicKey)

        if (cancelled) return

        setOrganizationName(config.organization_name)

        let token = localStorage.getItem(sessionStorageKey)

        if (!token) {
          const session = await widgetApiService.createSession(publicKey)
          token = session.session_token
          localStorage.setItem(sessionStorageKey, token)
        }

        if (cancelled) return

        setSessionToken(token)

        try {
          await loadConversation(token)
        } catch (historyError) {
          // A new visitor has no conversation yet.
          if (
            axios.isAxiosError(historyError) &&
            historyError.response?.status === 404
          ) {
            setConversationStarted(false)
            setMessages([])
          } else if (
            axios.isAxiosError(historyError) &&
            historyError.response?.status === 401
          ) {
            // Recover from an expired visitor session.
            const newSession =
              await widgetApiService.createSession(publicKey)

            if (cancelled) return

            localStorage.setItem(
              sessionStorageKey,
              newSession.session_token
            )

            setSessionToken(newSession.session_token)
            setConversationStarted(false)
            setMessages([])
          } else {
            throw historyError
          }
        }
      } catch (initializationError) {
        if (!cancelled) {
          setError(getErrorMessage(initializationError))
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    if (publicKey) {
      void initialize()
    } else {
      setError('A widget public key is required.')
      setIsLoading(false)
    }

    return () => {
      cancelled = true
    }
  }, [publicKey, sessionStorageKey, loadConversation])

  // Poll for agent replies while a conversation is active.
  useEffect(() => {
    if (!conversationStarted || !sessionToken || !publicKey) {
      return
    }

    const interval = window.setInterval(async () => {
      try {
        await loadConversation(sessionToken)
      } catch (pollError) {
        console.error('Widget message refresh failed:', pollError)
      }
    }, 3000)

    return () => window.clearInterval(interval)
  }, [conversationStarted, sessionToken, publicKey, loadConversation])

  // Keep the latest message visible.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth',
    })
  }, [messages])

  async function handleStartConversation(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault()

    if (!sessionToken || !form.full_name.trim() || !form.message.trim()) {
      return
    }

    try {
      setIsSending(true)
      setError('')

      const conversation =
        await widgetApiService.createConversation(
          publicKey,
          sessionToken,
          {
            full_name: form.full_name.trim(),
            ...(form.email.trim()
              ? { email: form.email.trim() }
              : {}),
            subject: form.subject.trim() || 'Website support request',
            message: form.message.trim(),
          }
        )

      setMessages(conversation.messages)
      setConversationStarted(true)

      setForm((previous) => ({
        ...previous,
        message: '',
      }))
    } catch (sendError) {
      setError(getErrorMessage(sendError))
    } finally {
      setIsSending(false)
    }
  }

  async function handleSendMessage(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault()

    const content = reply.trim()

    if (!content || !sessionToken || isSending) return

    try {
      setIsSending(true)
      setError('')

      const sentMessage = await widgetApiService.sendMessage(
        publicKey,
        sessionToken,
        content
      )

      setMessages((previous) => {
        if (previous.some((message) => message.id === sentMessage.id)) {
          return previous
        }

        return [...previous, sentMessage]
      })

      setReply('')

      // Refresh so any newly generated AI response is also visible.
      await loadConversation(sessionToken)
    } catch (sendError) {
      setError(getErrorMessage(sendError))
    } finally {
      setIsSending(false)
    }
  }

  return (
    <div className="widget-embed-root">
      {!isOpen ? (
        <button
          className="widget-launcher"
          onClick={() => setIsOpen(true)}
          aria-label="Open support chat"
        >
          <MessageCircle size={25} />
        </button>
      ) : (
        <section className="widget-window">
          <header className="widget-header">
            <div className="widget-header-brand">
              <div className="widget-brand-icon">
                <Headphones size={21} />
              </div>

              <div>
                <h2>{organizationName}</h2>
                <span>
                  <span className="widget-online-dot" />
                  We're here to help
                </span>
              </div>
            </div>

            <button
              className="widget-close"
              onClick={() => setIsOpen(false)}
              aria-label="Minimize chat"
            >
              <X size={20} />
            </button>
          </header>

          <div className="widget-content">
            {isLoading ? (
              <div className="widget-state">
                <LoaderCircle className="widget-spinner" size={28} />
                <p>Connecting to support...</p>
              </div>
            ) : error && !sessionToken ? (
              <div className="widget-state widget-error">
                <p>{error}</p>
              </div>
            ) : !conversationStarted ? (
              <div className="widget-start">
                <div className="widget-welcome">
                  <h3>How can we help you?</h3>
                  <p>
                    Send us a message and our support team will
                    get back to you.
                  </p>
                </div>

                <form onSubmit={handleStartConversation}>
                  <label htmlFor="widget-name">Your name</label>
                  <input
                    id="widget-name"
                    value={form.full_name}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        full_name: event.target.value,
                      })
                    }
                    placeholder="John Smith"
                    maxLength={150}
                    required
                  />

                  <label htmlFor="widget-email">
                    Email address <span>(optional)</span>
                  </label>
                  <input
                    id="widget-email"
                    type="email"
                    value={form.email}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        email: event.target.value,
                      })
                    }
                    placeholder="john@example.com"
                  />

                  <label htmlFor="widget-subject">Subject</label>
                  <input
                    id="widget-subject"
                    value={form.subject}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        subject: event.target.value,
                      })
                    }
                    maxLength={200}
                    required
                  />

                  <label htmlFor="widget-message">
                    How can we help?
                  </label>
                  <textarea
                    id="widget-message"
                    value={form.message}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        message: event.target.value,
                      })
                    }
                    placeholder="Write your message..."
                    maxLength={10000}
                    rows={4}
                    required
                  />

                  {error && (
                    <p className="widget-form-error">{error}</p>
                  )}

                  <button
                    className="widget-submit"
                    type="submit"
                    disabled={
                      isSending ||
                      !form.full_name.trim() ||
                      !form.message.trim()
                    }
                  >
                    {isSending ? (
                      <LoaderCircle size={17} className="widget-spinner" />
                    ) : (
                      <>
                        Start conversation
                        <Send size={16} />
                      </>
                    )}
                  </button>
                </form>
              </div>
            ) : (
              <div className="widget-chat">
                <div className="widget-chat-intro">
                  <h3>Conversation started</h3>
                  <p>
                    Thanks for contacting {organizationName}.
                    Send a message below to continue.
                  </p>
                </div>

                <div className="widget-messages">
                  {messages.map((message) => {
                    const customer = isCustomerMessage(message)

                    return (
                      <div
                        key={message.id}
                        className={`widget-message-row ${
                          customer ? 'customer' : 'support'
                        }`}
                      >
                        <div className="widget-message-bubble">
                          <p>{message.content}</p>
                          <time>
                            {new Date(
                              message.created_at
                            ).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </time>
                        </div>
                      </div>
                    )
                  })}

                  <div ref={messagesEndRef} />
                </div>

                <form
                  className="widget-reply-form"
                  onSubmit={handleSendMessage}
                >
                  <textarea
                    value={reply}
                    onChange={(event) =>
                      setReply(event.target.value)
                    }
                    placeholder="Type your message..."
                    rows={2}
                    maxLength={10000}
                    required
                  />

                  <button
                    type="submit"
                    disabled={isSending || !reply.trim()}
                    aria-label="Send message"
                  >
                    {isSending ? (
                      <LoaderCircle
                        size={19}
                        className="widget-spinner"
                      />
                    ) : (
                      <Send size={19} />
                    )}
                  </button>
                </form>

                {error && (
                  <p className="widget-form-error">{error}</p>
                )}
              </div>
            )}
          </div>

          <footer className="widget-footer">
            Powered by <strong>SupportFlow AI</strong>
          </footer>
        </section>
      )}
    </div>
  )
}

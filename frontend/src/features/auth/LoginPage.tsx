
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, LockKeyhole, Mail, ArrowRight } from 'lucide-react'
import { toast } from 'sonner'
import AuthLayout from './AuthLayout'
import { useAuth } from './AuthContext'
import type { LoginPayload } from '../../types/auth'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [showPassword, setShowPassword] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginPayload>()

  const onSubmit = async (payload: LoginPayload) => {
    try {
      await login(payload)

      toast.success('Welcome back!')

      const from = location.state?.from
      const destination =
        from?.pathname
          ? `${from.pathname}${from.search ?? ''}${from.hash ?? ''}`
          : '/dashboard'

      navigate(destination, { replace: true })
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Unable to sign in.',
      )
    }
  }

  return (
    <AuthLayout
      title="Welcome back"
      description="Enter your account details to access your workspace."
      footer={
        <p>
          Don't have an account? <Link to="/register">Create account</Link>
        </p>
      }
    >
      <form className="auth-form" onSubmit={handleSubmit(onSubmit)}>
        <div className="auth-field">
          <label htmlFor="email">Email address</label>
          <div className={`auth-input-wrap ${errors.email ? 'has-error' : ''}`}>
            <Mail size={18} />
            <input
              id="email"
              type="email"
              placeholder="you@company.com"
              autoComplete="email"
              {...register('email', {
                required: 'Email address is required.',
                pattern: {
                  value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                  message: 'Enter a valid email address.',
                },
              })}
            />
          </div>
          {errors.email && (
            <span className="auth-field-error">{errors.email.message}</span>
          )}
        </div>

        <div className="auth-field">
          <div className="auth-label-row">
            <label htmlFor="password">Password</label>
            <Link to="/forgot-password">Forgot password?</Link>
          </div>

          <div className={`auth-input-wrap ${errors.password ? 'has-error' : ''}`}>
            <LockKeyhole size={18} />
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              placeholder="Enter your password"
              autoComplete="current-password"
              {...register('password', {
                required: 'Password is required.',
              })}
            />
            <button
              type="button"
              className="auth-password-toggle"
              onClick={() => setShowPassword((value) => !value)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          {errors.password && (
            <span className="auth-field-error">{errors.password.message}</span>
          )}
        </div>

        <button
          className="auth-submit-button"
          type="submit"
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Signing in...' : 'Sign in to workspace'}
          {!isSubmitting && <ArrowRight size={18} />}
        </button>
      </form>
    </AuthLayout>
  )
}

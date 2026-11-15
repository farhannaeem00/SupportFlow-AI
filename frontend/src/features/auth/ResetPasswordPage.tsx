
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import AuthLayout from './AuthLayout'
import api from '../../lib/api'

interface ResetPasswordForm {
  password: string
  confirmPassword: string
}

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token') || ''

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordForm>()

  const password = watch('password')

  const onSubmit = async (data: ResetPasswordForm) => {
    try {
      await api.post('/auth/password-reset/confirm', {
        token,
        new_password: data.password,
      })

      toast.success('Password reset successfully. You can now sign in.')
      navigate('/login', { replace: true })
    } catch {
      toast.error(
        'This reset link is invalid or expired. Please request a new one.',
      )
    }
  }

  return (
    <AuthLayout
      title="Create a new password"
      description="Choose a strong password to secure your SupportFlow AI account."
      footer={
        <p>
          Remember your password? <Link to="/login">Sign in</Link>
        </p>
      }
    >
      {!token ? (
        <div className="auth-form">
          <div className="auth-success-message">
            <h3>Reset link unavailable</h3>
            <p>
              This password reset link is missing its token. Request a new
              reset link to continue.
            </p>
          </div>

          <Link to="/forgot-password" className="auth-submit-button">
            Request a new link
          </Link>
        </div>
      ) : (
        <form className="auth-form" onSubmit={handleSubmit(onSubmit)}>
          <div className="auth-field">
            <label htmlFor="password">New password</label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              placeholder="Enter your new password"
              className={`auth-input ${errors.password ? 'has-error' : ''}`}
              {...register('password', {
                required: 'Password is required.',
                minLength: {
                  value: 8,
                  message: 'Password must contain at least 8 characters.',
                },
                maxLength: {
                  value: 128,
                  message: 'Password cannot exceed 128 characters.',
                },
              })}
            />
            {errors.password && (
              <span className="auth-field-error">
                {errors.password.message}
              </span>
            )}
          </div>

          <div className="auth-field">
            <label htmlFor="confirmPassword">Confirm new password</label>
            <input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              placeholder="Confirm your new password"
              className={`auth-input ${
                errors.confirmPassword ? 'has-error' : ''
              }`}
              {...register('confirmPassword', {
                required: 'Please confirm your password.',
                validate: (value) =>
                  value === password || 'Passwords do not match.',
              })}
            />
            {errors.confirmPassword && (
              <span className="auth-field-error">
                {errors.confirmPassword.message}
              </span>
            )}
          </div>

          <button
            type="submit"
            className="auth-submit-button"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Resetting password...' : 'Reset password'}
          </button>
        </form>
      )}
    </AuthLayout>
  )
}

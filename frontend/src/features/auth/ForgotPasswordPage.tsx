
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import AuthLayout from './AuthLayout'
import api from '../../lib/api'

interface ForgotPasswordForm {
  email: string
}

export default function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordForm>()

  const onSubmit = async (data: ForgotPasswordForm) => {
    try {
      await api.post('/auth/password-reset/request', {
        email: data.email,
      })

      setSubmitted(true)
      toast.success('Password reset instructions requested.')
    } catch {
      toast.error('Unable to process your request. Please try again.')
    }
  }

  return (
    <AuthLayout
      title="Forgot your password?"
      description="Enter your account email and we'll send you instructions to reset your password."
      footer={
        <p>
          Remember your password? <Link to="/login">Sign in</Link>
        </p>
      }
    >
      {submitted ? (
        <div className="auth-form">
          <div className="auth-success-message">
            <h3>Check your email</h3>
            <p>
              If an account exists with that email address, you will receive
              a password reset link shortly.
            </p>
          </div>

          <Link to="/login" className="auth-submit-button">
            Back to sign in
          </Link>
        </div>
      ) : (
        <form className="auth-form" onSubmit={handleSubmit(onSubmit)}>
          <div className="auth-field">
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              placeholder="you@company.com"
              autoComplete="email"
              className={`auth-input ${errors.email ? 'has-error' : ''}`}
              {...register('email', {
                required: 'Email address is required.',
                pattern: {
                  value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                  message: 'Enter a valid email address.',
                },
              })}
            />
            {errors.email && (
              <span className="auth-field-error">
                {errors.email.message}
              </span>
            )}
          </div>

          <button
            type="submit"
            className="auth-submit-button"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Sending instructions...' : 'Send reset link'}
          </button>
        </form>
      )}
    </AuthLayout>
  )
}

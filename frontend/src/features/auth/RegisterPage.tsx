
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  Building2,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  UserRound,
} from 'lucide-react'
import { toast } from 'sonner'
import AuthLayout from './AuthLayout'
import { useAuth } from './AuthContext'
import type { RegisterPayload } from '../../types/auth'

interface RegistrationForm extends RegisterPayload {
  confirmPassword: string
}

export default function RegisterPage() {
  const { register: createAccount } = useAuth()
  const navigate = useNavigate()
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegistrationForm>()

  const password = watch('password')

  const onSubmit = async ({
    confirmPassword: _confirmPassword,
    ...payload
  }: RegistrationForm) => {
    try {
      await createAccount(payload)
      toast.success('Your workspace has been created.')
      navigate('/dashboard', { replace: true })
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Unable to create your account.',
      )
    }
  }

  return (
    <AuthLayout
      title="Create your workspace"
      description="Get started with a smarter way to manage customer support."
      footer={
        <p>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      }
    >
      <form className="auth-form auth-register-form" onSubmit={handleSubmit(onSubmit)}>
        <div className="auth-field">
          <label htmlFor="full_name">Full name</label>
          <div className={`auth-input-wrap ${errors.full_name ? 'has-error' : ''}`}>
            <UserRound size={18} />
            <input
              id="full_name"
              type="text"
              placeholder="Your full name"
              autoComplete="name"
              {...register('full_name', {
                required: 'Full name is required.',
                minLength: {
                  value: 2,
                  message: 'Name must contain at least 2 characters.',
                },
                maxLength: {
                  value: 150,
                  message: 'Name cannot exceed 150 characters.',
                },
              })}
            />
          </div>
          {errors.full_name && (
            <span className="auth-field-error">{errors.full_name.message}</span>
          )}
        </div>

        <div className="auth-field">
          <label htmlFor="organization_name">Organization name</label>
          <div className={`auth-input-wrap ${errors.organization_name ? 'has-error' : ''}`}>
            <Building2 size={18} />
            <input
              id="organization_name"
              type="text"
              placeholder="Your company or team"
              autoComplete="organization"
              {...register('organization_name', {
                required: 'Organization name is required.',
                minLength: {
                  value: 2,
                  message: 'Organization name must contain at least 2 characters.',
                },
                maxLength: {
                  value: 150,
                  message: 'Organization name cannot exceed 150 characters.',
                },
              })}
            />
          </div>
          {errors.organization_name && (
            <span className="auth-field-error">
              {errors.organization_name.message}
            </span>
          )}
        </div>

        <div className="auth-field">
          <label htmlFor="register_email">Email address</label>
          <div className={`auth-input-wrap ${errors.email ? 'has-error' : ''}`}>
            <Mail size={18} />
            <input
              id="register_email"
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
          <label htmlFor="register_password">Password</label>
          <div className={`auth-input-wrap ${errors.password ? 'has-error' : ''}`}>
            <LockKeyhole size={18} />
            <input
              id="register_password"
              type={showPassword ? 'text' : 'password'}
              placeholder="At least 8 characters"
              autoComplete="new-password"
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

        <div className="auth-field">
          <label htmlFor="confirm_password">Confirm password</label>
          <div className={`auth-input-wrap ${errors.confirmPassword ? 'has-error' : ''}`}>
            <LockKeyhole size={18} />
            <input
              id="confirm_password"
              type={showConfirmPassword ? 'text' : 'password'}
              placeholder="Re-enter your password"
              autoComplete="new-password"
              {...register('confirmPassword', {
                required: 'Please confirm your password.',
                validate: (value) =>
                  value === password || 'Passwords do not match.',
              })}
            />
            <button
              type="button"
              className="auth-password-toggle"
              onClick={() => setShowConfirmPassword((value) => !value)}
              aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
            >
              {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          {errors.confirmPassword && (
            <span className="auth-field-error">
              {errors.confirmPassword.message}
            </span>
          )}
        </div>

        <button
          className="auth-submit-button"
          type="submit"
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Creating workspace...' : 'Create account'}
          {!isSubmitting && <ArrowRight size={18} />}
        </button>

        <p className="auth-terms-note">
          By creating an account, you agree to use SupportFlow AI responsibly.
        </p>
      </form>
    </AuthLayout>
  )
}

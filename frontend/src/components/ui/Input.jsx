import { clsx } from 'clsx'
import { forwardRef } from 'react'

const Input = forwardRef(({
  label,
  error,
  type = 'text',
  className,
  ...props
}, ref) => {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </label>
      )}
      <input
        ref={ref}
        type={type}
        className={clsx(
          'w-full px-3 py-2 rounded-lg border text-sm transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500',
          'placeholder:text-gray-400',
          error
            ? 'border-red-300 bg-red-50 text-red-900'
            : 'border-gray-300 bg-white text-gray-900',
          className
        )}
        {...props}
      />
      {error && (
        <p className="mt-1 text-xs text-red-600">{error}</p>
      )}
    </div>
  )
})

Input.displayName = 'Input'
export default Input

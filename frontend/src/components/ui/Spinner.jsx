import { Loader2 } from 'lucide-react'
import { clsx } from 'clsx'

export default function Spinner({ size = 'md', fullScreen = false, className }) {
  const sizes = { sm: 16, md: 24, lg: 40 }

  const spinner = (
    <Loader2
      size={sizes[size]}
      className={clsx('animate-spin text-brand-600', className)}
    />
  )

  if (fullScreen) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-white/80 z-50">
        {spinner}
      </div>
    )
  }

  return spinner
}

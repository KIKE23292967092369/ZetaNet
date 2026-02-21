import { clsx } from 'clsx'

const borderColors = {
  blue: 'border-l-blue-500',
  orange: 'border-l-orange-500',
  red: 'border-l-red-500',
  green: 'border-l-green-600',
  purple: 'border-l-purple-600',
  cyan: 'border-l-cyan-500',
}

const iconBgColors = {
  blue: 'text-blue-500',
  orange: 'text-orange-500',
  red: 'text-red-500',
  green: 'text-green-600',
  purple: 'text-purple-600',
  cyan: 'text-cyan-500',
}

const valueColors = {
  blue: 'text-blue-600',
  orange: 'text-orange-600',
  red: 'text-red-600',
  green: 'text-green-600',
  purple: 'text-purple-600',
  cyan: 'text-cyan-600',
}

export default function StatCard({
  title,
  subtitle,
  value,
  icon: Icon,
  color = 'blue',
  onClick,
}) {
  const Component = onClick ? 'button' : 'div'

  return (
    <Component
      onClick={onClick}
      className={clsx(
        'bg-white rounded-lg border border-gray-200 border-l-4 p-5',
        'flex items-center gap-4 transition-all hover:shadow-md',
        borderColors[color],
        onClick && 'cursor-pointer w-full text-left'
      )}
    >
      {/* Icono grande */}
      {Icon && (
        <div className={clsx('shrink-0', iconBgColors[color])}>
          <Icon size={48} strokeWidth={1.5} />
        </div>
      )}

      {/* Info */}
      <div className="flex-1 min-w-0">
        <h4 className={clsx('text-sm font-bold', valueColors[color])}>
          {title}
        </h4>
        {subtitle && (
          <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>
        )}
        <p className={clsx('text-3xl font-bold mt-1', valueColors[color])}>
          {value}
        </p>
      </div>
    </Component>
  )
}

import { Inbox } from 'lucide-react'
import Button from './Button'

export default function EmptyState({
  icon: Icon = Inbox,
  message = 'No hay datos',
  description,
  actionLabel,
  onAction,
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <Icon size={48} className="text-gray-300 mb-3" />
      <h3 className="text-base font-medium text-gray-500 mb-1">{message}</h3>
      {description && (
        <p className="text-sm text-gray-400 mb-4 text-center max-w-sm">{description}</p>
      )}
      {actionLabel && onAction && (
        <Button onClick={onAction}>{actionLabel}</Button>
      )}
    </div>
  )
}

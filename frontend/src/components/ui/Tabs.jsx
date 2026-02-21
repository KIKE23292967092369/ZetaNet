import { clsx } from 'clsx'

export default function Tabs({ tabs, activeTab, onChange }) {
  return (
    <div className="border-b border-gray-200">
      <nav className="flex gap-0 -mb-px overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={clsx(
              'px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors',
              activeTab === tab.id
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            )}
          >
            {tab.icon && <tab.icon size={16} className="inline-block mr-1.5 -mt-0.5" />}
            {tab.label}
            {tab.count != null && (
              <span className={clsx(
                'ml-2 px-1.5 py-0.5 rounded-full text-xs',
                activeTab === tab.id
                  ? 'bg-brand-100 text-brand-700'
                  : 'bg-gray-100 text-gray-500'
              )}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </nav>
    </div>
  )
}

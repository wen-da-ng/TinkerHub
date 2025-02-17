// frontend\src\components\SearchSettings.tsx
import { SEARCH_TYPES, DEFAULT_SEARCH_SETTINGS, ICONS } from './config'
import type { SearchSettings } from './types'

export const SearchSettings = ({
  settings,
  onChange
}: {
  settings: SearchSettings
  onChange: (newSettings: SearchSettings) => void
}) => (
  <div className="flex items-center gap-2 mb-2">
    <ToggleButton
      label="Web Search"
      icon={<ICONS.search className="w-4 h-4" />}
      enabled={settings.webSearchEnabled}
      onToggle={() => onChange({ ...settings, webSearchEnabled: !settings.webSearchEnabled })}
    />
    
    {settings.webSearchEnabled && (
      <>
        <select
          value={settings.searchType}
          onChange={(e) => onChange({ ...settings, searchType: e.target.value as any })}
          className="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200"
        >
          {SEARCH_TYPES.map((type) => (
            <option key={type} value={type}>
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </option>
          ))}
        </select>

        <input
          type="number"
          min="1"
          max="10"
          value={settings.resultsCount}
          onChange={(e) => onChange({ ...settings, resultsCount: Math.min(10, Math.max(1, parseInt(e.target.value) || 1)) })}
          className="w-16 px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200"
        />
        
        <ToggleButton
          label="Auto-Summarize"
          enabled={settings.showSummary}
          onToggle={() => onChange({ ...settings, showSummary: !settings.showSummary })}
        />
      </>
    )}
  </div>
)

const ToggleButton = ({
  label,
  icon,
  enabled,
  onToggle
}: {
  label: string
  icon?: React.ReactNode
  enabled: boolean
  onToggle: () => void
}) => (
  <button
    onClick={onToggle}
    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
      enabled
        ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800' 
        : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
    }`}
  >
    {icon}
    {label} {enabled ? 'On' : 'Off'}
  </button>
)
interface IndustryFilterProps {
  industries: string[]
  selected: string
  onChange: (industry: string) => void
}

export default function IndustryFilter({ industries, selected, onChange }: IndustryFilterProps) {
  return (
    <div role="group" aria-label="Industry filter" className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
      <button
        onClick={() => onChange('')}
        className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
          selected === ''
            ? 'bg-emerald-600 text-white'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'
        }`}
      >
        All
      </button>
      {industries.map((ind) => (
        <button
          key={ind}
          onClick={() => onChange(ind === selected ? '' : ind)}
          className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
            ind === selected
              ? 'bg-emerald-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'
          }`}
        >
          {ind}
        </button>
      ))}
    </div>
  )
}

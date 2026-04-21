const LEVEL_CLASSES = {
  critique: 'bg-red-50 text-red-600 border border-red-200',
  élevé:    'bg-orange-50 text-orange-600 border border-orange-200',
  moyen:    'bg-yellow-50 text-yellow-700 border border-yellow-200',
  faible:   'bg-green-50 text-green-700 border border-green-200',
};

const DOT_CLASSES = {
  critique: 'bg-red-500',
  élevé:    'bg-orange-500',
  moyen:    'bg-yellow-500',
  faible:   'bg-green-500',
};

const SIZE_CLASSES = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
};

export default function Badge({ level, size = 'sm' }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${LEVEL_CLASSES[level] ?? ''} ${SIZE_CLASSES[size]}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${DOT_CLASSES[level] ?? ''}`} />
      {level}
    </span>
  );
}

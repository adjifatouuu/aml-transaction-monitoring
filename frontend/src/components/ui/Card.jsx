export default function Card({ children, className = '', onClick }) {
  const interactive = onClick
    ? 'cursor-pointer hover:shadow-card-hover transition-shadow duration-150'
    : '';

  return (
    <div
      className={`bg-white rounded-card shadow-card ${interactive} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

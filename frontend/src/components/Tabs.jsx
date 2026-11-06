export default function Tabs({ value, onChange, items }) {
  return (
    <nav className="tabs" role="tablist" aria-label="Vistas de resultados">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={value === item.id}
          className={`tab ${value === item.id ? "is-active" : ""}`}
          onClick={() => onChange(item.id)}
        >
          {item.label}
          {item.badge ? <span className="tab-badge">{item.badge}</span> : null}
        </button>
      ))}
    </nav>
  );
}

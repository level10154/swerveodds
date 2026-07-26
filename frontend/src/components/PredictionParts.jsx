export function FormPills({ form = [] }) {
  if (!form?.length) return <span className="text-xs text-slate-500">No recent matches</span>;
  return (
    <div className="flex items-center gap-1">
      {form.slice(0, 5).reverse().map((f, i) => (
        <span key={i} className={`form-dot form-${f}`}>{f}</span>
      ))}
    </div>
  );
}

export function ProbBarLine({ label, value, color = "bg-purple-500" }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-300">{label}</span>
        <span className="text-white font-semibold">{value}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${Math.min(100, value)}%` }} />
      </div>
    </div>
  );
}

// Shared rolling-day helpers used by AllMatches and Predictions pages.
// Produces: Today, Tomorrow, then each following calendar day by name + date.

export function buildRollingDays(count = 7) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Array.from({ length: count }, (_, i) => {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    return d;
  });
}

export function dayLabel(i) {
  if (i === 0) return "Today";
  if (i === 1) return "Tomorrow";
  return null; // caller falls back to weekday name
}

export function toISODate(d) {
  return d.toISOString().slice(0, 10);
}

import { useEffect, useMemo, useState } from "react";

type UseNowOptions = {
  /** Update interval in ms (default: 1000). */
  intervalMs?: number;
  /** Optional IANA timezone name, e.g. "America/Sao_Paulo". */
  timeZone?: string;
};

function getZonedDate(timeZone?: string) {
  if (!timeZone) return new Date();
  // Create a Date-like representation in a target time zone.
  // We keep it simple by formatting and parsing back.
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(new Date());

  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "00";
  const y = Number(get("year"));
  const m = Number(get("month"));
  const d = Number(get("day"));
  const hh = Number(get("hour"));
  const mm = Number(get("minute"));
  const ss = Number(get("second"));
  return new Date(y, m - 1, d, hh, mm, ss);
}

export function useNow(options: UseNowOptions = {}) {
  const { intervalMs = 1000, timeZone } = options;

  const [now, setNow] = useState<Date>(() => getZonedDate(timeZone));

  const tzKey = useMemo(() => timeZone ?? "local", [timeZone]);

  useEffect(() => {
    setNow(getZonedDate(timeZone));

    const id = window.setInterval(() => {
      setNow(getZonedDate(timeZone));
    }, intervalMs);

    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, tzKey]);

  return now;
}

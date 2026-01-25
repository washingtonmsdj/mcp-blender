import { useMemo } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type TimezonePickerProps = {
  value: string;
  onChange: (tz: string) => void;
};

const COMMON_TIMEZONES = [
  { value: "local", label: "Local (dispositivo)" },
  { value: "America/Sao_Paulo", label: "América/São Paulo" },
  { value: "America/Manaus", label: "América/Manaus" },
  { value: "America/Fortaleza", label: "América/Fortaleza" },
  { value: "UTC", label: "UTC" },
  { value: "Europe/Lisbon", label: "Europa/Lisboa" },
  { value: "Europe/London", label: "Europa/Londres" },
  { value: "Europe/Paris", label: "Europa/Paris" },
  { value: "America/New_York", label: "América/Nova York" },
  { value: "Asia/Tokyo", label: "Ásia/Tóquio" },
];

export default function TimezonePicker({ value, onChange }: TimezonePickerProps) {
  const normalized = useMemo(() => (value === "local" ? "local" : value), [value]);

  return (
    <div className="w-full max-w-md">
      <label className="mb-2 block text-sm font-medium text-muted-foreground">
        Fuso horário
      </label>
      <Select
        value={normalized}
        onValueChange={(v) => {
          onChange(v);
        }}
      >
        <SelectTrigger className="h-11 rounded-2xl bg-card/60 shadow-soft backdrop-blur">
          <SelectValue placeholder="Escolha um fuso" />
        </SelectTrigger>
        <SelectContent className="rounded-2xl">
          {COMMON_TIMEZONES.map((tz) => (
            <SelectItem key={tz.value} value={tz.value}>
              {tz.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

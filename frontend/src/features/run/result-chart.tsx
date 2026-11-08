import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
  type ChartOptions,
} from "chart.js";
import { Bar, Line, Pie, Scatter } from "react-chartjs-2";

import type { Chart } from "@/lib/api";
import { formatCompact } from "@/lib/format";
import { useUI } from "@/lib/store";

ChartJS.register(ArcElement, BarElement, CategoryScale, Legend, LinearScale, LineElement, PointElement, Tooltip);

/** Read a token at render time so charts follow the active theme. */
const tokenColor = (name: string, alpha = 1) => {
  const rgb = getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim();
  return `rgb(${rgb} / ${alpha})`;
};

const humanize = (col: string) => col.replace(/_/g, " ");

export function ResultChart({ chart }: { chart: Chart }) {
  const theme = useUI((s) => s.theme);
  const fg = tokenColor("fg-muted");
  const grid = tokenColor("border");
  const accent = tokenColor("accent");
  const font = { family: "IBM Plex Sans", size: 12 };

  // Pie only works for a few parts of a whole; otherwise fall back to bars.
  const type = chart.type === "pie" && chart.labels.length > 4 ? "bar" : chart.type;

  const axes: ChartOptions<"bar" | "line">["scales"] = {
    x: {
      title: { display: true, text: humanize(chart.x), color: fg, font },
      ticks: { color: fg, font, maxRotation: 0, autoSkip: true },
      grid: { display: false },
      border: { color: grid },
    },
    y: {
      title: { display: true, text: humanize(chart.y), color: fg, font },
      ticks: { color: fg, font, callback: (v) => formatCompact(Number(v)) },
      grid: { color: grid },
      border: { display: false },
      beginAtZero: type === "bar",
    },
  };

  const common = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 160 },
    plugins: {
      legend: { display: type === "pie", position: "right" as const, labels: { color: fg, font } },
      tooltip: { titleFont: font, bodyFont: font },
    },
  };

  const labels = chart.labels.map(String);
  const series = { label: humanize(chart.y), data: chart.values };

  return (
    <figure className="flex flex-col gap-2">
      <figcaption className="text-sm text-fg-muted">{chart.title}</figcaption>
      <div className="h-chart" role="img" aria-label={`${type} chart of ${humanize(chart.y)} by ${humanize(chart.x)}`}>
        {type === "bar" && (
          <Bar
            key={theme}
            data={{ labels, datasets: [{ ...series, backgroundColor: accent, borderRadius: 2, maxBarThickness: 40 }] }}
            options={{ ...common, scales: axes }}
          />
        )}
        {type === "line" && (
          <Line
            key={theme}
            data={{ labels, datasets: [{ ...series, borderColor: accent, backgroundColor: accent, pointRadius: 2, borderWidth: 2 }] }}
            options={{ ...common, scales: axes }}
          />
        )}
        {type === "scatter" && (
          <Scatter
            key={theme}
            data={{
              datasets: [
                {
                  ...series,
                  data: chart.values.map((y, i) => ({ x: Number(chart.labels[i]), y })),
                  backgroundColor: accent,
                },
              ],
            }}
            options={{ ...common, scales: axes as ChartOptions<"scatter">["scales"] }}
          />
        )}
        {type === "pie" && (
          <Pie
            key={theme}
            data={{
              labels,
              datasets: [
                {
                  ...series,
                  backgroundColor: ["chart-1", "chart-2", "chart-3", "chart-4"].map((t) => tokenColor(t)),
                  borderColor: tokenColor("bg"),
                },
              ],
            }}
            options={common}
          />
        )}
      </div>
    </figure>
  );
}

import { useMemo, type CSSProperties } from "react";
import ReactECharts from "echarts-for-react";
import type { SpeedCurveChartData } from "@/components/speed-curve-chart";
import { isNil } from "@/utils";

type SpeedMultiCurveChartProps = {
  curveData1?: SpeedCurveChartData;
  curveData2?: SpeedCurveChartData;
  name1?: string;
  name2?: string;
  yAxisMin?: number;
  yAxisMax?: number;
  style?: CSSProperties;
};

type NumericPoint = { t: number; v: number };

function toNumericPoints(curveData?: SpeedCurveChartData): NumericPoint[] {
  const raw = Array.isArray(curveData) ? curveData : [];

  return raw
    .map((p) => {
      const t = typeof p.t === "number" ? p.t : Number(p.t);
      const v = typeof p.v === "number" ? p.v : Number(p.v);
      return { t, v };
    })
    .filter((p) => Number.isFinite(p.t) && Number.isFinite(p.v))
    .sort((a, b) => a.t - b.t);
}

function round2(n: number) {
  return Math.round(n * 100) / 100;
}

function normalizeToIntervals(points: NumericPoint[], intervalCount = 100): Array<number | null> {
  if (!Array.isArray(points) || points.length === 0) {
    return Array.from({ length: intervalCount }, () => null);
  }

  if (points.length === 1) {
    return Array.from({ length: intervalCount }, () => round2(points[0].v));
  }

  const minT = points[0].t;
  const maxT = points[points.length - 1].t;

  if (minT === maxT) {
    return Array.from({ length: intervalCount }, () => round2(points[0].v));
  }

  const result: Array<number | null> = [];
  let j = 0;

  for (let i = 0; i < intervalCount; i += 1) {
    const ratio = intervalCount === 1 ? 0 : i / (intervalCount - 1);
    const targetT = minT + ratio * (maxT - minT);

    while (j < points.length - 2 && points[j + 1].t < targetT) {
      j += 1;
    }

    const p0 = points[j];
    const p1 = points[j + 1] ?? p0;

    if (!p1 || p0.t === p1.t) {
      result.push(round2(p0.v));
      continue;
    }

    if (targetT <= p0.t) {
      result.push(round2(p0.v));
      continue;
    }

    if (targetT >= p1.t) {
      result.push(round2(p1.v));
      continue;
    }

    const tRatio = (targetT - p0.t) / (p1.t - p0.t);
    const y = p0.v + tRatio * (p1.v - p0.v);
    result.push(Number.isFinite(y) ? round2(y) : null);
  }

  return result;
}

export default function SpeedMultiCurveChart({
  curveData1,
  curveData2,
  name1 = "视频 A",
  name2 = "视频 B",
  yAxisMin = 0,
  yAxisMax = 12,
  style,
}: SpeedMultiCurveChartProps) {
  const option = useMemo(() => {
    const xAxisData = Array.from({ length: 100 }, (_, idx) => String(idx + 1));

    const points1 = toNumericPoints(curveData1);
    const points2 = toNumericPoints(curveData2);

    const series1 = normalizeToIntervals(points1, 100);
    const series2 = normalizeToIntervals(points2, 100);

    const hasAnyData =
      series1.some((v) => !isNil(v)) || series2.some((v) => !isNil(v));

    return {
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: "cross",
          label: {
            backgroundColor: "#6a7985",
          },
        },
      },
      legend: {
        show: hasAnyData,
        data: [name1, name2],
      },
      xAxis: {
        type: "category",
        name: "区间",
        boundaryGap: false,
        data: xAxisData,
      },
      yAxis: {
        type: "value",
        name: "速度 (mm/s)",
        min: yAxisMin,
        max: yAxisMax,
      },
      series: [
        {
          name: name1,
          type: "line",
          smooth: true,
          emphasis: { focus: "series" },
          data: series1,
        },
        {
          name: name2,
          type: "line",
          smooth: true,
          emphasis: { focus: "series" },
          data: series2,
        },
      ],
    };
  }, [curveData1, curveData2, name1, name2, yAxisMin, yAxisMax]);

  return <ReactECharts option={option} style={{ width: "100%", height: "100%", ...style }} />;
}


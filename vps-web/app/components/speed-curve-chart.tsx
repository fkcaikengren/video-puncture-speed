import { useMemo, type CSSProperties } from "react";
import ReactECharts from "echarts-for-react";
import { isNil } from "@/utils";

export interface SpeedCurveChartPoint {
  t: number | string;
  v: number | string;
}

export type SpeedCurveChartData = SpeedCurveChartPoint[];

type SpeedCurveChartProps = {
  curveData?: SpeedCurveChartData;
  yAxisMin?: number;
  yAxisMax?: number;
  style?: CSSProperties;
};

export default function SpeedCurveChart({
  curveData,
  yAxisMin = 0,
  yAxisMax = 12,
  style,
}: SpeedCurveChartProps) {
  const option = useMemo(() => {
    const fallbackXAxisData = ["0.00", "1.00", "2.00", "3.00", "4.00", "5.00", "6.00"];
    const fallbackYSeriesData = [0, 1, 2, 3, 4, 5, 6];

    const safeCurveData = Array.isArray(curveData) ? curveData : [];

    const xAxisData =
      safeCurveData.length > 0
        ? safeCurveData.map((p, idx) => {
            if (!isNil(p.t)) {
              if (typeof p.t === "number") return p.t.toFixed(2);
              if (typeof p.t === "string") return p.t;
            }
            return `${idx}s`;
          })
        : fallbackXAxisData;

    const ySeriesData =
      safeCurveData.length > 0
        ? safeCurveData.map((p, idx) => {
            if (!isNil(p.v)) {
              const num = typeof p.v === "number" ? p.v : Number(p.v);
              if (Number.isFinite(num)) {
                return Math.round(num * 100) / 100;
              }
            }
            return idx === 0 ? 0 : idx * 3;
          })
        : fallbackYSeriesData;

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
      xAxis: {
        type: "category",
        name: "时间 (s)",
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
          name: "速度曲线",
          type: "line",
          smooth: true,
          emphasis: {
            focus: "series",
          },
          data: ySeriesData,
        },
      ],
    };
  }, [curveData, yAxisMin, yAxisMax]);

  return (
    <ReactECharts
      option={option}
      style={{ width: "100%", height: "100%", ...style }}
    />
  );
}

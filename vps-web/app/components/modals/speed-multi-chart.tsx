import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { BaseModalProps } from "@/lib/react-modal-store";
import SpeedMultiCurveChart from "@/components/speed-multi-curve-chart";
import type { SpeedCurveChartData } from "@/components/speed-curve-chart";

type SpeedMultiChartModalProps = BaseModalProps & {
  title?: string;
  curveData1?: SpeedCurveChartData;
  curveData2?: SpeedCurveChartData;
  name1?: string;
  name2?: string;
  yAxisMin?: number;
  yAxisMax?: number;
};

export function SpeedMultiChartModal({
  visible,
  onCancel,
  title,
  curveData1,
  curveData2,
  name1,
  name2,
  yAxisMin,
  yAxisMax,
}: SpeedMultiChartModalProps) {
  return (
    <Dialog
      open={visible}
      onOpenChange={(v) => {
        if (!v) onCancel();
      }}
    >
      <DialogContent className="!w-4/5 !max-w-none flex h-[80vh] flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="p-4 border-b bg-muted/50">
          <DialogTitle className="truncate">{title || "A/B速度曲线"}</DialogTitle>
        </DialogHeader>
        <div className="min-h-0 flex-1 p-4">
          <div className="h-full w-full">
            <SpeedMultiCurveChart
              curveData1={curveData1}
              curveData2={curveData2}
              name1={name1}
              name2={name2}
              yAxisMin={yAxisMin}
              yAxisMax={yAxisMax}
            />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}


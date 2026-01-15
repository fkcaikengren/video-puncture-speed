import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { BaseModalProps } from "@/lib/react-modal-store";
import SpeedCurveChart, { type SpeedCurveChartData } from "@/components/speed-curve-chart";

type SpeedChartModalProps = BaseModalProps & {
  title?: string;
  curveData?: SpeedCurveChartData;
};

export function SpeedChartModal({ visible, onCancel, title, curveData }: SpeedChartModalProps) {
  return (
    <Dialog
      open={visible}
      onOpenChange={(v) => {
        if (!v) onCancel();
      }}
    >
      <DialogContent className="!w-4/5 !max-w-none flex h-[80vh] flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="p-4 border-b bg-muted/50">
          <DialogTitle className="truncate">{title || "速度曲线"}</DialogTitle>
        </DialogHeader>
        <div className="min-h-0 flex-1 p-4">
          <div className="h-full w-full">
            <SpeedCurveChart curveData={curveData} />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

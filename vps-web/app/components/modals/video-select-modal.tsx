import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { BaseModalProps } from "@/lib/react-modal-store";
import VideoSearchList from "@/components/biz/video-search-list";

type VideoSelectModalProps = BaseModalProps & {
  title?: string;
  disabledVideoIds?: string[];
  onSelectVideoId?: (videoId: string) => void;
};

export function VideoSelectModal({
  visible,
  onCancel,
  title,
  disabledVideoIds,
  onSelectVideoId,
}: VideoSelectModalProps) {
  return (
    <Dialog
      open={visible}
      onOpenChange={(v) => {
        if (!v) onCancel();
      }}
    >
      <DialogContent className="!w-4/5 !max-w-none flex h-[80vh] flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="p-4 border-b bg-muted/50">
          <DialogTitle className="truncate">{title || "选择视频"}</DialogTitle>
        </DialogHeader>

        <div className="min-h-0 flex-1 overflow-auto p-4">
          <VideoSearchList
            selectable
            disabledVideoIds={disabledVideoIds}
            onSelectVideoId={(videoId) => {
              onSelectVideoId?.(videoId);
              onCancel();
            }}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}


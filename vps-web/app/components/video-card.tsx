import { FileVideo, CheckCircle2, Clock, AlertCircle, PlayCircle } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { Video } from "@/types/video";

export const videoStatusVariants = cva("h-4 w-4", {
  variants: {
    status: {
      completed: "text-green-500",
      processing: "text-blue-500",
      failed: "text-red-500",
      pending: "text-yellow-500",
      default: "text-muted-foreground",
    },
  },
  defaultVariants: {
    status: "default",
  },
});

interface VideoCardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "onPlay"> {
  video: Video;
  statusVariant?: VariantProps<typeof videoStatusVariants>["status"];
  onPlay?: (video: Video) => void;
  onAnalysis?: (video: Video) => void;
}

const StatusIcon = ({ status, className }: { status?: string; className?: string }) => {
  const variant = (status || "default") as VariantProps<typeof videoStatusVariants>["status"];
    
  const variantClassName = videoStatusVariants({ status: variant });

  const Icon = {
    completed: CheckCircle2,
    processing: Clock,
    failed: AlertCircle,
    pending: Clock,
    default: Clock,
  }[variant as string] || Clock;

  return <Icon className={cn(variantClassName, className)} />;
};

export function VideoCard({ video, className, onPlay, onAnalysis, ...props }: VideoCardProps) {
  const handlePlay = (e: React.MouseEvent) => {
    e.preventDefault();
    onPlay?.(video);
  };

  const handleAnalysis = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onAnalysis?.(video);
  };

  return (
    <div className={cn("group relative", className)} {...props}>
        <Card className="overflow-hidden border-none shadow-none bg-transparent">
          <div className="aspect-video w-full bg-muted flex items-center justify-center relative rounded-lg overflow-hidden group/thumb">
            {video.thumbnail_url ? (
              <img 
                src={video.thumbnail_url} 
                alt={video.title} 
                className="w-full h-full object-cover transition-transform duration-300 group-hover/thumb:scale-105" 
              />
            ) : (
              <FileVideo className="h-10 w-10 text-muted-foreground/50 group-hover/thumb:hidden" />
            )}
            
            {/* Gradient Overlay */}
            <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/60 to-transparent" />

            {/* Hover Actions */}
            <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/20"
              onClick={handlePlay}
            >
                <PlayCircle size={48} color="white" />
            </div>

            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
               <Button 
                size="sm" 
                className="cursor-pointer bg-black/60 hover:bg-black/80 text-white text-xs h-7 px-3 rounded-md border border-white/10 backdrop-blur-sm"
                onClick={handleAnalysis}
               >
                 去分析
               </Button>
            </div>

            {/* Duration */}
            {video.durationStr && (
              <span className="absolute bottom-2 right-2 text-white text-xs font-medium">
                {video.durationStr}
              </span>
            )}
          </div>
          
          <div className="mt-1 space-y-1">
            <h3 className="text-[15px] font-medium leading-snug line-clamp-2 group-hover:text-primary transition-colors" title={video.title}>
              {video.title}
            </h3>
            <div className="flex items-center text-xs text-muted-foreground gap-2">
              {video.statusStr && (
                <StatusIcon status={video.statusStr} className="h-3.5 w-3.5" />
              )}
              {video.uploader && (
                <>
                  <span>{video.uploader}</span>
                  <span>·</span>
                </>
              )}
              {video.dateStr && <span>{video.dateStr}</span>}
            </div>
          </div>
        </Card>
    </div>
  );
}

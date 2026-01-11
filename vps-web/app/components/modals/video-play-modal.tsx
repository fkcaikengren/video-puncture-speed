import { useState, useImperativeHandle } from "react"
import ReactPlayer from "react-player"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import type { Video } from "@/types/video"
import { Calendar, User, Eye } from "lucide-react"
import type { BaseModalProps } from "@/lib/react-modal-store"

type VideoPlayModalProps = BaseModalProps & {
  video?: Video;
}

export function VideoPlayModal({visible, onCancel, video}: VideoPlayModalProps) {

  return (
    <Dialog open={visible} onOpenChange={(v)=>{
      if(!v){
        onCancel()
      }
    }} >
      <DialogContent className="sm:max-w-4xl p-0 gap-0 overflow-hidden bg-background border-border">
        <DialogHeader className="p-4 flex flex-row items-center justify-between border-b border-border bg-muted/50">
          <DialogTitle className="text-foreground font-medium text-lg truncate flex-1 pr-4">
            {video?.title || "Video Player"}
          </DialogTitle>
        </DialogHeader>
        
        <div className="aspect-video w-full bg-black flex items-center justify-center relative">
             {video && visible && (
                <ReactPlayer
                  slot="media"
                  src={video.url || ''}
                  controls={true}
                  style={{
                    width: "100%",
                    height: "100%",
                  }}
                ></ReactPlayer>
             )}
        </div>

        {video && (
            <div className="p-6 bg-background space-y-4">
                <div className="flex items-center justify-between text-sm text-zinc-400">
                    <div className="flex items-center gap-6">
                        {video.uploader && (
                            <div className="flex items-center gap-2">
                                <User className="w-4 h-4 text-zinc-500" />
                                <span>{video.uploader}</span>
                            </div>
                        )}
                        {video.dateStr && (
                            <div className="flex items-center gap-2">
                                <Calendar className="w-4 h-4 text-zinc-500" />
                                <span>{video.dateStr}</span>
                            </div>
                        )}
                    </div>
                    
                   
                </div>
            </div>
        )}

      
      </DialogContent>
    </Dialog>
  )
}

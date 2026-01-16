import type { ReactNode } from "react";
import ReactPlayer from "react-player"
import { useMeasure } from "react-use";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const rootCls = "py-0 overflow-hidden relative bg-black flex items-center justify-center aspect-video flex-1 rounded-xl"

export default function VideoPlayCard({
    title,
    url,
    supportChildren,
    children,
    isPending = false,
}:{
    title: string,
    url?: string | null,
    supportChildren?: boolean,
    children?: ReactNode,
    isPending?: boolean,
}){
    const [containerRef, { height: containerHeight }] = useMeasure<HTMLDivElement>();

    if(isPending){
        return <div 
            ref={containerRef}  
            className={cn(rootCls, "bg-muted ")} 
            style={{
                width: containerHeight * (16 / 9),
            }}>
        </div>
    }
    return (
        <Card 
            ref={containerRef} 
            className={rootCls }
            style={{
                width: containerHeight * (16 / 9),
            }}
        >
            <div className="absolute top-0 right-0 z-10 bg-black/60 text-white text-center py-1 px-2 rounded-bl-xl">
                {title}
            </div>
            <CardContent className="px-0 h-full w-full relative">
                {url &&
                    <ReactPlayer
                        slot="media"
                        src={url}
                        controls={true}
                        style={{
                            width: "100%",
                            height: "100%",
                            objectFit: "contain",
                        }}
                    ></ReactPlayer>
                }
            </CardContent>
            {supportChildren && children}
        </Card>
    )
}

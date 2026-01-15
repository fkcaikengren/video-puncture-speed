import type { ReactNode } from "react";
import ReactPlayer from "react-player"
import { useMeasure } from "react-use";
import { Card, CardContent } from "@/components/ui/card";

export default function VideoPlayCard({
    title,
    url,
    supportChildren,
    children,
}:{
    title: string,
    url?: string | null,
    supportChildren?: boolean,
    children?: ReactNode,
}){
    const [containerRef, { height: containerHeight }] = useMeasure<HTMLDivElement>();

    return (
        <Card 
            ref={containerRef} 
            className="py-0 overflow-hidden relative bg-black flex items-center justify-center aspect-video lg:flex-1"
            style={{
                width: containerHeight * (16 / 9),
            }}
        >
            
            <div className="absolute top-0 right-0 z-10 bg-black text-white text-center py-1 px-1 rounded-bl-xl">
                {title}
            </div>
            {supportChildren ? children : null}
            <CardContent  className="px-0 h-full w-full">
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
        </Card>
    )
}

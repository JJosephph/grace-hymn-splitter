import { useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { FileImage, RotateCcw, UploadCloud } from "lucide-react"
import { toast } from "sonner"
import { useDropzone, type DropEvent } from "react-dropzone"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { callDesktop } from "@/lib/desktop-api"
import { cn } from "@/lib/utils"
import { useAppStore } from "@/store/app-store"

const acceptedTypes = {
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
  "image/webp": [".webp"],
  "image/bmp": [".bmp"],
}

export function UploadPanel() {
  const image = useAppStore((state) => state.image)
  const setImage = useAppStore((state) => state.setImage)
  const clearImage = useAppStore((state) => state.clearImage)
  const chooseImage = useAppStore((state) => state.chooseImage)
  const [dimensions, setDimensions] = useState("")

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: acceptedTypes,
    multiple: false,
    noClick: true,
    onDrop: async (_acceptedFiles, _rejections, event: DropEvent) => {
      const response = await callDesktop<{
        path: string
        url: string
        name?: string
      }>("on_drop", event)

      if (!response.ok || !response.path) {
        toast.error(response.error || "无法读取拖入的图片。")
        return
      }

      setImage({
        path: response.path,
        url: response.url,
        name: response.name || response.path.split(/[\\/]/).pop() || "歌谱图片",
      })
    },
  })

  return (
    <section className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <div className="text-xs font-medium tracking-[0.14em] text-muted-foreground uppercase">
            01
          </div>
          <h2 className="mt-1 text-xl font-semibold tracking-tight">上传歌谱</h2>
        </div>
      </div>

      <AnimatePresence mode="wait" initial={false}>
        {image ? (
          <motion.div
            key="selected"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.18 }}
          >
            <Card className="overflow-hidden">
              <CardContent className="flex gap-4 p-0">
                <div className="flex h-40 w-32 shrink-0 items-center justify-center overflow-hidden bg-muted">
                  <img
                    src={image.url}
                    alt={image.name}
                    className="h-full w-full object-cover"
                    onLoad={(event) => {
                      const target = event.currentTarget
                      setDimensions(
                        `${target.naturalWidth} × ${target.naturalHeight}`,
                      )
                    }}
                  />
                </div>
                <div className="flex min-w-0 flex-1 flex-col justify-between py-4 pr-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <FileImage className="size-4 text-muted-foreground" />
                      <span className="truncate">{image.name}</span>
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                      {dimensions || "正在读取图片…"}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={chooseImage}>
                      <RotateCcw />
                      重新选择
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        clearImage()
                        setDimensions("")
                      }}
                    >
                      移除
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ) : (
          <motion.div
            key="empty"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.18 }}
          >
            <div
              {...getRootProps()}
              className={cn(
                "flex min-h-64 flex-col items-center justify-center rounded-xl border border-dashed bg-muted/25 px-6 text-center transition-colors",
                isDragActive && "border-primary bg-primary/5",
              )}
            >
              <input {...getInputProps()} />
              <div className="flex size-11 items-center justify-center rounded-xl bg-background ring-1 ring-foreground/10">
                <UploadCloud className="size-5 text-muted-foreground" />
              </div>
              <div className="mt-4 text-base font-medium">拖入歌谱图片</div>
              <Button className="mt-5" onClick={chooseImage}>
                <UploadCloud />
                选择图片
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  )
}

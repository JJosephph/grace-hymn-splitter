import {
  FolderOpen,
  Heart,
  RefreshCw,
  SlidersHorizontal,
  Upload,
  WandSparkles,
} from "lucide-react"
import { motion } from "motion/react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { useAppStore } from "@/store/app-store"
import { cn } from "@/lib/utils"
import logo from "@/assets/logo.png"

const steps = [
  { icon: Upload, label: "上传歌谱", value: 1 },
  { icon: SlidersHorizontal, label: "调整选项", value: 2 },
  { icon: WandSparkles, label: "生成大图", value: 3 },
]

export function AppSidebar() {
  const bootstrap = useAppStore((state) => state.bootstrap)
  const image = useAppStore((state) => state.image)
  const job = useAppStore((state) => state.job)
  const openPath = useAppStore((state) => state.openPath)
  const checkUpdates = useAppStore((state) => state.checkUpdates)

  const activeStep = !image ? 1 : job.status === "idle" ? 2 : 3

  return (
    <aside className="flex h-full w-[264px] shrink-0 flex-col border-r bg-sidebar px-4 py-5">
      <div className="flex items-center gap-3 px-1">
        <img
          src={logo}
          alt="恩典歌谱转换PPT大图"
          className="size-10 shrink-0 rounded-[10px]"
        />
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold">恩典歌谱</div>
          <div className="truncate text-xs text-muted-foreground">
            转换 PPT 大图
          </div>
        </div>
      </div>

      <div className="mt-7 px-1">
        <p className="text-[11px] font-medium tracking-[0.14em] text-muted-foreground uppercase">
          恩典简谱分段转换
        </p>
        <p className="mt-2 text-sm leading-6 text-foreground/80">
          让每一段诗歌，都清清楚楚。
        </p>
      </div>

      <nav className="mt-7 flex flex-col gap-1">
        {steps.map((step) => {
          const Icon = step.icon
          const active = activeStep === step.value
          return (
            <div
              key={step.value}
              className={cn(
                "flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-muted-foreground",
              )}
            >
              <Icon className="size-4" />
              <span>{step.label}</span>
            </div>
          )
        })}
      </nav>

      <div className="mt-auto flex flex-col gap-3">
        <motion.button
          type="button"
          whileTap={{ scale: 0.985 }}
          onClick={() =>
            toast.success("愿你的服侍成为祝福，也愿每一次投影都让人更清楚地看见诗歌。")
          }
          className="rounded-xl border bg-background/70 p-3 text-left transition-colors hover:bg-background"
        >
          <div className="flex items-start gap-2.5">
            <Heart className="mt-0.5 size-4 text-rose-500" />
            <div>
              <div className="text-sm font-medium">愿你的服侍成为祝福</div>
              <div className="mt-1 text-xs leading-5 text-muted-foreground">
                把诗歌唱清楚，也把人带到主面前。
              </div>
            </div>
          </div>
        </motion.button>

        <Separator />

        <div className="flex items-center justify-between gap-2 px-1">
          <div className="min-w-0">
            <div className="truncate text-[11px] text-muted-foreground">
              恩典开源免费软件
            </div>
            <div className="truncate text-[11px] text-muted-foreground">
              开发者 WangYufan
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            title="打开软件目录"
            onClick={() => bootstrap?.project_dir && openPath(bootstrap.project_dir)}
          >
            <FolderOpen />
          </Button>
        </div>

        <Button
          variant="ghost"
          size="sm"
          className="justify-start px-1 text-xs text-muted-foreground"
          onClick={checkUpdates}
        >
          <RefreshCw />
          检查更新 · v{bootstrap?.version || "…"}
        </Button>
      </div>
    </aside>
  )
}

import { Type, Layers3 } from "lucide-react"

import { Field, FieldLabel } from "@/components/ui/field"
import { Switch } from "@/components/ui/switch"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group"
import { useAppStore, type BoldMode } from "@/store/app-store"

export function OptionsPanel() {
  const boldMode = useAppStore((state) => state.boldMode)
  const keepMetadata = useAppStore((state) => state.keepMetadata)
  const makeChorus = useAppStore((state) => state.makeChorus)
  const setBoldMode = useAppStore((state) => state.setBoldMode)
  const setKeepMetadata = useAppStore((state) => state.setKeepMetadata)
  const setMakeChorus = useAppStore((state) => state.setMakeChorus)

  return (
    <section className="space-y-4">
      <div>
        <div className="text-xs font-medium tracking-[0.14em] text-muted-foreground uppercase">
          03
        </div>
        <h2 className="mt-1 text-xl font-semibold tracking-tight">制作选项</h2>
      </div>

      <div className="divide-y rounded-xl border bg-card px-4">
        <div className="flex items-center justify-between gap-4 py-4">
          <div className="flex items-center gap-2.5">
            <Type className="size-4 text-muted-foreground" />
            <span className="text-sm font-medium">歌词加粗</span>
          </div>
          <ToggleGroup
            type="single"
            value={boldMode}
            onValueChange={(value) => value && setBoldMode(value as BoldMode)}
            variant="outline"
            size="sm"
          >
            <ToggleGroupItem value="none">原样</ToggleGroupItem>
            <ToggleGroupItem value="light">轻度</ToggleGroupItem>
            <ToggleGroupItem value="strong">明显</ToggleGroupItem>
          </ToggleGroup>
        </div>

        <Field orientation="horizontal" className="py-4">
          <div className="flex items-center gap-2.5">
            <Layers3 className="size-4 text-muted-foreground" />
            <FieldLabel htmlFor="keep-metadata">第一页保留标题信息</FieldLabel>
          </div>
          <Switch
            id="keep-metadata"
            checked={keepMetadata}
            onCheckedChange={setKeepMetadata}
          />
        </Field>

        <Field orientation="horizontal" className="py-4">
          <div className="flex items-center gap-2.5">
            <Layers3 className="size-4 text-muted-foreground" />
            <FieldLabel htmlFor="make-chorus">副歌单独成页</FieldLabel>
          </div>
          <Switch
            id="make-chorus"
            checked={makeChorus}
            onCheckedChange={setMakeChorus}
          />
        </Field>
      </div>
    </section>
  )
}

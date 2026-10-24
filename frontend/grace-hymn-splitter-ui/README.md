# 恩典歌谱转换PPT大图前端

桌面界面源码，使用 React、TypeScript、Vite 和 shadcn/ui Nova。

## 技术栈

- UI 组件：shadcn/ui Nova
- 图标：Lucide
- 动画：Motion
- 可调整布局：react-resizable-panels
- 文件拖入：react-dropzone
- 状态管理：Zustand

## 构建

```powershell
npm ci
npm run build
```

构建结果会写入 `../../hymn_splitter/web/`，由 Python 桌面入口加载。

# 恩典歌谱转换PPT大图

**恩典简谱分段转换**

把一整页多段式简谱，拆成适合 PPT 投影的单段大图。每一段都尽量占满画面，解决诗歌 PPT 字太小、看不清的问题。

这是一个 **恩典开源免费软件**，开发者：**WangYufan**。

![413 第一段示例](docs/examples/413-第1段.png)

## 为什么做这个软件

很多教会做诗歌 PPT 时，会把整页简谱截图放上去。页面上同时有 3 段或 4 段歌词，投影到屏幕上后，每一行都变得很小。

这个软件把同一页歌谱按段拆开：

- 第一段一张图，保留完整标题、作者、调号等元信息；
- 第二段以后每张只保留段号和歌谱，页面更短、歌词更大；
- 有副歌时，可以额外生成一张副歌大图；
- 重复制作同一首诗歌会覆盖旧文件，不会越做越乱。

## 效果示例

第一页保留完整元信息：

![413 第一段](docs/examples/413-第1段.png)

后续页面只保留段号和歌谱，明显更矮、更适合投影：

![413 第二段](docs/examples/413-第2段.png)

副歌可以单独成页：

![500 副歌](docs/examples/500-副歌.png)

三句主歌也能单独拆开：

![665 第二段](docs/examples/665-第2段.png)

## 功能

- 支持 PNG、JPG、JPEG、WEBP、BMP 歌谱图片。
- 支持拖入图片或点击选择图片。
- 自动识别常见简谱版式，普通用户不需要手动填坐标。
- 支持 3 段、4 段歌词，也支持没有副歌或带副歌的歌谱。
- 歌词加粗可选：保持原样、轻度加粗、明显加粗。
- 默认只在第一页保留完整标题元信息。
- 可单独生成副歌页。
- 按“编号-诗歌名”自动建立输出目录。
- 同一首诗歌再次制作时覆盖旧图。
- 提供检查更新入口，方便后续发布新版本。
- 保留 JSON 布局配置，特殊版式仍可精调。

## 快速开始

### 方式一：双击启动

1. 安装 Python 3.10 或更高版本。
2. 双击项目目录里的 `run.bat`。
3. 第一次启动会自动安装 `Pillow` 和 `pywebview`。
4. 在窗口里选择歌谱、填写诗歌名、选择输出目录，然后点击“开始制作”。

### 方式二：命令行启动

```powershell
cd E:\PROJ\hymn-splitter
py -m pip install -r requirements.txt
py run.py
```

`py run.py` 默认打开桌面界面。

如果只需要原来的命令行工作流：

```powershell
py run.py --cli list
py run.py --cli build configs/500-信心使我得胜.json
py run.py --cli auto samples/665-当转眼仰望耶稣.png --output configs/665-自动识别.json
```

## 使用说明

1. **选择歌谱**：拖入图片，或点击“选择图片”。
2. **歌曲信息**：填写诗歌编号和名称；如果图片文件名已经包含编号和名称，软件会自动带出来。
3. **输出目录**：选择输出根目录。软件会在里面自动建立 `<编号-诗歌名>` 子目录。
4. **制作选项**：
   - `歌词加粗`：如果原谱歌词已经足够粗，建议保持原样。
   - `只保留第一页标题元信息`：默认打开。第一页保留完整标题，后续页只保留段号。
   - `副歌单独成页`：歌谱里有副歌时，建议打开。
5. 点击“开始制作”，完成后可以在右侧预览，也可以点击“打开输出目录”。

生成文件示例：

```text
输出根目录/
  413-成圣须用工夫/
    413-成圣须用工夫-第1段.png
    413-成圣须用工夫-第2段.png
    413-成圣须用工夫-第3段.png
    413-成圣须用工夫-第4段.png
```

## 加粗怎么选

- **保持原样**：适合原谱歌词已经比较粗、比较清楚的扫描版。
- **轻度加粗**：适合原谱歌词偏细，但仍然希望保留原本笔画质感。
- **明显加粗**：适合投影后仍然觉得字轻、希望歌词更抢眼的情况。

不建议所有歌谱都强制加粗。扫描件本身已经比较黑时，继续加粗可能让笔画粘连。

## 自动识别和高级配置

普通歌谱直接上传即可。软件会尝试识别：

- 页眉标题区域；
- 每一组简谱行；
- 主歌歌词行；
- 副歌行；
- 段数。

如果遇到出版社的特殊版式，或者识别结果不理想，可以生成一份自动识别配置，再手动微调坐标：

```powershell
py run.py auto samples/新歌谱.png --output configs/新歌谱.json
py run.py build configs/新歌谱.json
```

配置文件里的 `note_crop` 是简谱行范围，`lyric_rows` 是各段歌词行范围。坐标以原图像素为单位。

## 更新检测

软件侧边栏有“检查更新”入口。

默认更新地址写在 `app_config.json`：

```json
{
  "update_url": "https://api.github.com/repos/WangYufan/grace-hymn-splitter/releases/latest",
  "project_url": "https://github.com/WangYufan/grace-hymn-splitter"
}
```

发布到 GitHub Releases 后，把上面的仓库地址改成实际地址即可。也可以临时通过环境变量覆盖：

```powershell
$env:HYMN_SPLITTER_UPDATE_URL="https://api.github.com/repos/你的账号/你的仓库/releases/latest"
```

## 目录结构

```text
hymn-splitter/
  hymn_splitter/
    auto_layout.py     自动识别歌谱版式
    imaging.py         分段、加粗、标题策略和图片输出
    service.py         界面和引擎之间的工作流
    desktop_api.py     桌面界面接口
    gui.py             pywebview 启动入口
    web/               浅色桌面界面
  configs/             已调好的示例布局和特殊版式配置
  samples/             示例歌谱
  outputs/             默认输出目录
  docs/examples/       切图示例
  run.py               双击/命令行入口
  run.bat              Windows 双击启动脚本
  requirements.txt     Python 依赖
  app_config.json      更新地址配置
  LICENSE             MIT 开源许可
```

## 开发和打包

开发运行：

```powershell
py -m pip install -r requirements.txt
py run.py
```

检查语法：

```powershell
py -m compileall -q hymn_splitter run.py
```

项目是普通 Python 项目，后续可以使用 PyInstaller 打包成 Windows 单文件程序。

## 开源说明

- 软件名称：**恩典歌谱转换PPT大图**
- 副标题：**恩典简谱分段转换**
- 开发者：**WangYufan**
- 许可证：MIT
- 声明：**恩典开源免费软件**

你可以自由使用、修改和分发本软件。请在使用歌谱图片时遵守相应版权和教会内部使用规范。

愿这个工具帮助服侍诗歌投影的弟兄姊妹，让会众更清楚地看见歌词、同心歌唱。

# Crop3DPlus

`Crop3DPlus` 是一个面向作物/植株三维重建前处理的工具集合，覆盖了从视频抽帧、前景分割，到 `whitebg` 图像整理和导入 `Agisoft Metashape` 的完整流程。

当前仓库已经不只是若干独立脚本，还新增了一个桌面 GUI 工作台，可在一个窗口里完成以下三类核心任务：

- 视频截帧
- BiRefNet 前景分割
- 抽帧后自动分割

## 1. 当前项目功能

### 1.1 桌面工作台 GUI

相关文件：

- `launch_crop3dplus_gui.py`
- `crop3dplus_gui_app/`

GUI 名称为 `Crop3DPlus Workbench`，是当前仓库最适合日常使用的入口。它把核心流程封装成桌面界面，支持：

- 运行时填写输入输出目录，不必每次手动改脚本源码
- 后台线程执行长任务
- 日志实时输出
- 进度条显示
- `PySide6` 优先，缺失时自动兼容 `PySide2`

GUI 内置三个页面：

1. `视频截帧`
2. `前景分割`
3. `一键串联`

### 1.2 视频抽帧

脚本：`extract_video_frames_ordered.py`

用途：

- 遍历输入根目录下的各个子文件夹
- 每个子文件夹要求恰好有 `4` 个 `mp4`
- 自动识别其中 `1` 个短视频为顶部视角视频
- 其余 `3` 个作为主视频，按拍摄时间排序抽帧
- 输出连续编号的 JPG 图像

当前实现特点：

- 依赖 `ffmpeg` 和 `ffprobe`
- 会读取视频时长与创建时间
- 顶部视频识别规则由 `TOP_VIDEO_MAX_DURATION` 控制，默认 `10` 秒
- 主视频默认各抽 `33` 帧，顶部视频默认抽 `3` 帧

### 1.3 BiRefNet 前景分割

脚本：`Seg_BiRefNet_HR.py`

用途：

- 对输入根目录下的每个子文件夹批量做前景分割
- 使用 Hugging Face 上的 `ZhengPeng7/BiRefNet_HR`
- 为每张图片输出三类结果：
  - `masks/`
  - `rgba/`
  - `whitebg/`

当前实现特点：

- 支持 `configure_runtime(...)` 动态修改模型、尺寸、设备和 FP16
- 首次真正推理时加载模型，后续可复用缓存
- 支持 `cuda` / `cpu` / `auto`
- 默认分割尺寸为 `2048 x 2048`

### 1.4 抽帧与分割一键串联

脚本：`run_extract_and_segment.py`

用途：

- 先运行视频抽帧
- 再对抽出的 RGB 图像运行前景分割

这个脚本适合脚本化批处理；GUI 中的“一键串联”页面则提供了同一流程的图形界面版本。

### 1.5 Metashape 批量导入 `whitebg`

脚本：

- `Meatashape_import_imgs.py`
- `create_chunks_from_whitebg_menu.py`

用途：

- 递归查找根目录下所有名为 `whitebg` 的文件夹
- 每个 `whitebg` 文件夹作为一个 chunk 导入 `Agisoft Metashape`
- chunk 名默认使用 `whitebg` 的上一级目录名
- 如果 chunk 名重复，会自动追加 `_01`、`_02` 等后缀

两者区别：

- `Meatashape_import_imgs.py`：直接执行脚本，弹窗选目录后导入
- `create_chunks_from_whitebg_menu.py`：注册到 Metashape 菜单，带简单界面和进度条

### 1.6 等间隔筛图

脚本：`select_interval_images.py`

用途：

- 读取一个文件夹中的图片
- 优先按 EXIF 拍摄时间排序，没有 EXIF 时回退到文件修改时间
- 从全部图片中均匀选出指定数量
- 复制到输出目录并重新编号

### 1.7 LabelMe 多边形转白底图

脚本：`extract_labelme_polygon.py`

用途：

- 读取 `LabelMe` 标注生成的 `json`
- 提取 polygon 区域
- 把目标抠出并合成到白色背景
- 输出白底结果图

## 2. 推荐使用方式

如果你现在主要是日常处理项目数据，推荐优先使用 GUI：

1. 准备好视频目录或 RGB 图像目录
2. 启动 `Crop3DPlus Workbench`
3. 根据任务选择“视频截帧”“前景分割”或“一键串联”
4. 检查输出目录中的 `masks`、`rgba`、`whitebg`
5. 在 Metashape 中运行导入脚本，把多个 `whitebg` 文件夹批量导入为 chunks

如果你更偏向脚本式批处理，仍然可以直接运行各个 `.py` 文件。

## 3. GUI 启动方式

推荐先安装 GUI 相关依赖：

```powershell
pip install PySide6 torch torchvision transformers pillow
```

如果你的环境里已经装了 `PySide2`，GUI 也会自动兼容。

启动方式一：

```powershell
python .\launch_crop3dplus_gui.py
```

启动方式二：

```powershell
python -m crop3dplus_gui_app
```

说明：

- GUI 中显示的默认路径是示例值，运行前请改成你的实际目录
- GUI 会在后台执行任务，底部显示日志和进度

## 4. 脚本模式使用说明

### 4.1 视频抽帧

先修改 `extract_video_frames_ordered.py` 顶部配置区中的参数：

- `INPUT_DIR`
- `OUTPUT_DIR`
- `FRAMES_PER_MAIN_VIDEO`
- `FRAMES_FOR_TOP_VIDEO`
- `TOP_VIDEO_MAX_DURATION`
- `FFMPEG_CMD`
- `FFPROBE_CMD`

然后执行：

```powershell
python .\extract_video_frames_ordered.py
```

### 4.2 图像分割

先修改 `Seg_BiRefNet_HR.py` 顶部配置区中的参数：

- `INPUT_ROOT`
- `OUTPUT_ROOT`
- `MODEL_ID`
- `IMAGE_SIZE`
- `USE_FP16`
- `DEVICE`

然后执行：

```powershell
python .\Seg_BiRefNet_HR.py
```

### 4.3 一键串联

先修改 `run_extract_and_segment.py` 顶部配置区中的路径参数：

- `VIDEO_INPUT_DIR`
- `FRAME_OUTPUT_DIR`
- `SEG_OUTPUT_DIR`

然后执行：

```powershell
python .\run_extract_and_segment.py
```

### 4.4 Metashape 导入 `whitebg`

方法一：

- 在 Metashape 中运行 `Meatashape_import_imgs.py`

方法二：

- 在 Metashape 中加载 `create_chunks_from_whitebg_menu.py`
- 从菜单点击 `Scripts/Create Chunks from whitebg`

## 5. 目录约定

仓库中的主流程默认围绕如下数据组织方式工作：

```text
项目根目录
├─ Video
│  ├─ 组1
│  │  ├─ *.mp4
│  ├─ 组2
│     ├─ *.mp4
├─ RGB
│  ├─ 组1
│  │  ├─ 1.jpg
│  │  ├─ 2.jpg
│  ├─ 组2
├─ RGB-Seg
│  ├─ 组1
│  │  ├─ masks
│  │  ├─ rgba
│  │  ├─ whitebg
│  ├─ 组2
```

`whitebg` 是后续导入 Metashape 的关键目录。

## 6. 仓库结构

```text
Crop3DPlus
├─ launch_crop3dplus_gui.py
├─ extract_video_frames_ordered.py
├─ Seg_BiRefNet_HR.py
├─ run_extract_and_segment.py
├─ Meatashape_import_imgs.py
├─ create_chunks_from_whitebg_menu.py
├─ select_interval_images.py
├─ extract_labelme_polygon.py
├─ crop3dplus_gui_app/
│  ├─ __main__.py
│  ├─ main.py
│  ├─ tasks.py
│  ├─ qt_compat.py
│  └─ icons/
└─ BiRefNet/
```

说明：

- `crop3dplus_gui_app/` 是桌面 GUI 应用代码
- `BiRefNet/` 目录保留了相关参考代码与资源
- 当前主分割流程实际调用的是 Hugging Face 上的 `ZhengPeng7/BiRefNet_HR`

## 7. 运行环境与依赖

### 7.1 Python

建议：

- Python 3.10 及以上

### 7.2 常用 Python 依赖

主流程常用依赖包括：

- `torch`
- `torchvision`
- `transformers`
- `pillow`
- `PySide6` 或 `PySide2`

一个常见安装示例：

```powershell
pip install torch torchvision transformers pillow PySide6
```

### 7.3 外部依赖

视频抽帧依赖：

- `ffmpeg`
- `ffprobe`

要求：

- 需要提前加入系统 `PATH`

### 7.4 Metashape 相关依赖

Metashape 导入脚本需要：

- `Agisoft Metashape` Python API

另外：

- `create_chunks_from_whitebg_menu.py` 当前直接导入 `PySide2`
- 这类脚本通常需要放在 Metashape 的 Python 环境中运行，或保证当前环境能正确导入 `Metashape`

## 8. 注意事项

1. `extract_video_frames_ordered.py` 当前要求每个子目录恰好有 `4` 个 `mp4` 文件。
2. 顶部视角视频依靠“短视频”规则识别，默认阈值为 `10` 秒。
3. `Seg_BiRefNet_HR.py` 首次运行会下载模型，要求网络可用。
4. 分割过程显存和耗时都比较敏感，建议优先使用 CUDA。
5. 大多数独立脚本仍采用“顶部配置区写路径”的使用方式。
6. GUI 已经把核心流程参数化，如果你不想反复改源码，优先用 GUI。
7. 旧版 README 中提到的串口控制脚本当前仓库里已经不存在，现阶段主功能集中在抽帧、分割、白底整理和 Metashape 导入。

## 9. 项目定位

这个仓库的核心价值不是做成一个复杂框架，而是把拍摄数据处理链条串起来：

`Video -> RGB -> masks / rgba / whitebg -> Metashape`

如果你的工作流本身就是围绕作物三维建模、图像前处理和批量整理展开，这个仓库现在已经能同时提供：

- 脚本式批处理入口
- 更适合日常操作的桌面 GUI 入口

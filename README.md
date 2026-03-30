# Crop3DPlus 项目说明

## 1. 项目简介

`Crop3DPlus` 是一个面向作物/植株三维重建与图像预处理的工具集合，主要用于以下流程：

1. 从多机位或多段视频中按时间顺序抽帧。
2. 使用 `BiRefNet_HR` 对图像做前景分割。
3. 生成透明背景图、白底图和掩膜图。
4. 将白底图批量导入 `Agisoft Metashape`，按文件夹自动创建 chunk。
5. 提供若干辅助工具，例如等间隔抽图、LabelMe 多边形导出白底图、串口转台控制等。

## 2. 主要功能概览

### 2.1 视频抽帧

脚本: `extract_video_frames_ordered.py`

用途：

- 读取输入根目录下的各个子文件夹。
- 每个子文件夹中要求存在 `4` 个 `mp4` 视频。
- 自动识别其中 `1` 个较短视频作为俯视视频，另外 `3` 个作为主视频。
- 按拍摄时间排序后抽帧，并输出为连续编号的 JPG。

特点：

- 依赖 `ffmpeg` 和 `ffprobe`。
- 可自动读取视频创建时间和时长。
- 对横屏俯视视频可自动旋转为竖屏。

### 2.2 图像前景分割

脚本: `Seg_BiRefNet_HR.py`

用途：

- 对输入根目录下的每个子文件夹批量进行前景分割。
- 调用 Hugging Face 上的 `ZhengPeng7/BiRefNet_HR` 模型。
- 为每张图片输出三类结果：
  - `masks/`：掩膜图
  - `rgba/`：透明背景图
  - `whitebg/`：白底图

特点：

- 支持 CUDA 自动加速。
- 显卡支持时可启用 FP16。
- 输出结构清晰，适合后续重建或筛选。

### 2.3 抽帧与分割一键串联

脚本: `run_extract_and_segment.py`

用途：

- 先运行 `extract_video_frames_ordered.py`
- 再运行 `Seg_BiRefNet_HR.py`

适用场景：

- 想把“视频转图片”和“图片分割”合并成一次处理时使用。

### 2.4 Metashape 批量导入白底图

脚本：

- `Meatashape_import_imgs.py`
- `create_chunks_from_whitebg_menu.py`

用途：

- 递归查找项目根目录下所有名为 `whitebg` 的文件夹。
- 每个 `whitebg` 文件夹会被作为一个 chunk 导入 `Agisoft Metashape`。
- chunk 名默认取 `whitebg` 的上一级目录名，重名时自动追加 `_01`、`_02` 等后缀。

区别：

- `Meatashape_import_imgs.py`：直接执行脚本，弹窗选择根目录后导入。
- `create_chunks_from_whitebg_menu.py`：注册到 Metashape 菜单中，带简单界面和进度条，交互更友好。

### 2.5 等间隔筛图

脚本: `select_interval_images.py`

用途：

- 读取一个文件夹中的图片。
- 优先使用 EXIF 拍摄时间排序；没有 EXIF 时回退到文件修改时间。
- 从全部图片中均匀抽取指定数量的图片。
- 将结果复制到输出目录，并重新编号。

适用场景：

- 从大批量图像中快速选出较均匀的一组样本用于建模或标注。

### 2.6 LabelMe 多边形转白底图

脚本: `extract_labelme_polygon.py`

用途：

- 读取 `LabelMe` 标注生成的 `json` 文件。
- 提取其中的 polygon 区域作为前景。
- 将对象合成到白色背景上，并输出为图片。

适用场景：

- 已有人工标注，想快速生成白底训练样本或展示图时使用。

### 2.7 串口转台控制

脚本: `serial_controller.py`

用途：

- 提供一个基于 `tkinter` 的串口控制界面。
- 默认监控 `COM3`，连接后可发送 `GO` 和 `ST` 指令。

适用场景：

- 用于控制拍摄转台或相关串口设备。

## 3. 推荐处理流程

如果你的目标是进行作物图像预处理并导入 Metashape，推荐流程如下：

1. 准备每组拍摄视频，按项目放在 `Video/子文件夹/` 下。
2. 运行 `run_extract_and_segment.py`。
3. 检查输出目录中的：
   - `masks`
   - `rgba`
   - `whitebg`
4. 打开 `Agisoft Metashape`。
5. 运行 `create_chunks_from_whitebg_menu.py` 或 `Meatashape_import_imgs.py`。
6. 选择包含多个 `whitebg` 文件夹的根目录，批量导入 chunk。

## 4. 目录约定

仓库中的脚本默认围绕以下数据组织方式工作：

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

`whitebg` 文件夹是后续导入 Metashape 的关键目录。

## 5. 运行环境与依赖

### 5.1 Python

建议使用：

- Python 3.10 及以上

### 5.2 常用依赖

根据脚本内容，项目至少会用到以下组件：

- `torch`
- `torchvision`
- `transformers`
- `Pillow`
- `pyserial`
- `PySide2`（Metashape 菜单界面脚本需要）
- `Agisoft Metashape` Python API
- `ffmpeg`
- `ffprobe`

安装示例：

```powershell
pip install torch torchvision transformers pillow pyserial
```

说明：

- `Metashape` 相关脚本通常需要在 Metashape 自带的 Python 环境中运行，或确保当前环境能正确导入 `Metashape`。
- `ffmpeg` 和 `ffprobe` 需要提前加入系统 `PATH`。
- `BiRefNet` 子目录是仓库内附带的相关代码与资源，当前主流程主要通过 Hugging Face 模型直接推理。

## 6. 使用示例

### 6.1 运行视频抽帧

先修改 `extract_video_frames_ordered.py` 配置区中的：

- `INPUT_DIR`
- `OUTPUT_DIR`
- `FRAMES_PER_MAIN_VIDEO`
- `FRAMES_FOR_TOP_VIDEO`

然后执行：

```powershell
python .\extract_video_frames_ordered.py
```

### 6.2 运行图像分割

先修改 `Seg_BiRefNet_HR.py` 配置区中的：

- `INPUT_ROOT`
- `OUTPUT_ROOT`

然后执行：

```powershell
python .\Seg_BiRefNet_HR.py
```

### 6.3 一键执行抽帧和分割

先修改 `run_extract_and_segment.py` 中的路径配置，然后执行：

```powershell
python .\run_extract_and_segment.py
```

### 6.4 在 Metashape 中导入白底图

方法一：

- 在 Metashape 中执行 `Meatashape_import_imgs.py`

方法二：

- 在 Metashape 中加载 `create_chunks_from_whitebg_menu.py`
- 从菜单中点击 `Scripts/Create Chunks from whitebg`

## 7. 当前脚本特点与注意事项

1. 大部分脚本采用“配置区写死路径”的方式使用，运行前需要先手动修改输入输出路径。
2. 多数脚本是独立工具脚本，没有统一命令行参数接口。
3. `extract_video_frames_ordered.py` 默认要求每个子目录恰好有 `4` 个 `mp4` 文件，否则会报错。
4. `Seg_BiRefNet_HR.py` 首次运行会下载模型，要求网络通畅。
5. 如果图片数量较大，分割过程会比较耗显存和时间，建议优先使用 CUDA 环境。
6. `create_chunks_from_whitebg_menu.py` 更适合作为日常导入工具，界面比直接脚本方式更清晰。

## 8. 后续可改进方向

如果后续继续维护，建议优先做以下整理：

1. 给所有脚本统一增加命令行参数。
2. 把公共逻辑抽成模块，减少重复代码。
3. 增加一个统一配置文件，而不是在每个脚本里单独改路径。
4. 补充环境安装说明和示例数据说明。
5. 统一脚本命名，例如 `Meatashape_import_imgs.py` 可以根据实际用途调整命名。

## 9. 仓库定位总结

这个仓库的核心价值不在“框架化”，而在“把拍摄、抽帧、抠图、白底整理、Metashape 导入串成一个可落地流程”。如果你的工作流本身就是围绕作物三维重建、图像筛选和批处理展开，这套脚本是比较实用的。

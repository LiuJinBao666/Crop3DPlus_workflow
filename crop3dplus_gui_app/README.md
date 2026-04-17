# Crop3DPlus GUI

桌面应用入口，包含三个流程：

- 视频截帧
- BiRefNet 前景分割
- 抽帧后自动分割

推荐依赖：

```powershell
pip install PySide6 torch torchvision transformers pillow
```

如果环境里已经有 `PySide2`，本应用也会自动兼容。

启动方式：

```powershell
python .\launch_crop3dplus_gui.py
```

或者：

```powershell
python -m crop3dplus_gui_app
```


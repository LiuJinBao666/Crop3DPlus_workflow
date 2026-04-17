from __future__ import annotations

import traceback
from pathlib import Path

from .qt_compat import QT_API, QtCore, QtGui, QtWidgets, Signal
from .tasks import ExtractConfig, PipelineConfig, SegmentConfig, TaskRunner


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WINDOW_TITLE = "Crop3DPlus Workbench"

APP_STYLESHEET = """
QWidget {
    background: #f4f1e8;
    color: #203126;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}
QMainWindow {
    background: #efe8d8;
}
QFrame#card {
    background: #fffdf8;
    border: 1px solid #d9d2c2;
    border-radius: 18px;
}
QFrame#navCard {
    background: #203126;
    border: 0;
    border-radius: 22px;
}
QLabel#heroTitle {
    font-size: 28px;
    font-weight: 700;
    color: #16361f;
}
QLabel#heroSubtitle {
    color: #526257;
    font-size: 13px;
}
QLabel#navTitle {
    color: #f6f2e8;
    font-size: 21px;
    font-weight: 700;
}
QLabel#navBody {
    color: #c9d3ca;
    font-size: 12px;
    line-height: 1.4em;
}
QPushButton#navButton {
    background: transparent;
    border: 1px solid rgba(227, 231, 220, 0.22);
    border-radius: 14px;
    color: #f2f4ee;
    font-size: 14px;
    font-weight: 600;
    padding: 14px 16px;
    text-align: left;
}
QPushButton#navButton:hover {
    border-color: rgba(255, 255, 255, 0.38);
    background: rgba(255, 255, 255, 0.06);
}
QPushButton#navButton:checked {
    background: #d2e3bb;
    color: #1f321d;
    border-color: #d2e3bb;
}
QLabel#pageTitle {
    font-size: 23px;
    font-weight: 700;
    color: #18341e;
}
QLabel#pageBody {
    color: #5c675f;
}
QGroupBox {
    border: 1px solid #dbd4c4;
    border-radius: 16px;
    margin-top: 16px;
    padding-top: 16px;
    font-weight: 600;
    color: #25402a;
    background: #fffdf9;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
}
QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #fbfaf5;
    border: 1px solid #d4cfbf;
    border-radius: 10px;
    padding: 8px 10px;
    selection-background-color: #7e9b58;
}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #7e9b58;
}
QPushButton {
    background: #243d23;
    color: #f6f2e8;
    border: 0;
    border-radius: 12px;
    padding: 10px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background: #2d492c;
}
QPushButton:disabled {
    background: #9ca49d;
    color: #e9ede7;
}
QPushButton#secondaryButton {
    background: #ece4d3;
    color: #284029;
    border: 1px solid #d1c7b2;
}
QPushButton#secondaryButton:hover {
    background: #e3d9c5;
}
QCheckBox {
    spacing: 8px;
}
QProgressBar {
    background: #ece6d8;
    border-radius: 9px;
    border: 1px solid #d8d1c2;
    min-height: 18px;
    text-align: center;
}
QProgressBar::chunk {
    background: #88a85b;
    border-radius: 8px;
}
QScrollArea {
    border: 0;
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px 0 4px 0;
}
QScrollBar::handle:vertical {
    background: #c0b8a6;
    border-radius: 5px;
    min-height: 28px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""


class PathPicker(QtWidgets.QWidget):
    def __init__(self, label: str, default_value: str = "", parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.label = QtWidgets.QLabel(label)
        self.label.setMinimumWidth(86)
        self.line_edit = QtWidgets.QLineEdit(default_value)
        self.button = QtWidgets.QPushButton("选择文件夹")
        self.button.setObjectName("secondaryButton")

        layout.addWidget(self.label)
        layout.addWidget(self.line_edit, 1)
        layout.addWidget(self.button)

        self.button.clicked.connect(self._choose_folder)

    def _choose_folder(self) -> None:
        start_dir = self.line_edit.text().strip() or str(PROJECT_ROOT)
        selected = QtWidgets.QFileDialog.getExistingDirectory(self, "选择文件夹", start_dir)
        if selected:
            self.line_edit.setText(selected)

    def text(self) -> str:
        return self.line_edit.text().strip()


class NoWheelSpinBox(QtWidgets.QSpinBox):
    def wheelEvent(self, event) -> None:
        event.ignore()


class NoWheelDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    def wheelEvent(self, event) -> None:
        event.ignore()


class NoWheelComboBox(QtWidgets.QComboBox):
    def wheelEvent(self, event) -> None:
        event.ignore()


class WorkerThread(QtCore.QThread):
    log_message = Signal(str)
    progress_changed = Signal(int, str)
    task_finished = Signal(bool, str)

    def __init__(self, mode: str, config, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self.mode = mode
        self.config = config

    def _log(self, message: str) -> None:
        self.log_message.emit(message)

    def _progress(self, value: int, message: str) -> None:
        self.progress_changed.emit(value, message)

    def run(self) -> None:
        runner = TaskRunner(self._log, self._progress)
        try:
            if self.mode == "extract":
                runner.run_extract(self.config)
                self.task_finished.emit(True, "视频截帧处理完成。")
            elif self.mode == "segment":
                runner.run_segment(self.config)
                self.task_finished.emit(True, "前景分割处理完成。")
            elif self.mode == "pipeline":
                runner.run_pipeline(self.config)
                self.task_finished.emit(True, "一键串联处理完成。")
            else:
                raise ValueError(f"Unknown task mode: {self.mode}")
        except Exception as exc:
            self.log_message.emit(traceback.format_exc())
            self.task_finished.emit(False, str(exc))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker: WorkerThread | None = None
        self.nav_buttons: list[QtWidgets.QPushButton] = []
        self.run_buttons: list[QtWidgets.QPushButton] = []

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1450, 920)
        self.setMinimumSize(1200, 760)

        self._build_ui()
        self._apply_window_icon()

    def _apply_window_icon(self) -> None:
        icon = QtGui.QIcon()
        pixmap = QtGui.QPixmap(64, 64)
        pixmap.fill(QtGui.QColor("#203126"))
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor("#d2e3bb"))
        painter.drawRoundedRect(8, 8, 48, 48, 14, 14)
        painter.setPen(QtGui.QColor("#203126"))
        font = QtGui.QFont("Segoe UI", 26)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, "C")
        painter.end()
        icon.addPixmap(pixmap)
        self.setWindowIcon(icon)

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(16)

        root.addWidget(self._build_hero_card())

        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setSpacing(16)
        root.addLayout(content_layout, 1)

        content_layout.addWidget(self._build_nav_panel(), 0)
        content_layout.addWidget(self._build_pages_panel(), 1)

        root.addWidget(self._build_console_card(), 0)

    def _build_hero_card(self) -> QtWidgets.QWidget:
        card = QtWidgets.QFrame()
        card.setObjectName("card")
        layout = QtWidgets.QHBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(20)

        text_col = QtWidgets.QVBoxLayout()
        text_col.setSpacing(8)
        title = QtWidgets.QLabel("Crop3DPlus 桌面工作台")
        title.setObjectName("heroTitle")
        subtitle = QtWidgets.QLabel(
            "面向作物三维建模前处理的统一桌面入口。你可以在一个应用里完成视频截帧、BiRefNet 前景分割，以及抽帧后自动分割。"
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("heroSubtitle")
        text_col.addWidget(title)
        text_col.addWidget(subtitle)

        badges = QtWidgets.QHBoxLayout()
        badges.setSpacing(10)
        for text in (
            f"Qt: {QT_API}",
            "模型: BiRefNet_HR",
            "后台: FFmpeg + Torch",
        ):
            badge = QtWidgets.QLabel(text)
            badge.setStyleSheet(
                "QLabel { background: #e7efda; color: #2d472d; border-radius: 10px; padding: 8px 12px; font-weight: 600; }"
            )
            badges.addWidget(badge)
        badges.addStretch(1)
        text_col.addLayout(badges)

        art = QtWidgets.QFrame()
        art.setFixedWidth(240)
        art.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #213325, stop:1 #506b34);"
            "border-radius: 20px; border: 1px solid #31492e; }"
        )
        art_layout = QtWidgets.QVBoxLayout(art)
        art_layout.setContentsMargins(18, 18, 18, 18)
        art_layout.setSpacing(8)
        art_title = QtWidgets.QLabel("Workflow")
        art_title.setStyleSheet("QLabel { color: #f4f1e8; font-size: 18px; font-weight: 700; background: transparent; }")
        art_body = QtWidgets.QLabel("Video\n↓\nRGB Frames\n↓\nMasks / RGBA / WhiteBG")
        art_body.setStyleSheet("QLabel { color: #d8e3d1; font-size: 14px; font-weight: 600; background: transparent; }")
        art_body.setAlignment(QtCore.Qt.AlignCenter)
        art_layout.addWidget(art_title)
        art_layout.addStretch(1)
        art_layout.addWidget(art_body)
        art_layout.addStretch(1)

        layout.addLayout(text_col, 1)
        layout.addWidget(art)
        return card

    def _build_nav_panel(self) -> QtWidgets.QWidget:
        card = QtWidgets.QFrame()
        card.setObjectName("navCard")
        card.setMinimumWidth(280)
        card.setMaximumWidth(320)

        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(20, 22, 20, 22)
        layout.setSpacing(14)

        title = QtWidgets.QLabel("处理功能")
        title.setObjectName("navTitle")
        body = QtWidgets.QLabel(
            "选择一个处理流程，在右侧填写参数。所有长时间任务都会在后台执行，日志和进度会持续显示在底部。"
        )
        body.setWordWrap(True)
        body.setObjectName("navBody")
        layout.addWidget(title)
        layout.addWidget(body)

        self.button_group = QtWidgets.QButtonGroup(self)
        self.button_group.setExclusive(True)

        for index, label in enumerate(("视频截帧", "前景分割", "一键串联")):
            button = QtWidgets.QPushButton(label)
            button.setCheckable(True)
            button.setObjectName("navButton")
            button.clicked.connect(lambda checked, i=index: self.stack.setCurrentIndex(i))
            self.button_group.addButton(button, index)
            self.nav_buttons.append(button)
            layout.addWidget(button)

        self.nav_buttons[0].setChecked(True)
        layout.addStretch(1)
        return card

    def _build_pages_panel(self) -> QtWidgets.QWidget:
        container = QtWidgets.QFrame()
        container.setObjectName("card")
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)

        self.stack = QtWidgets.QStackedWidget()
        self.stack.addWidget(self._build_extract_page())
        self.stack.addWidget(self._build_segment_page())
        self.stack.addWidget(self._build_pipeline_page())

        layout.addWidget(self.stack)
        return container

    def _build_page_shell(self, title: str, body: str) -> tuple[QtWidgets.QWidget, QtWidgets.QVBoxLayout]:
        page = QtWidgets.QWidget()
        page_layout = QtWidgets.QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)

        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("pageTitle")
        body_label = QtWidgets.QLabel(body)
        body_label.setWordWrap(True)
        body_label.setObjectName("pageBody")
        layout.addWidget(title_label)
        layout.addWidget(body_label)

        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        return page, layout

    def _build_extract_page(self) -> QtWidgets.QWidget:
        page, layout = self._build_page_shell(
            "视频截帧",
            "按 `extract_video_frames_ordered.py` 的逻辑处理每个子文件夹。每个子文件夹要求有 4 个 MP4，其中 1 个短视频会被识别为顶部视角。",
        )

        io_group = QtWidgets.QGroupBox("输入与输出")
        io_layout = QtWidgets.QVBoxLayout(io_group)
        io_layout.setSpacing(12)
        self.extract_input = PathPicker("视频目录", r"F:/Crop3DPlus/Project/Video")
        self.extract_output = PathPicker("输出目录", r"F:/Crop3DPlus/Project/RGB")
        io_layout.addWidget(self.extract_input)
        io_layout.addWidget(self.extract_output)

        settings_group = QtWidgets.QGroupBox("抽帧参数")
        form = QtWidgets.QFormLayout(settings_group)
        form.setLabelAlignment(QtCore.Qt.AlignLeft)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)

        self.extract_main_frames = NoWheelSpinBox()
        self.extract_main_frames.setRange(1, 500)
        self.extract_main_frames.setValue(33)

        self.extract_top_frames = NoWheelSpinBox()
        self.extract_top_frames.setRange(1, 100)
        self.extract_top_frames.setValue(3)

        self.extract_top_duration = NoWheelDoubleSpinBox()
        self.extract_top_duration.setRange(0.1, 600.0)
        self.extract_top_duration.setDecimals(2)
        self.extract_top_duration.setSingleStep(0.5)
        self.extract_top_duration.setValue(10.0)

        self.extract_ffmpeg = QtWidgets.QLineEdit("ffmpeg")
        self.extract_ffprobe = QtWidgets.QLineEdit("ffprobe")

        form.addRow("主视频帧数", self.extract_main_frames)
        form.addRow("顶部视频帧数", self.extract_top_frames)
        form.addRow("顶部视频阈值(秒)", self.extract_top_duration)
        form.addRow("ffmpeg 命令", self.extract_ffmpeg)
        form.addRow("ffprobe 命令", self.extract_ffprobe)

        run_button = QtWidgets.QPushButton("开始视频截帧")
        run_button.clicked.connect(lambda: self.start_task("extract"))
        self.run_buttons.append(run_button)

        layout.addWidget(io_group)
        layout.addWidget(settings_group)
        layout.addStretch(1)
        layout.addWidget(run_button)
        return page

    def _build_segment_page(self) -> QtWidgets.QWidget:
        page, layout = self._build_page_shell(
            "前景分割",
            "按 `Seg_BiRefNet_HR.py` 的逻辑输出 `masks`、`rgba` 和 `whitebg`。模型只会在第一次真正执行分割时加载，后续会复用。",
        )

        io_group = QtWidgets.QGroupBox("输入与输出")
        io_layout = QtWidgets.QVBoxLayout(io_group)
        io_layout.setSpacing(12)
        self.segment_input = PathPicker("图像目录", r"F:/Crop3DPlus/Project/RGB")
        self.segment_output = PathPicker("输出目录", r"F:/Crop3DPlus/Project/RGB-Seg")
        io_layout.addWidget(self.segment_input)
        io_layout.addWidget(self.segment_output)

        settings_group = QtWidgets.QGroupBox("模型参数")
        form = QtWidgets.QFormLayout(settings_group)
        form.setLabelAlignment(QtCore.Qt.AlignLeft)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)

        self.segment_model_id = QtWidgets.QLineEdit("ZhengPeng7/BiRefNet_HR")

        image_size_row = QtWidgets.QHBoxLayout()
        self.segment_width = NoWheelSpinBox()
        self.segment_width.setRange(256, 8192)
        self.segment_width.setSingleStep(256)
        self.segment_width.setValue(2048)
        self.segment_height = NoWheelSpinBox()
        self.segment_height.setRange(256, 8192)
        self.segment_height.setSingleStep(256)
        self.segment_height.setValue(2048)
        image_size_row.addWidget(self.segment_width)
        image_size_row.addWidget(QtWidgets.QLabel("x"))
        image_size_row.addWidget(self.segment_height)
        image_size_row.addStretch(1)
        image_size_widget = QtWidgets.QWidget()
        image_size_widget.setLayout(image_size_row)

        self.segment_use_fp16 = QtWidgets.QCheckBox("CUDA 可用时使用 FP16")
        self.segment_use_fp16.setChecked(True)

        self.segment_device = NoWheelComboBox()
        self.segment_device.addItems(["auto", "cuda", "cpu"])

        form.addRow("模型 ID", self.segment_model_id)
        form.addRow("缩放尺寸", image_size_widget)
        form.addRow("推理精度", self.segment_use_fp16)
        form.addRow("运行设备", self.segment_device)

        run_button = QtWidgets.QPushButton("开始前景分割")
        run_button.clicked.connect(lambda: self.start_task("segment"))
        self.run_buttons.append(run_button)

        layout.addWidget(io_group)
        layout.addWidget(settings_group)
        layout.addStretch(1)
        layout.addWidget(run_button)
        return page

    def _build_pipeline_page(self) -> QtWidgets.QWidget:
        page, layout = self._build_page_shell(
            "一键串联",
            "按 `run_extract_and_segment.py` 的先抽帧、再分割顺序运行，适合完整批处理。下面可以分别配置抽帧阶段和分割阶段的关键参数。",
        )

        io_group = QtWidgets.QGroupBox("流程目录")
        io_layout = QtWidgets.QVBoxLayout(io_group)
        io_layout.setSpacing(12)
        self.pipeline_video_input = PathPicker("视频目录", r"F:/Crop3DPlus/Project/Video")
        self.pipeline_frame_output = PathPicker("RGB 输出", r"F:/Crop3DPlus/Project/RGB")
        self.pipeline_seg_output = PathPicker("分割输出", r"F:/Crop3DPlus/Project/RGB-Seg")
        io_layout.addWidget(self.pipeline_video_input)
        io_layout.addWidget(self.pipeline_frame_output)
        io_layout.addWidget(self.pipeline_seg_output)

        extract_group = QtWidgets.QGroupBox("抽帧阶段")
        extract_form = QtWidgets.QFormLayout(extract_group)
        extract_form.setHorizontalSpacing(18)
        extract_form.setVerticalSpacing(12)

        self.pipeline_main_frames = NoWheelSpinBox()
        self.pipeline_main_frames.setRange(1, 500)
        self.pipeline_main_frames.setValue(33)
        self.pipeline_top_frames = NoWheelSpinBox()
        self.pipeline_top_frames.setRange(1, 100)
        self.pipeline_top_frames.setValue(3)
        self.pipeline_top_duration = NoWheelDoubleSpinBox()
        self.pipeline_top_duration.setRange(0.1, 600.0)
        self.pipeline_top_duration.setDecimals(2)
        self.pipeline_top_duration.setSingleStep(0.5)
        self.pipeline_top_duration.setValue(10.0)
        self.pipeline_ffmpeg = QtWidgets.QLineEdit("ffmpeg")
        self.pipeline_ffprobe = QtWidgets.QLineEdit("ffprobe")

        extract_form.addRow("主视频帧数", self.pipeline_main_frames)
        extract_form.addRow("顶部视频帧数", self.pipeline_top_frames)
        extract_form.addRow("顶部视频阈值(秒)", self.pipeline_top_duration)
        extract_form.addRow("ffmpeg 命令", self.pipeline_ffmpeg)
        extract_form.addRow("ffprobe 命令", self.pipeline_ffprobe)

        segment_group = QtWidgets.QGroupBox("分割阶段")
        segment_form = QtWidgets.QFormLayout(segment_group)
        segment_form.setHorizontalSpacing(18)
        segment_form.setVerticalSpacing(12)

        self.pipeline_model_id = QtWidgets.QLineEdit("ZhengPeng7/BiRefNet_HR")
        size_row = QtWidgets.QHBoxLayout()
        self.pipeline_width = NoWheelSpinBox()
        self.pipeline_width.setRange(256, 8192)
        self.pipeline_width.setSingleStep(256)
        self.pipeline_width.setValue(2048)
        self.pipeline_height = NoWheelSpinBox()
        self.pipeline_height.setRange(256, 8192)
        self.pipeline_height.setSingleStep(256)
        self.pipeline_height.setValue(2048)
        size_row.addWidget(self.pipeline_width)
        size_row.addWidget(QtWidgets.QLabel("x"))
        size_row.addWidget(self.pipeline_height)
        size_row.addStretch(1)
        size_widget = QtWidgets.QWidget()
        size_widget.setLayout(size_row)

        self.pipeline_use_fp16 = QtWidgets.QCheckBox("CUDA 可用时使用 FP16")
        self.pipeline_use_fp16.setChecked(True)
        self.pipeline_device = NoWheelComboBox()
        self.pipeline_device.addItems(["auto", "cuda", "cpu"])

        segment_form.addRow("模型 ID", self.pipeline_model_id)
        segment_form.addRow("缩放尺寸", size_widget)
        segment_form.addRow("推理精度", self.pipeline_use_fp16)
        segment_form.addRow("运行设备", self.pipeline_device)

        run_button = QtWidgets.QPushButton("开始一键串联")
        run_button.clicked.connect(lambda: self.start_task("pipeline"))
        self.run_buttons.append(run_button)

        layout.addWidget(io_group)
        layout.addWidget(extract_group)
        layout.addWidget(segment_group)
        layout.addStretch(1)
        layout.addWidget(run_button)
        return page

    def _build_console_card(self) -> QtWidgets.QWidget:
        card = QtWidgets.QFrame()
        card.setObjectName("card")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        top = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel("就绪。请选择功能并填写目录。")
        self.status_label.setStyleSheet("QLabel { color: #304336; font-weight: 600; }")
        clear_button = QtWidgets.QPushButton("清空日志")
        clear_button.setObjectName("secondaryButton")
        clear_button.clicked.connect(lambda: self.log_edit.setPlainText(""))
        top.addWidget(self.status_label, 1)
        top.addWidget(clear_button)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.log_edit = QtWidgets.QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(180)

        layout.addLayout(top)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_edit)
        return card

    def append_log(self, message: str) -> None:
        self.log_edit.appendPlainText(message.rstrip())
        self.log_edit.verticalScrollBar().setValue(self.log_edit.verticalScrollBar().maximum())

    def set_busy(self, busy: bool) -> None:
        for button in self.nav_buttons:
            button.setEnabled(not busy)
        for button in self.run_buttons:
            button.setEnabled(not busy)

    def build_extract_config(self) -> ExtractConfig:
        return ExtractConfig(
            input_dir=Path(self.extract_input.text()),
            output_dir=Path(self.extract_output.text()),
            frames_per_main_video=self.extract_main_frames.value(),
            frames_for_top_video=self.extract_top_frames.value(),
            top_video_max_duration=self.extract_top_duration.value(),
            ffmpeg_cmd=self.extract_ffmpeg.text().strip(),
            ffprobe_cmd=self.extract_ffprobe.text().strip(),
        )

    def build_segment_config(self) -> SegmentConfig:
        return SegmentConfig(
            input_root=Path(self.segment_input.text()),
            output_root=Path(self.segment_output.text()),
            model_id=self.segment_model_id.text().strip(),
            image_width=self.segment_width.value(),
            image_height=self.segment_height.value(),
            use_fp16=self.segment_use_fp16.isChecked(),
            device=self.segment_device.currentText(),
        )

    def build_pipeline_config(self) -> PipelineConfig:
        return PipelineConfig(
            video_input_dir=Path(self.pipeline_video_input.text()),
            frame_output_dir=Path(self.pipeline_frame_output.text()),
            seg_output_dir=Path(self.pipeline_seg_output.text()),
            frames_per_main_video=self.pipeline_main_frames.value(),
            frames_for_top_video=self.pipeline_top_frames.value(),
            top_video_max_duration=self.pipeline_top_duration.value(),
            ffmpeg_cmd=self.pipeline_ffmpeg.text().strip(),
            ffprobe_cmd=self.pipeline_ffprobe.text().strip(),
            model_id=self.pipeline_model_id.text().strip(),
            image_width=self.pipeline_width.value(),
            image_height=self.pipeline_height.value(),
            use_fp16=self.pipeline_use_fp16.isChecked(),
            device=self.pipeline_device.currentText(),
        )

    def start_task(self, mode: str) -> None:
        if self.worker is not None and self.worker.isRunning():
            QtWidgets.QMessageBox.warning(self, WINDOW_TITLE, "当前已有任务在运行，请等待完成。")
            return

        if mode == "extract":
            config = self.build_extract_config()
            intro = "准备开始视频截帧..."
        elif mode == "segment":
            config = self.build_segment_config()
            intro = "准备开始前景分割..."
        elif mode == "pipeline":
            config = self.build_pipeline_config()
            intro = "准备开始一键串联处理..."
        else:
            raise ValueError(f"Unknown task mode: {mode}")

        self.log_edit.appendPlainText("")
        self.append_log(intro)
        self.progress_bar.setValue(0)
        self.status_label.setText("任务运行中...")
        self.set_busy(True)

        self.worker = WorkerThread(mode, config, self)
        self.worker.log_message.connect(self.append_log)
        self.worker.progress_changed.connect(self.on_progress_changed)
        self.worker.task_finished.connect(self.on_task_finished)
        self.worker.start()

    def on_progress_changed(self, value: int, message: str) -> None:
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def on_task_finished(self, ok: bool, message: str) -> None:
        self.set_busy(False)
        self.progress_bar.setValue(100 if ok else self.progress_bar.value())
        self.status_label.setText(message if ok else f"任务失败: {message}")
        self.append_log(message)

        if not ok:
            QtWidgets.QMessageBox.critical(self, WINDOW_TITLE, message)

        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None


def main() -> None:
    app = QtWidgets.QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QtWidgets.QApplication([])

    app.setApplicationName(WINDOW_TITLE)
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    window.show()

    if owns_app:
        app.exec_() if hasattr(app, "exec_") else app.exec()


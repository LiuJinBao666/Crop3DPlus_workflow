import Metashape
import os
from PySide2 import QtCore, QtWidgets


IMAGE_EXTS = {".jpg", ".jpeg", ".tif", ".tiff", ".png", ".bmp"}


class WhitebgImportDlg(QtWidgets.QDialog):

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Create Chunks from whitebg")
        self.resize(520, 180)

        self.root_dir = ""

        self.lblPath = QtWidgets.QLabel("Root folder:")
        self.editPath = QtWidgets.QLineEdit()
        self.editPath.setReadOnly(True)

        self.btnBrowse = QtWidgets.QPushButton("Browse...")
        self.btnRun = QtWidgets.QPushButton("Run")
        self.btnClose = QtWidgets.QPushButton("Close")

        self.pBar = QtWidgets.QProgressBar()
        self.pBar.setValue(0)

        self.txtInfo = QtWidgets.QLabel(
            "Select a root folder.\n"
            "The script will search all subfolders and import every 'whitebg' folder as one chunk."
        )
        self.txtInfo.setWordWrap(True)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.lblPath, 0, 0)
        layout.addWidget(self.editPath, 0, 1)
        layout.addWidget(self.btnBrowse, 0, 2)
        layout.addWidget(self.txtInfo, 1, 0, 1, 3)
        layout.addWidget(self.btnRun, 2, 1)
        layout.addWidget(self.btnClose, 2, 2)
        layout.addWidget(self.pBar, 3, 0, 1, 3)
        self.setLayout(layout)

        self.btnBrowse.clicked.connect(self.choose_folder)
        self.btnRun.clicked.connect(self.run_import)
        self.btnClose.clicked.connect(self.reject)

        self.exec()

    def choose_folder(self):
        folder = Metashape.app.getExistingDirectory("Select root folder")
        if folder:
            self.root_dir = folder
            self.editPath.setText(folder)

    def get_unique_chunk_label(self, doc, base_label):
        existing = {chunk.label for chunk in doc.chunks if chunk.label}

        if base_label not in existing:
            return base_label

        index = 1
        while True:
            new_label = "{}_{:02d}".format(base_label, index)
            if new_label not in existing:
                return new_label
            index += 1

    def collect_images(self, folder):
        files = []
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                ext = os.path.splitext(name)[1].lower()
                if ext in IMAGE_EXTS:
                    files.append(path)
        return files

    def find_whitebg_folders(self, root_dir):
        results = []
        for current_root, dirs, files in os.walk(root_dir):
            if os.path.basename(current_root).lower() == "whitebg":
                results.append(current_root)
        results.sort()
        return results

    def run_import(self):
        app = QtWidgets.QApplication.instance()
        doc = Metashape.app.document

        if not self.root_dir or not os.path.isdir(self.root_dir):
            Metashape.app.messageBox("Please select a valid root folder first.")
            return

        whitebg_folders = self.find_whitebg_folders(self.root_dir)

        if not whitebg_folders:
            Metashape.app.messageBox("No 'whitebg' folders were found.")
            return

        print("Script started...")
        print("Root folder: {}".format(self.root_dir))
        print("Found {} whitebg folder(s).".format(len(whitebg_folders)))

        created_count = 0
        skipped_count = 0
        total = len(whitebg_folders)

        for i, whitebg_dir in enumerate(whitebg_folders):
            parent_folder = os.path.basename(os.path.dirname(whitebg_dir))
            images = self.collect_images(whitebg_dir)

            if not images:
                print("[Skipped] No images in: {}".format(whitebg_dir))
                skipped_count += 1
                self.pBar.setValue(int((i + 1) / total * 100))
                app.processEvents()
                continue

            chunk = doc.addChunk()
            chunk.label = self.get_unique_chunk_label(doc, parent_folder)
            chunk.addPhotos(images)

            created_count += 1
            print("[OK] Chunk: {} | Photos: {}".format(chunk.label, len(images)))

            self.pBar.setValue(int((i + 1) / total * 100))
            app.processEvents()

        self.pBar.setValue(100)

        msg = (
            "Finished!\n\n"
            "Created chunks: {}\n"
            "Skipped folders: {}"
        ).format(created_count, skipped_count)

        print(msg)
        Metashape.app.messageBox(msg)


def create_chunks_from_whitebg():
    app = QtWidgets.QApplication.instance()
    parent = app.activeWindow()
    dlg = WhitebgImportDlg(parent)


label = "Scripts/Create Chunks from whitebg"
Metashape.app.addMenuItem(label, create_chunks_from_whitebg)
print("To execute this script press {}".format(label))
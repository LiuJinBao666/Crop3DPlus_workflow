# Exports depth map of each camera.
#
# This is python script for Metashape Pro. Scripts repository: https://github.com/agisoft-llc/metashape-scripts
 
import Metashape
import os
import re
from PySide2 import QtGui, QtCore, QtWidgets
 
try:
    import numpy as np
except ImportError:
    print("Please ensure that you installed numpy via 'pip install numpy' - see https://agisoft.freshdesk.com/support/solutions/articles/31000136860-how-to-install-external-python-module-to-metashape-professional-package")
    raise
 
 
class ExportDepthDlg(QtWidgets.QDialog):

    invalid_path_chars = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

    @staticmethod
    def safe_path_name(name, fallback):
        name = ExportDepthDlg.invalid_path_chars.sub("_", str(name)).strip()
        name = name.rstrip(". ")
        return name or fallback

    @staticmethod
    def unique_path(path):
        if not os.path.exists(path):
            return path

        folder, filename = os.path.split(path)
        base, ext = os.path.splitext(filename)
        index = 2
        while True:
            candidate = os.path.join(folder, "{}_{}{}".format(base, index, ext))
            if not os.path.exists(candidate):
                return candidate
            index += 1

    @staticmethod
    def unique_chunk_folder(output_folder, chunk_name, used_folders):
        chunk_folder = os.path.join(output_folder, chunk_name)
        folder_key = os.path.normcase(os.path.abspath(chunk_folder))
        if folder_key not in used_folders:
            used_folders.add(folder_key)
            return chunk_folder

        index = 2
        while True:
            candidate = os.path.join(output_folder, "{}_{}".format(chunk_name, index))
            folder_key = os.path.normcase(os.path.abspath(candidate))
            if folder_key not in used_folders:
                used_folders.add(folder_key)
                return candidate
            index += 1
 
    def __init__ (self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle("Export depth maps")
 
        self.btnQuit = QtWidgets.QPushButton("&Close")
        self.btnP1 = QtWidgets.QPushButton("&Export")
        self.pBar = QtWidgets.QProgressBar()
        self.pBar.setTextVisible(False)
        self.output_folder = ""
        self.exporting = False
 
        # self.selTxt =QtWidgets.QLabel()
        # self.selTxt.setText("Apply to:")
        self.radioBtn_all = QtWidgets.QRadioButton("Apply to all cameras in all chunks")
        self.radioBtn_sel = QtWidgets.QRadioButton("Apply to selected")
        self.radioBtn_all.setChecked(True)
        self.radioBtn_sel.setChecked(False)
 
        self.formTxt = QtWidgets.QLabel()
        self.formTxt.setText("Export format:")
        self.formCmb = QtWidgets.QComboBox()
        self.formCmb.addItem("1-band F32")
        self.formCmb.addItem("Grayscale 8-bit")
        self.formCmb.addItem("Grayscale 16-bit")
 
        # creating layout
        layout = QtWidgets.QGridLayout()
        layout.setSpacing(10)
        layout.addWidget(self.radioBtn_all, 0, 0)
        layout.addWidget(self.radioBtn_sel, 1, 0)
        layout.addWidget(self.formTxt, 0, 1)
        layout.addWidget(self.formCmb, 1, 1)
        layout.addWidget(self.btnP1, 2, 0)
        layout.addWidget(self.btnQuit, 2, 1)
        layout.addWidget(self.pBar, 3, 0, 1, 2)
        self.setLayout(layout)  
 
        QtCore.QObject.connect(self.btnP1, QtCore.SIGNAL("clicked()"), self.export_depth)
        QtCore.QObject.connect(self.btnQuit, QtCore.SIGNAL("clicked()"), self, QtCore.SLOT("reject()"))    
 
        self.exec()
 
    def export_depth(self):
        if self.exporting:
            return 0

        self.exporting = True
        self.btnP1.setEnabled(False)
        try:
            return self._export_depth()
        finally:
            self.exporting = False
            self.btnP1.setEnabled(True)

    def _export_depth(self):
 
        app = QtWidgets.QApplication.instance()
        global doc
        doc = Metashape.app.document
        chunks = list(doc.chunks)

        if not len(chunks):
            print("Script aborted: no chunks found.")
            return 0
 
        if self.formCmb.currentText() == "1-band F32":
            F32 = True
        elif self.formCmb.currentText() == "Grayscale 8-bit":
            F32 = False
        elif self.formCmb.currentText() == "Grayscale 16-bit":
            F32 = False
        else:
            print("Script aborted: unexpected error.")
            return 0
 
        export_items = list()
        if self.radioBtn_sel.isChecked():
            for chunk in chunks:
                for camera in chunk.cameras:
                    if camera.selected and camera.transform and (camera.type == Metashape.Camera.Type.Regular) and camera in chunk.depth_maps.keys():
                        export_items.append((chunk, camera))
        elif self.radioBtn_all.isChecked():
            for chunk in chunks:
                for camera in chunk.cameras:
                    if camera.transform and camera.type == Metashape.Camera.Type.Regular and camera in chunk.depth_maps.keys():
                        export_items.append((chunk, camera))
 
        if not len(export_items):
            print("Script aborted: nothing to export.")
            return 0
 
        if not self.output_folder or not os.path.isdir(self.output_folder):
            self.output_folder = Metashape.app.getExistingDirectory("Specify the export folder:")

        output_folder = self.output_folder
        if not output_folder:
            print("Script aborted: invalid output folder.")    
            return 0
 
        print("Script started...")
        app.processEvents()
        count = 0
        chunk_folders = dict()
        used_chunk_folders = set()
        
        for chunk, camera in export_items:
            chunk_key = id(chunk)
            if chunk_key in chunk_folders:
                chunk_folder = chunk_folders[chunk_key]
            else:
                chunk_name = self.safe_path_name(chunk.label, "Chunk")
                chunk_folder = self.unique_chunk_folder(output_folder, chunk_name, used_chunk_folders)
                chunk_folders[chunk_key] = chunk_folder
                os.makedirs(chunk_folder, exist_ok=True)

            if chunk.transform.scale:
                scale = chunk.transform.scale
            else:
                scale = 1

            depth = chunk.depth_maps[camera].image()
            if not F32:
                img = np.frombuffer(depth.tostring(), dtype=np.float32)
                depth_range = img.max() - img.min()
                img = depth - img.min()
                img = img * (1. / depth_range)
                if self.formCmb.currentText() == "Grayscale 8-bit":
                    img = img.convert("RGB", "U8")
                    img = 255 - img
                    img = img - 255 * (img * (1 / 255)) # normalized
                    img = img.convert("RGB", "U8")
                elif self.formCmb.currentText() == "Grayscale 16-bit":
                    img = img.convert("RGB", "U16")
                    img = 65535 - img
                    img = img - 65535 * (img * (1 / 65535)) # normalized
                    img = img.convert("RGB", "U16")
            else:
                img = depth * scale

            camera_name = self.safe_path_name(camera.label, "Camera")
            output_path = self.unique_path(os.path.join(chunk_folder, camera_name + ".tif"))
            img.save(output_path)
            print("Processed depth for {}/{}".format(chunk.label, camera.label))
            count += 1
            self.pBar.setValue(int(count / len(export_items) * 100))
            app.processEvents()

        self.pBar.setValue(100)
        print("Script finished. Total cameras processed: " + str(count))
        print("Depth maps exported to:\n " + output_folder)
        return 1 
 
 
def export_depth_maps():
    app = QtWidgets.QApplication.instance()
    parent = app.activeWindow()
 
    dlg = ExportDepthDlg(parent)
 
 
label = "Scripts/Export Depth Maps All Chunks"
Metashape.app.addMenuItem(label, export_depth_maps)
print("To execute this script press {}".format(label))

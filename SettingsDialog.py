from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QListWidget, QHBoxLayout, QFileDialog

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.audio_library_paths_list = QListWidget()
        self.layout.addWidget(self.audio_library_paths_list)

        self.add_button = QPushButton("Add Path")
        self.add_button.clicked.connect(self.add_path)
        self.layout.addWidget(self.add_button)

        self.remove_button = QPushButton("Remove Selected Path")
        self.remove_button.clicked.connect(self.remove_selected_path)
        self.layout.addWidget(self.remove_button)

        self.import_button = QPushButton("Import Settings")
        self.import_button.clicked.connect(parent.import_settings)
        self.layout.addWidget(self.import_button)

        self.export_button = QPushButton("Export Settings")
        self.export_button.clicked.connect(parent.export_settings)
        self.layout.addWidget(self.export_button)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.accept)
        self.layout.addWidget(self.save_button)

        self.load_paths()

    def load_paths(self):
        self.audio_library_paths_list.clear()
        for path in self.parent().audio_library_paths:
            self.audio_library_paths_list.addItem(path)

    def add_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            self.audio_library_paths_list.addItem(path)

    def remove_selected_path(self):
        for item in self.audio_library_paths_list.selectedItems():
            self.audio_library_paths_list.takeItem(self.audio_library_paths_list.row(item))
import argparse, os, sys, json, threading, requests
from backend.assistant import Message, AssistantResponse, Role
from typing import List
import genesis as gs
from PySide6 import QtCore, QtGui, QtWidgets
from .controllers import GenesisRunner, LLMClient

class ChatList(QtWidgets.QListWidget):
    def __init__(self, bubble_hpad: int = 8, bubble_vpad: int = 8, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setUniformItemSizes(False)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self._bubble_hpad = bubble_hpad
        self._bubble_vpad = bubble_vpad

    def _compute_bubble_height(self, edit: QtWidgets.QTextEdit, max_width: int) -> int:
        # account for padding in stylesheet
        text_width = max(20, max_width - 2 * self._bubble_hpad)
        doc: QtGui.QTextDocument = edit.document()
        doc.setTextWidth(text_width)
        h = int(doc.size().height()) + 2 * self._bubble_vpad
        return max(h, 40)
    
    def add_bubble(self, text: str, me: bool):
        item = QtWidgets.QListWidgetItem()
        bubble = QtWidgets.QTextEdit()
        bubble.setReadOnly(True)
        bubble.setText(text)
        bubble.setMinimumHeight(40)
        bubble.setFrameShape(QtWidgets.QFrame.NoFrame)
        bubble.setWordWrapMode(QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere)
        if me:
            bubble.setStyleSheet("QTextEdit { background: #e8f5e9; border-radius: 10px; padding: 8px; }")
        else:
            bubble.setStyleSheet("QTextEdit { background: #e3f2fd; border-radius: 10px; padding: 8px; }")
        maxw = int(self.viewport().width() * 0.66)
        bubble.setMaximumWidth(maxw)
        bubble.setMinimumWidth(min(180, maxw))
        bubble.setFixedHeight(self._compute_bubble_height(bubble, maxw))
        
        row = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(row)
        lay.setContentsMargins(6, 2, 6, 2)
        lay.setSpacing(6)
        
        if me:
            lay.addStretch(1)
            lay.addWidget(bubble, 0, QtCore.Qt.AlignRight)
        else:
            lay.addWidget(bubble, 0, QtCore.Qt.AlignLeft)
            lay.addStretch(1)
        
        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(row.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, row)
        self.scrollToBottom()

class MainWindow(QtWidgets.QMainWindow):
    addBubble = QtCore.Signal(str, bool)
    showError = QtCore.Signal(str)
    updateConfig = QtCore.Signal(AssistantResponse)
    
    def __init__(self, args):
        super().__init__()
        self.setWindowTitle("Genesis + LLM GUI")
        self.resize(1200, 720)

        self.runner = GenesisRunner()

        self.llm = LLMClient(
            backend_url=args.backend,
            model=args.model,
            device=args.llm_device,
            max_tokens=args.max_tokens,
        )

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Horizontal)

        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)

        status_row = QtWidgets.QHBoxLayout()
        self.lbl_status = QtWidgets.QLabel()
        self.lbl_status.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Fixed
        )
        font = self.lbl_status.font()
        font.setPointSize(font.pointSize() + 1)
        self.lbl_status.setFont(font)

        status_row.addStretch(1)
        status_row.addWidget(self.lbl_status)
        status_row.addStretch(1)
        left_layout.addLayout(status_row)   # add first so it's on top
        sim_controls = QtWidgets.QHBoxLayout()
        self.btn_start = QtWidgets.QPushButton("Start Sim")
        self.btn_end = QtWidgets.QPushButton("End Sim")
        self.btn_stop = QtWidgets.QPushButton("Stop Sim")
        self.btn_stop.setEnabled(False)
        sim_controls.addWidget(self.btn_start)
        sim_controls.addWidget(self.btn_end)
        sim_controls.addWidget(self.btn_stop)
        sim_controls.addStretch(1)
        self.btn_start.clicked.connect(self._on_start)
        self.btn_end.clicked.connect(self._on_end)
        self.btn_stop.clicked.connect(self._on_stop)
        left_layout.addLayout(sim_controls)

        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)

        top_controls = QtWidgets.QHBoxLayout()
        self.ed_model = QtWidgets.QLineEdit(args.model)
        self.ed_device = QtWidgets.QLineEdit(args.llm_device)
        self.spn_tokens = QtWidgets.QSpinBox()
        self.spn_tokens.setRange(1, 51200)
        self.spn_tokens.setValue(args.max_tokens)
        self.btn_apply = QtWidgets.QPushButton("Apply Params")
        top_controls.addWidget(QtWidgets.QLabel("Model:"))
        top_controls.addWidget(self.ed_model)
        top_controls.addWidget(QtWidgets.QLabel("Device:"))
        top_controls.addWidget(self.ed_device)
        top_controls.addWidget(QtWidgets.QLabel("Max Tokens:"))
        top_controls.addWidget(self.spn_tokens)
        top_controls.addWidget(self.btn_apply)

        self.chat_list = ChatList()
        input_row = QtWidgets.QHBoxLayout()
        self.ed_input = QtWidgets.QLineEdit()
        self.ed_input.setPlaceholderText("Type a message for the LLM…")
        self.btn_send = QtWidgets.QPushButton("Send")
        input_row.addWidget(self.ed_input)
        input_row.addWidget(self.btn_send)

        right_layout.addLayout(top_controls)
        right_layout.addWidget(self.chat_list, stretch=1)
        right_layout.addLayout(input_row)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        self.setCentralWidget(splitter)

        self.btn_apply.clicked.connect(self._on_apply)
        self.btn_send.clicked.connect(self._on_send)
        self.ed_input.returnPressed.connect(self._on_send)
        self.addBubble.connect(self.chat_list.add_bubble)
        self.showError.connect(lambda msg: self._set_status(f"Error: {msg}"))
        self.updateConfig.connect(self._on_update)
        self.runner.started.connect(lambda: self._set_status("Running"))
        self.runner.stopped.connect(lambda rc: self._set_status(f"Stopped (rc={rc})"))
        self.runner.errored.connect(lambda msg: self._set_status(f"Error: {msg}"))

        self.chat_list.add_bubble("Connected UI ready. Start the sim and chat with the model on the right.", me=False)

    def _set_status(self, s: str):
        self.lbl_status.setText(s)
        self.btn_start.setEnabled(not self.runner.is_running())
        self.btn_stop.setEnabled(self.runner.is_running())

    def _on_start(self):
        # Warn if capture dir not referenced in config
        # We don't parse the config here; we rely on user's config to have capture.dir set to args.capture.
        self.runner.start()
        self._set_status("Starting…")
        
    def _on_end(self):
        self.runner.end()
        self._set_status("Ending…")

    def _on_stop(self):
        self.runner.stop()
        self._set_status("Stopping…")

    def _on_apply(self):
        self.llm.set_params(
            model=self.ed_model.text().strip() or "Qwen/Qwen2.5-1.5B-Instruct",
            device=self.ed_device.text().strip() or "auto",
            max_tokens=int(self.spn_tokens.value()),
        )
    
    def _on_update(self, resp: AssistantResponse):
        try:
            self.runner.update_config(resp.config.model_dump())
        except Exception as e:
            self.showError.emit(f"Failed to update config: {e}")

    def _on_send(self):
        text = self.ed_input.text().strip()
        if not text:
            return
        self.chat_list.add_bubble(text, me=True)
        self.ed_input.clear()
        
        def success_update(resp: AssistantResponse, me: bool):
            self.addBubble.emit(f"{resp.content}", me=False)
            cfg = resp.config
            self.updateConfig.emit(cfg)

        def worker():
            try:
                resp = self.llm.send(text)
                success_update(resp)
            except Exception as e:
                self.showError.emit(f"LLM request failed: {e}")
        threading.Thread(target=worker, daemon=True).start()

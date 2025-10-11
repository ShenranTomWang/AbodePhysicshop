import argparse
import os
import sys
import time
import json
import threading
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import List, Literal, Optional
import genesis as gs

import requests

from PySide6 import QtCore, QtGui, QtWidgets

# --------------------------- Data Models (数据模型) ---------------------------
Role = Literal["system", "user", "assistant"]

@dataclass
class Message:
    role: Role
    content: str

@dataclass
class AssistantResponse:
    role: Role
    content: str
    # chain_of_thought deliberately not surfaced in UI

class GenesisRunner(QtCore.QObject):
    """Run Genesis.

    Public API:
        - is_running() -> bool
        - start()
        - stop()
        - end()
        - update_config(cfg: dict)

    Signals:
        - started()
        - stopped(int_rc)
        - errored(str_msg)
    """
    started = QtCore.Signal()
    stopped = QtCore.Signal(int)
    errored = QtCore.Signal(str)

    def __init__(self):
        super().__init__()

        self.t = 0
        self._scene = None
        self._bodies = []
        self._statics = []
        self._step_thread = threading.Thread(target=self.step, daemon=True)
        self._running = False
        self.fps = fps

    def update_config(self, cfg: dict):
        self._scene = gs.Scene(
            sim_options=gs.options.SimOptions(**cfg["sim_options"]),
            mpm_options=gs.options.MPMOptions(**cfg["mpm_options"]),
            vis_options=gs.options.VisOptions(**cfg["vis_options"]),
            viewer_options=gs.options.ViewerOptions(**cfg["viewer_options"]),
            show_viewer=cfg["show_viewer"]
        )
        self._bodies = []
        for body in cfg["mpm_bodies"]:
            _body = self._scene.add_entity(
                material=body.material.to_genesis(),
                morph=body.morph.to_genesis(),
                surface=body.surface.to_genesis()
            )
            self._bodies.append(_body)
        for body in cfg["static_bodies"]:
            _static = self._scene.add_entity(
                material=body.material.to_genesis(),
                morph=body.morph.to_genesis(),
                surface=body.surface.to_genesis()
            )
            self._statics.append(_static)
    
    def is_running(self) -> bool:
        return self._running

    def start(self):
        if self._running:
            return
        self._running = True
        self.started.emit()
        if not self._step_thread.is_alive():
            self._step_thread = threading.Thread(target=self.step, daemon=True)
            self._step_thread.start()
            
    def stop(self):
        if not self._running:
            return
        self._running = False

    def end(self):
        if not self._running:
            return
        self._running = False
        if self._step_thread.is_alive():
            self._step_thread.join(timeout=5)
        self.stopped.emit(0)
    
    def step(self):
        try:
            if self._running:
                self._scene.step()
        except Exception as e:
            self.errored.emit(str(e))
            self._running = False
            self.stopped.emit(-1)

class LLMClient:
    def __init__(self, backend_url: str, model: str = "Qwen/Qwen2.5-1.5B-Instruct", device: str = "auto", max_tokens: int = 51200):
        self.backend_url = backend_url.rstrip("/")
        self.model = model
        self.device = device
        self.max_tokens = max_tokens
        self.history: List[Message] = []

    def set_params(self, model: str, device: str, max_tokens: int):
        self.model = model
        self.device = device
        self.max_tokens = max_tokens

    def send(self, user_text: str) -> AssistantResponse:
        self.history.append(Message(role="user", content=user_text))
        payload = {
            "model": self.model,
            "device": self.device,
            "max_tokens": self.max_tokens,
            "conversation_history": [m.__dict__ for m in self.history],
        }
        r = requests.post(self.backend_url + "/generate", json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "response" in data:
            resp = data["response"]
            role = resp.get("role", "assistant")
            content = resp.get("content", "")
            config = resp.get("config", {})
            cot = resp.get("chain_of_thought", "")
        else:
            role = data.get("role", "assistant")
            content = data.get("content", json.dumps(data))
        ar = AssistantResponse(role=role, content=content, config=config, chain_of_thought=cot)
        self.history.append(ar)
        return ar

class ChatList(QtWidgets.QListWidget):
    def add_bubble(self, text: str, me: bool):
        item = QtWidgets.QListWidgetItem()
        bubble = QtWidgets.QTextEdit()
        bubble.setReadOnly(True)
        bubble.setText(text)
        bubble.setMinimumHeight(40)
        bubble.setFrameShape(QtWidgets.QFrame.NoFrame)
        bubble.setWordWrapMode(QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere)
        # Simple alignment cue
        if me:
            bubble.setStyleSheet("QTextEdit { background: #e8f5e9; border-radius: 10px; padding: 8px; }")
        else:
            bubble.setStyleSheet("QTextEdit { background: #e3f2fd; border-radius: 10px; padding: 8px; }")
        item.setSizeHint(QtCore.QSize(100, bubble.document().size().toSize().height() + 24))
        self.addItem(item)
        self.setItemWidget(item, bubble)
        self.scrollToBottom()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.setWindowTitle("Genesis + LLM GUI")
        self.resize(1200, 720)

        self.runner = GenesisRunner()

        self.llm = LLMClient(
            backend_url=args.backend,
            model=args.model,
            device=args.device,
            max_tokens=args.max_tokens,
        )

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Horizontal)

        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)

        sim_controls = QtWidgets.QHBoxLayout()
        self.btn_start = QtWidgets.QPushButton("Start Sim")
        self.btn_end = QtWidgets.QPushButton("End Sim")
        self.btn_stop = QtWidgets.QPushButton("Stop Sim")
        self.btn_stop.setEnabled(False)
        self.lbl_status = QtWidgets.QLabel("Idle")
        sim_controls.addWidget(self.btn_start)
        sim_controls.addWidget(self.btn_end)
        sim_controls.addWidget(self.btn_stop)
        sim_controls.addStretch(1)
        sim_controls.addWidget(self.lbl_status)

        left_layout.addLayout(sim_controls)

        # Right: Chat (右侧聊天)
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)

        # Top controls (参数)
        top_controls = QtWidgets.QHBoxLayout()
        self.ed_model = QtWidgets.QLineEdit(args.model)
        self.btn_apply = QtWidgets.QPushButton("Apply Params")
        top_controls.addWidget(QtWidgets.QLabel("Model:"))
        top_controls.addWidget(self.ed_model)
        top_controls.addWidget(self.btn_apply)

        self.chat_list = ChatList()
        input_row = QtWidgets.QHBoxLayout()
        self.ed_input = QtWidgets.QLineEdit()
        self.ed_input.setPlaceholderText("Type a message for the LLM…")
        self.btn_send = QtWidgets.QPushButton("Send")
        input_row.addWidget(self.ed_input)
        input_row.addWidget(self.btn_send)

        right_layout.addLayout(top_controls)
        right_layout.addWidget(self.chat_list)
        right_layout.addLayout(input_row)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        self.setCentralWidget(splitter)

        # Signals (信号)
        self.btn_start.clicked.connect(self._on_start)
        self.btn_end.clicked.connect(self._on_end)
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_apply.clicked.connect(self._on_apply)
        self.btn_send.clicked.connect(self._on_send)
        self.ed_input.returnPressed.connect(self._on_send)

        # Runner signals
        self.runner.started.connect(lambda: self._set_status("Running"))
        self.runner.stopped.connect(lambda rc: self._set_status(f"Stopped (rc={rc})"))
        self.runner.errored.connect(lambda msg: self._set_status(f"Error: {msg}"))

        # Helpful tip in chat
        self.chat_list.add_bubble("Connected UI ready. Start the sim and chat with the model on the right.", me=False)

    # ---------------- UI Actions ----------------
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

    def _on_send(self):
        text = self.ed_input.text().strip()
        if not text:
            return
        self.chat_list.add_bubble(text, me=True)
        self.ed_input.clear()
        
        def success_update(resp: AssistantResponse, me: bool):
            self.chat_list.add_bubble(resp.content, me=me)
            cfg = resp.config
            self.runner.update_config(cfg)

        def worker():
            try:
                resp = self.llm.send(text)
                # Render assistant response
                self._post_to_ui(success_update)
            except Exception as e:
                self._post_to_ui(lambda: self.chat_list.add_bubble(f"[error] {e}", me=False))

        threading.Thread(target=worker, daemon=True).start()

    def _post_to_ui(self, fn):
        QtCore.QMetaObject.invokeMethod(self, lambda: fn(), QtCore.Qt.QueuedConnection)

# ------------------------------ CLI (命令行) ------------------------------

def parse_args():
    ap = argparse.ArgumentParser(description="Genesis + LLM Chat GUI")
    ap.add_argument("--backend", default="localhost:8000", help="FastAPI base URL without trailing slash")
    ap.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct", help="LLM model name")
    ap.add_argument("--device", default="auto", help="Device hint for LLM")
    ap.add_argument("--max_tokens", type=int, default=2048, help="Max tokens")
    return ap.parse_args()

def main():
    args = parse_args()

    backend = args.backend.rstrip("/")
    if backend.endswith("/generate"):
        backend = backend.rsplit("/", 1)[0]
    args.backend = backend

    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow(args)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

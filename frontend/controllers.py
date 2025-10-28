from PySide6 import QtCore
import threading, requests
import genesis as gs
from typing import List
from backend.assistant import Message, AssistantResponse, Role
from simulator.config import GenesisConfig
import traceback

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
        - ended(int_rc)
        - errored(str_msg)
    """
    started = QtCore.Signal()
    stopped = QtCore.Signal(int)
    ended = QtCore.Signal(int)
    errored = QtCore.Signal(str)

    def __init__(self, device: str = "cpu"):
        super().__init__()
        self.device = getattr(gs, device)
        gs.init(backend=self.device)
        self._scene = None
        self.cfg = None
        self._bodies = []
        self._statics = []
        self._step_thread = threading.Thread(target=self.step, daemon=True)
        self._running = False
    
    def to(self, device: str):
        if device == self.device:
            return
        self.device = device
        gs.init(device=self.device)
        if self._scene:
            self.update_config(self.cfg)

    def update_config(self, cfg: GenesisConfig):
        try:
            self.cfg = cfg
            self._scene = gs.Scene(
                sim_options=cfg.sim_options.to_genesis(),
                mpm_options=cfg.mpm_options.to_genesis(),
                vis_options=cfg.vis_options.to_genesis(),
                viewer_options=cfg.viewer_options.to_genesis(),
                show_viewer=cfg.show_viewer
            )
            self._bodies = []
            for body in cfg.mpm_bodies:
                _body = self._scene.add_entity(
                    material=body.material.to_genesis(),
                    morph=body.morph.to_genesis(),
                    surface=body.surface.to_genesis()
                )
                self._bodies.append(_body)
            for body in cfg.static:
                _static = self._scene.add_entity(
                    morph=body.morph.to_genesis(),
                    surface=body.surface.to_genesis()
                )
                self._statics.append(_static)
            self._scene.build()
        except Exception as e:
            traceback.print_exc()
            self.errored.emit(f"Failed to update config: {e}")
    
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
        if self._step_thread.is_alive():
            self._step_thread.join(timeout=5)
        self._scene.reset() if self._scene else None
        self.stopped.emit(0)

    def end(self):
        if not self._running:
            return
        self._running = False
        if self._step_thread.is_alive():
            self._step_thread.join(timeout=5)
        self._scene.reset() if self._scene else None
        self.ended.emit(0)
    
    def step(self):
        try:
            if self._running:
                self._scene.step()
        except Exception as e:
            self.errored.emit(str(e))
            self._running = False
            self.ended.emit(-1)

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
        payload = {
            "model": self.model,
            "device": self.device
        }
        resp = requests.put(self.backend_url + "/set_model", json=payload, timeout=10)
        resp.raise_for_status()
        resp = resp.json()
        if resp["status_code"] != 200:
            raise ValueError(f"Failed to set model parameters: {resp['text']}")

    def send(self, user_text: str) -> AssistantResponse:
        self.history.append(Message(role=Role.USER, content=user_text))
        payload = {
            "model": self.model,
            "device": self.device,
            "max_tokens": self.max_tokens,
            "conversation_history": [m.__dict__ for m in self.history],
        }
        resp = requests.post(self.backend_url + "/generate", json=payload, timeout=300)
        resp.raise_for_status()
        resp = resp.json()
        ar = AssistantResponse.model_validate_json(resp)
        self.history.append(ar)
        return ar
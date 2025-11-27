from PySide6 import QtCore
from PySide6.QtCore import Slot
import requests, json, openai, os
import genesis as gs
from typing import List
from backend.assistant import Message, AssistantResponse, Role
from simulator.config import GenesisConfig

def get_system_prompt() -> Message:
    return Message(
        role=Role.SYSTEM,
        content=f"""
            You are a helpful AI assistant that provides config for Genesis physics simulation structured in JSON format.
            The user may ask you to generate or modify the simulation config.
            You will provide a textual response or anything you want to ask the user in the "content" field, and a detailed "chain_of_thought" field for your reasoning.
            Finally, you will provide a "config" field containing the GenesisConfig JSON schema.
            Make assumptions about what the user wants, what objects should be static or dynamic, etc. You do not always need to make changes to the config; if the user is just chatting, you can keep the config the same.
            Your response schema will look like this:
            {json.dumps(AssistantResponse.model_json_schema(), indent=4)}
            Notice that there must be at least one MPM body in the config.
        """
    )

class GenesisRunner(QtCore.QObject):
    """Run Genesis.

    Public API:
        - start()
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
        self._running = False
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)   # runs in GUI thread
    
    def to(self, device: str):
        if device == self.device:
            return
        self.device = device
        gs.init(device=self.device)
        if self._scene:
            self.update_config(self.cfg)

    def update_config(self, cfg: GenesisConfig):
        if self._scene is not None:
            self._scene.reset()
            del self._scene
            self._scene = None
            self._bodies = []
            self._statics = []
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
        except Exception as e:
            self.errored.emit(f"Failed to update config: {e}")
    
    def is_running(self) -> bool:
        return self._running

    def start(self, fps=60):
        if self._running:
            return
        self._running = True
        if not self._scene.is_built:
            self._scene.build()
        self.started.emit()
        interval_ms = 0 if fps is None else max(0, int(1000 / fps))
        self._timer.start(interval_ms)
            
    def stop(self):
        if not self._running:
            return
        self._running = False
        self._timer.stop()
        self.stopped.emit(0)

    def end(self):
        if not self._running:
            return
        self._running = False
        self._timer.stop()
        self._scene.reset() if self._scene else None
        self.ended.emit(0)
    
    @Slot()
    def _tick(self):
        try:
            if not self._running:
                return
            self._scene.step()
        except Exception as e:
            self._running = False
            self._timer.stop()
            self.errored.emit(str(e))
            self.ended.emit(-1)

class LLMClient:
    def __init__(self, backend_url: str, model: str = "qwen-plus", device: str = "auto", max_tokens: int = 51200, use_API: bool = False):
        self.backend_url = backend_url.rstrip("/")
        self.model = model
        self.device = device
        self.max_tokens = max_tokens
        self.history: List[Message] = []
        self.client = openai.OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        )
        self.use_API = use_API

    def set_params(self, model: str, device: str, max_tokens: int):
        self.model = model
        self.device = device
        self.max_tokens = max_tokens
        if not self.use_API:
            payload = {
                "model": self.model,
                "device": self.device
            }
            resp = requests.put(self.backend_url + "/set_model", json=payload, timeout=10)
            resp.raise_for_status()
            body = resp.json()
            if body.get("status") != 200:
                raise ValueError(f"Failed to set model parameters: {body}")

    def send(self, user_text: str) -> AssistantResponse:
        if self.use_API:
            return self._send_API(user_text)
        else:
            return self._send_backend(user_text)
    
    def _send_backend(self, user_text: str) -> AssistantResponse:
        user_msg = Message(role=Role.USER, content=user_text)
        self.history.append(user_msg)
        payload = {
            "model": self.model,
            "device": self.device,
            "max_tokens": self.max_tokens,
            "conversation_history": [m.model_dump(mode="json") for m in self.history],
        }
        try:
            resp = requests.post(self.backend_url + "/generate", json=payload, timeout=300)
            resp.raise_for_status()
        except Exception:
            self.history.pop()  # keep history consistent if the call failed
            raise
        resp = resp.json()
        ar = AssistantResponse.model_validate_json(resp)
        self.history.append(ar)
        return ar
    
    def _send_API(self, user_text: str) -> AssistantResponse:
        user_msg = Message(role=Role.USER, content=user_text)
        self.history.append(user_msg)
        conversation_history = self.history.copy()
        if conversation_history[0].role != Role.SYSTEM:
            conversation_history = [get_system_prompt(), *self.history]
        payload = {
            "model": self.model,
            "messages": [m.model_dump(mode="json") for m in conversation_history],
            "response_format": {
                "type": "json_object"
            }
        }
        try:
            resp = self.client.chat.completions.create(
                **payload
            )
            resp = resp.choices[0].message.content
        except Exception:
            self.history.pop()  # keep history consistent if the call failed
            raise
        resp = json.loads(resp)
        ar = AssistantResponse.model_validate(resp)
        self.history.append(ar)
        return ar

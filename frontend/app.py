import sys, argparse
from PySide6 import QtWidgets
from .ui import MainWindow
import requests

def parse_args():
    ap = argparse.ArgumentParser(description="Genesis + LLM Chat GUI")
    ap.add_argument("--backend", default="http://localhost:8000", help="FastAPI base URL without trailing slash")
    ap.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct", help="LLM model name")
    ap.add_argument("--llm_device", default="auto", help="Device hint for LLM")
    ap.add_argument("--max_tokens", type=int, default=51200, help="Max tokens")
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
    win._on_apply()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
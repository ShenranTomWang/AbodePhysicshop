from subprocess import Popen
from threading import Thread

def run_backend():
    process = Popen(["uvicorn", "backend.app:app", "--host", "localhost", "--port", "8000", "--reload"])
    process.wait()

def run_frontend():
    process = Popen(["python", "-m", "frontend.app", "--use_api"])
    process.wait()

def main():
    thread_backend = Thread(target=run_backend)
    thread_frontend = Thread(target=run_frontend)
    thread_backend.start()
    thread_frontend.start()
    thread_frontend.join()

if __name__ == "__main__":
    main()

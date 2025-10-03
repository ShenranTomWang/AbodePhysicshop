from subprocess import Popen

def main():
    process = Popen(["uvicorn", "backend.app:app", "--port", "8000", "--reload"])
    process.wait()
    # TODO: start frontend here as well

if __name__ == "__main__":
    main()

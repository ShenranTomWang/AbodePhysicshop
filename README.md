# Abode Physicshop
## Setting Up
This project uses [uv](https://github.com/astral-sh/uv) to manage dependencies. Install it in your computer, then use
```shell
uv sync
```
to set up your environment. It should create a `.venv` folder in your repo. To activate this environment, use
```shell
source .venv/bin/activate
```
If you want to add another package to dependencies, use
```shell
uv add <package>
```
!!DO NOT USE PIP!!  
Similarly, to remove a package from the environment, use
```shell
uv remove <package>
```

## Architecture
This project consists of a [frontend](frontend) and a [backend](backend). The frontend is a GUI with a [GenesisRunner](frontend/controllers.py), and the backend is a LLM server that generates `.json` format responses using [outlines](https://github.com/dottxt-ai/outlines?tab=readme-ov-file).
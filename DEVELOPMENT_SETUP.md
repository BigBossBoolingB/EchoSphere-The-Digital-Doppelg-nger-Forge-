# EchoSphere Development Setup

This document provides instructions for setting up a local development environment for the EchoSphere project.

## Prerequisites

- Python 3.12 or later
- `pip` for package management
- `virtualenv` for creating isolated Python environments

## Setup Instructions

1.  **Clone the Repository**

    ```bash
    git clone [repository-url]
    cd echosystem
    ```

2.  **Create and Activate a Virtual Environment**

    It is highly recommended to use a virtual environment to manage project dependencies.

    ```bash
    # Create the virtual environment
    python3 -m venv .venv

    # Activate the virtual environment
    # On macOS and Linux:
    source .venv/bin/activate
    # On Windows:
    # .venv\Scripts\activate
    ```

3.  **Install Dependencies**

    All required Python packages are listed in the `requirements.txt` file.

    ```bash
    pip install -r requirements.txt
    ```

4.  **Compile Protobuf Definitions**

    The project uses Protocol Buffers for data contracts. If you make changes to the `.proto` files in the `proto/` directory, you must re-compile them.

    ```bash
    python -m grpc_tools.protoc -I./proto --python_out=. --pyi_out=. ./proto/persona.proto
    ```

## Running Quality Checks

### Code Formatting

This project uses `black` for code formatting. To format the entire codebase, run:

```bash
black .
```

### Linting

This project uses `ruff` for linting. to check for issues, run:

```bash
ruff check .
```

To automatically fix many common issues, run:

```bash
ruff check . --fix
```

## Running Tests

The project has a comprehensive test suite using `pytest`. To run all tests, execute the following command from the root of the repository:

```bash
PYTHONPATH=. pytest
```

The `PYTHONPATH=.` prefix is important as it allows `pytest` to correctly discover the application modules in the `echosystem/` directory.

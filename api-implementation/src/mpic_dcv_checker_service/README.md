# dcv

## Development

Instructions for developing the open-mpic dcv service.

### Getting Started

If using the devcontainer, you already have the required tools installed.

Note: app.conf has placeholder values. These must be updated before usage.

Run the following commands to get started:

```bash
# Install the python version specified in the .python-version file
pyenv install
# Activate the python version specified in the .python-version file
pyenv activate
# Install the dependencies
pip install -r requirements.txt
# Start the service
fastapi dev
```
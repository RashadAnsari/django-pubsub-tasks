{ pkgs ? import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/refs/tags/23.11.tar.gz") {} }:

pkgs.mkShell {
  name = "django-pubsub-tasks";
  buildInputs = [
    pkgs.python311
  ];

  shellHook = ''
    if [ -e .venv ]; then
      source .venv/bin/activate
    else
      python -m venv .venv
      source .venv/bin/activate
      pip3 install --upgrade pip
      pip3 install poetry==1.7.1
      poetry config virtualenvs.in-project true
      poetry env use .venv/bin/python
      poetry install
    fi
  '';
}

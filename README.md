# Albert Wi-Fi

Quickly search through and connect to your wifi networks.

### Install

To install, copy or symlink this directory to `~/.local/share/albert/python/plugins/albert_wifi/`

Or just run `git clone https://github.com/HarshNarayanJha/albert_wifi ~/.local/share/albert/python/plugins/albert_wifi/`

### Usage

Type the trigger (default `wifi`) to list all known networks. Select any item to connect/disconnect to that network.
Trigger followed by `list` or `ls` will list available networks. There is a bug right now that will duplicate any known network if connected through this list. Use the previous list to connect to know networks.

Typing the trigger followed by `scan` or `sc` will initiate a scan for available networks. Check again with `wifi ls`

### Development Setup

I use the Zed Editor (naturally). Python Developement includes `pyright` as `lsp` and `ruff` as `linter`.

Copy the `albert.pyi` file from `~/.local/share/albert/python/plugins/albert.pyi` to this directory for type definitions and completions!

### References

- The official VPN plugin - https://github.com/albertlauncher/python/blob/vpn/__init__.py

# Copyright (c) 2026 Harsh Narayan Jha

"""
This plugin allows you to quickly connect available wifi networks and interact with NetworkManager.

Type the trigger (default `wifi`) to list all known networks. Select any item to connect/disconnect to that network.
Trigger followed by `list` or `ls` will list available networks. There is a bug right now that will duplicate any known network if connected through this list. Use the previous list to connect to know networks.

Typing the trigger followed by `scan` or `sc` will initiate a scan for available networks. Check again with `wifi ls`

---
"""

import subprocess
from collections import namedtuple
from shutil import which
from typing import Generator, cast, override

from albert import (
    Action,
    GeneratorQueryHandler,
    Icon,
    Item,
    MatchConfig,
    Matcher,
    PluginInstance,
    QueryContext,
    StandardItem,
    runDetachedProcess,
)

md_iid = "5.0"
md_version = "3.0"
md_name = "Wi-Fi"
md_description = "Manage NetworkManager Wi-Fi Connections"
md_license = "MIT"
md_bin_dependencies = ["nmcli"]
md_url = "https://github.com/HarshNarayanJha/albert_wifi"
md_authors = ["@HarshNarayanJha"]
md_maintainers = ["@HarshNarayanJha"]


class Plugin(PluginInstance, GeneratorQueryHandler):
    WiFiConnection = namedtuple("WiFiConnection", ["name", "uuid", "type", "connected"])
    WiFiAP = namedtuple("WiFiAP", ["ssid", "signal", "security", "connected"])

    @override
    def __init__(self):
        PluginInstance.__init__(self)
        GeneratorQueryHandler.__init__(self)

        self.fuzzy: bool = False

        self._symbolic_icon: bool
        if (symbolic_icon := self.readConfig("symbolic_icon", bool)) is None:
            self._symbolic_icon = True
        else:
            self._symbolic_icon = cast(bool, symbolic_icon)

        if which("nmcli") is None:
            raise Exception("'nmcli' not in $PATH, you sure you are running NetworkManager?")

    @override
    def supportsFuzzyMatching(self):
        return True

    @override
    def setFuzzyMatching(self, enabled: bool):
        self.fuzzy = enabled

    @override
    def synopsis(self, query):
        return "<network name>"

    @override
    def defaultTrigger(self):
        return "wifi "

    def makeIcon(self):
        # return Icon.theme("network-wireless-symbolic" if self._symbolic_icon else "network-wireless")
        return Icon.grapheme("🛜")

    def getWifiConnections(self) -> list[WiFiConnection]:
        connections = []

        output = subprocess.check_output("nmcli -t connection show", shell=True, encoding="UTF-8")

        for conn in output.splitlines():
            name, uuid, type, dev = conn.split(":")
            if type in ["802-11-wireless"]:
                connected = dev != ""
                connections.append(self.WiFiConnection(name=name, uuid=uuid, type="wifi", connected=connected))

        return connections

    def getAPs(self) -> list[WiFiAP]:
        aps = []

        output = subprocess.check_output("nmcli -t device wifi list", shell=True, encoding="UTF-8")

        for ap in output.splitlines():
            inuse, bssid, _, _, _, signal, bars, security = ap.split(":")[:1] + ap.rsplit(":", 7)[1:]
            connected = inuse == "*"
            aps.append(
                self.WiFiAP(
                    ssid=bssid,
                    signal=bars,
                    security=security,
                    connected=connected,
                )
            )

        return aps

    @staticmethod
    def scanConnections() -> None:
        runDetachedProcess(["nmcli", "device", "wifi", "rescan"])

    @override
    def items(self, context: QueryContext) -> Generator[list[Item]]:
        if not context.isValid:
            return

        m = Matcher(context.query, MatchConfig(fuzzy=self.fuzzy))
        items: list[Item] = []

        if context.query.startswith(("list", "ls")):
            aps = self.getAPs()
            m = Matcher(
                context.query.removeprefix("list").removeprefix("ls").removeprefix(" "),
                MatchConfig(fuzzy=self.fuzzy),
            )

            aps = [ap for ap in aps if m.match(ap.ssid)]

            items = [self._build_ap_item(ap) for ap in aps]

        elif context.query.startswith(("scan", "sc")):
            self.scanConnections()

            items = [
                StandardItem(
                    id="wifi-scan",
                    text="Scanning for Access Points",
                    subtext="Scanning initiated. Do `wifi ls` again for updated list",
                    icon_factory=lambda: self.makeIcon(),
                )
            ]

        else:
            connections = self.getWifiConnections()
            connections = [con for con in connections if m.match(con.name)]

            items = [self._build_connection_item(con) for con in connections]

        yield items

    def _build_connection_item(self, con: WiFiConnection) -> Item:
        name = con.name
        command = "down" if con.connected else "up"
        text = f"Connect to {name}" if command == "up" else f"Disconnect from {name}"
        commandline = ["nmcli", "connection", command, name]

        return StandardItem(
            id=f"wifi-{command}-{con.uuid}",
            text=("º " if con.connected else "") + name,
            subtext=text,
            icon_factory=lambda: self.makeIcon(),
            input_action_text=name,
            actions=[
                Action("run", text=text, callable=lambda: runDetachedProcess(commandline)),
                Action("scan", text="Scan APs", callable=lambda: Plugin.scanConnections()),
            ],
        )

    def _build_ap_item(self, con: WiFiAP) -> Item:
        name = con.ssid
        text = f"Connect to {name}" if not con.connected else f"Disconnect from {name}"
        text += f" | {con.security} | {con.signal}"

        if not con.connected:
            commandline = ["nmcli", "device", "wifi", "connect", con.ssid]
        else:
            commandline = ["nmcli", "connection", "down", con.ssid]

        return StandardItem(
            id=f"wifi-{not con.connected}-{con.ssid}",
            text=("º " if con.connected else "") + name,
            subtext=text,
            icon_factory=lambda: self.makeIcon(),
            input_action_text=name,
            actions=[
                Action("run", text=text, callable=lambda: runDetachedProcess(commandline)),
                Action("scan", text="Scan APs", callable=lambda: Plugin.scanConnections()),
            ],
        )

    @property
    def symbolic_icon(self) -> bool:
        return self._symbolic_icon

    @symbolic_icon.setter
    def symbolic_icon(self, value: bool) -> None:
        self._symbolic_icon = value
        self.writeConfig("symbolic_icon", value)

    @override
    def configWidget(self):
        return [
            {"type": "label", "text": str(__doc__).strip(), "widget_properties": {"textFormat": "Qt::MarkdownText"}},
            {"type": "checkbox", "property": "symbolic_icon", "label": "Use symbolic icon for wifi", "default": False},
        ]

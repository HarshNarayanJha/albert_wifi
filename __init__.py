# Copyright (c) 2024 Harsh Narayan Jha

"""
This plugin allows you to quickly connect available wifi networks and interact with NetworkManager
"""

import subprocess
from collections import namedtuple
from shutil import which
from typing import Any, List

from albert import (  # type: ignore
    Action,
    Item,
    Matcher,
    PluginInstance,
    Query,
    StandardItem,
    TriggerQueryHandler,
    runDetachedProcess,
)

md_iid = "3.0"
md_version = "1.0"
md_name = "Wi-Fi"
md_description = "Manage NetworkManager Wi-Fi Connections"
md_license = "MIT"
md_bin_dependencies = ["nmcli"]
md_url = "https://github.com/HarshNarayanJha/albert_wifi"
md_authors = ["@HarshNarayanJha"]


class Plugin(PluginInstance, TriggerQueryHandler):
    WiFiConnection = namedtuple("WiFiConnection", ["name", "uuid", "type", "connected"])
    WiFiAP = namedtuple("WiFiAP", ["ssid", "signal", "security", "connected"])

    def __init__(self):
        PluginInstance.__init__(self)
        TriggerQueryHandler.__init__(self)

        if which("nmcli") is None:
            raise Exception("'nmcli' not in $PATH, you sure you are running NetworkManager?")

    def synopsis(self, query):
        return "<network name>"

    def defaultTrigger(self):
        return "wifi "

    def getWifiConnections(self) -> List[WiFiConnection]:
        connections = []

        Plugin.scanConnections()

        output = subprocess.check_output("nmcli -t connection show", shell=True, encoding="UTF-8")

        for conn in output.splitlines():
            name, uuid, type, dev = conn.split(":")
            if type in ["802-11-wireless"]:
                connected = dev != ""
                connections.append(self.WiFiConnection(name=name, uuid=uuid, type="wifi", connected=connected))

        return connections

    def getAPs(self) -> List[WiFiAP]:
        aps = []

        Plugin.scanConnections()

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

    def handleTriggerQuery(self, query: Query):
        if query.isValid:
            m = Matcher(query.string)

            if query.string.startswith(("list", "ls")):
                aps = self.getAPs()
                m = Matcher(query.string.removeprefix("list").removeprefix("ls").removeprefix(" "))

                aps = [ap for ap in aps if m.match(ap.ssid)]
                query.add([self._build_ap_item(ap) for ap in aps])

            elif query.string in ("scan", "sc"):
                self.scanConnections()
                query.add(
                    [
                        StandardItem(
                            id="wifi-scan",
                            text="Scanning for Access Points",
                            subtext="Scanning initiated. Do `wifi ls` again for updated list",
                            iconUrls=["xdg:network-wireless"],
                        )
                    ]
                )

            else:
                connections = self.getWifiConnections()
                connections = [con for con in connections if m.match(con.name)]

                query.add([self._build_connection_item(con) for con in connections])

    @staticmethod
    def _build_connection_item(con: WiFiConnection) -> Item:
        name = con.name
        command = "down" if con.connected else "up"
        text = f"Connect to {name}" if command == "up" else f"Disconnect from {name}"
        commandline = ["nmcli", "connection", command, name]

        return StandardItem(
            id=f"wifi-{command}-{con.uuid}",
            text=("º " if con.connected else "") + name,
            subtext=text,
            iconUrls=["xdg:network-wireless"],
            inputActionText=name,
            actions=[
                Action("run", text=text, callable=lambda: runDetachedProcess(commandline)),
                Action("scan", text="Scan APs", callable=lambda: Plugin.scanConnections()),
            ],
        )

    @staticmethod
    def _build_ap_item(con: WiFiAP) -> Item:
        name = con.ssid
        command = "disconnect" if con.connected else "connect"
        text = (
            f"Connect to {name}" if command == "connect" else f"Disconnect from {name}"
        )
        # text += f" - {con.security}"

        commandline = ["nmcli", "device", "wifi", command, con.ssid]

        return StandardItem(
            id=f"wifi-{command}-{con.ssid}",
            text=("º " if con.connected else "") + name,
            subtext=text,
            iconUrls=["xdg:network-wireless"],
            inputActionText=name,
            actions=[
                Action("run", text=text, callable=lambda: runDetachedProcess(commandline)),
                Action("scan", text="Scan APs", callable=lambda: Plugin.scanConnections()),
            ],
        )

    def configWidget(self):
        return [
            {
                "type": "label",
                "text": str(__doc__).strip(),
                "widget_properties": {"textFormat": "Qt::MarkdownText"},
            }
        ]

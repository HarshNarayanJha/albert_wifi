# Copyright (c) 2024 Harsh Narayan Jha

"""
This plugin allows you to quickly connect available wifi networks and interact with NetworkManager
"""

from collections import namedtuple
from shutil import which
import subprocess

from typing import List

from albert import (  # type: ignore
    Action,
    Item,
    Matcher,
    Query,
    StandardItem,
    PluginInstance,
    TriggerQueryHandler,
    runDetachedProcess,
)

md_iid = "2.3"
md_version = "0.1"
md_name = "Wi-Fi"
md_description = "Manage NetworkManager Wi-Fi Connections"
md_license = "MIT"
md_url = "https://github.com/HarshNarayanJha/albert_wifi"
md_authors = ["@HarshNarayanJha"]


class Plugin(PluginInstance, TriggerQueryHandler):
    WiFiConnection = namedtuple("WiFiConnection", ["name", "uuid", "type", "connected"])
    WiFiAP = namedtuple("WiFiAP", ["bssid", "signal", "security", "connected"])

    def __init__(self):
        PluginInstance.__init__(self)
        TriggerQueryHandler.__init__(
            self, self.id, self.name, self.description, defaultTrigger="wifi "
        )

        if which("nmcli") is None:
            raise Exception(
                "'nmcli' not in $PATH, you sure you are running NetworkManager?"
            )

    def getWifiConnections(self) -> List[WiFiConnection]:
        connections = []

        output = subprocess.check_output(
            "nmcli -t connection show", shell=True, encoding="UTF-8"
        )

        for conn in output.splitlines():
            name, uuid, type, dev = conn.split(":")
            if type in ["802-11-wireless"]:
                connected = dev != ""
                connections.append(
                    self.WiFiConnection(
                        name=name, uuid=uuid, type="wifi", connected=connected
                    )
                )

        return connections

    def getAPs(self) -> List[WiFiAP]:
        aps = []

        output = subprocess.check_output(
            "nmcli -t device wifi list", shell=True, encoding="UTF-8"
        )

        for ap in output.splitlines():
            inuse, bssid, _, _, _, signal, bars, security = (
                ap.split(":")[:1] + ap.rsplit(":", 7)[1:]
            )
            connected = inuse == "*"
            aps.append(
                self.WiFiAP(
                    bssid=bssid,
                    signal=bars,
                    security=security,
                    connected=connected,
                )
            )

        return aps

    def scanConnections(self) -> None:
        runDetachedProcess(["nmcli", "device", "wifi", "rescan"])

    def handleTriggerQuery(self, query: Query):
        if query.isValid:
            m = Matcher(query.string)

            if query.string.startswith(("list", "ls")):
                aps = self.getAPs()
                m = Matcher(query.string.removeprefix("list").removeprefix("ls"))

                aps = [ap for ap in aps if m.match(ap.bssid)]

                query.add([self._build_ap_item(ap) for ap in aps])

            elif query.string in ("scan", "sc"):
                self.scanConnections()

            else:
                connections = self.getWifiConnections()
                connections = [con for con in connections if m.match(con.name)]

                query.add([self._build_connection_item(con) for con in connections])

    @staticmethod
    def _build_connection_item(con: WiFiConnection) -> Item:
        name = con.name
        command = "down" if con.connected else "up"
        text = f"Connect to {name}" if command == "up" else f"Disconnect from {name}"
        commandline = ["nmcli", "connection", command, con.uuid]

        return StandardItem(
            id=f"wifi-{command}-{con.uuid}",
            text=name,
            subtext=text,
            iconUrls=["xdg:network-wireless"],
            inputActionText=name,
            actions=[
                Action(
                    "run", text=text, callable=lambda: runDetachedProcess(commandline)
                )
            ],
        )

    @staticmethod
    def _build_ap_item(con: WiFiAP) -> Item:
        name = con.bssid
        command = "disconnect" if con.connected else "connect"
        text = (
            f"Connect to {name}" if command == "connect" else f"Disconnect from {name}"
        )
        text += f" {con.signal} {con.security}"

        commandline = ["nmcli", "device", command, con.bssid]

        return StandardItem(
            id=f"wifi-{command}-{con.bssid}",
            text=name,
            subtext=text,
            iconUrls=["xdg:network-wireless"],
            inputActionText=name,
            actions=[
                Action(
                    "run", text=text, callable=lambda: runDetachedProcess(commandline)
                )
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

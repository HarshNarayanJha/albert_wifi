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
                print(conn)
                connections.append(
                    self.WiFiConnection(
                        name=name, uuid=uuid, type="wifi", connected=connected
                    )
                )

        return connections

    def handleTriggerQuery(self, query: Query):
        if query.isValid:
            connections = self.getWifiConnections()
            m = Matcher(query.string)

            connections = [con for con in connections if m.match(con.name)]
            query.add([self._build_item(con) for con in connections])

    @staticmethod
    def _build_item(con: WiFiConnection) -> Item:
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

    def configWidget(self):
        return [
            {
                "type": "label",
                "text": str(__doc__).strip(),
                "widget_properties": {"textFormat": "Qt::MarkdownText"},
            }
        ]

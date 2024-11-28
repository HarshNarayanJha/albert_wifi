# Copyright (c) 2024 Harsh Narayan Jha

"""
This plugin allows you to quickly connect available wifi networks on linux and macOS
"""

import sys
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
md_description = "Manage NetworkManager and Airport utility Wi-Fi Connections"
md_license = "MIT"
md_url = "https://github.com/HarshNarayanJha/albert_wifi"
md_authors = ["@HarshNarayanJha"]


class WifiPlatform:
    def __init__(self) -> None:
        self.platform = sys.platform
        self.command = ""
        self.command_not_found_message = ""
        self.get_wifi_command = ""
        self.get_ap_command = ""

        match self.platform:
            case "linux":
                self.command = "nmcli"
                self.command_not_found_message = (
                    "'nmcli' not in $PATH, you sure you are running NetworkManager?"
                )
                self.get_wifi_command = f"{self.command} -t connection show"
                self.get_ap_command = f"{self.command} -t device wifi list"
            case "darwin":
                self.command = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/A/Resources/airport"
                self.command_not_found_message = (
                    "'airport' not in found at '/System/Library/PrivateFrameworks/Apple80211.framework/Versions/A/Resources/airport',\
                    you sure you are running macOS?, Well, you are though..."
                )
                self.get_wifi_command = f"{self.command} -I"
                self.get_ap_command = f"{self.command} -s"
            case _:
                raise NotImplementedError(
                    f"Plugin not implemented for platform: {self.platform}"
                )


class Plugin(PluginInstance, TriggerQueryHandler):
    WiFiConnection = namedtuple("WiFiConnection", ["name", "uuid", "type", "connected"])
    WiFiAP = namedtuple("WiFiAP", ["ssid", "signal", "security", "connected"])

    def __init__(self):
        PluginInstance.__init__(self)
        TriggerQueryHandler.__init__(
            self, self.id, self.name, self.description, defaultTrigger="wifi "
        )

        self.wifi_platform = WifiPlatform()

        if which(self.wifi_platform.command) is None:
            raise Exception(self.wifi_platform.command_not_found_message)

    def getWifiConnections(self) -> List[WiFiConnection]:
        connections = []

        output = subprocess.check_output(
            self.wifi_platform.get_wifi_command, shell=True, encoding="UTF-8"
        )

        if self.wifi_platform.platform == "linux":
            for conn in output.splitlines():
                name, uuid, type, dev = conn.split(":")
                if type in ["802-11-wireless"]:
                    connected = dev != ""
                    connections.append(
                        self.WiFiConnection(
                            name=name, uuid=uuid, type="wifi", connected=connected
                        )
                    )

        elif self.wifi_platform.platform == "darwin":
            for line in output.splitlines():
                if " SSID: " in line:
                    name = line.split(": ")[1]
                    connections.append(
                        self.WiFiConnection(
                            name=name,
                            uuid=name,
                            type="wifi",
                            connected=True,
                        )
                    )

        return connections

    def getAPs(self) -> List[WiFiAP]:
        aps = []

        output = subprocess.check_output(
            self.wifi_platform.get_ap_command, shell=True, encoding="UTF-8"
        )

        if self.wifi_platform.platform == "linux":
            for ap in output.splitlines():
                inuse, bssid, _, _, _, signal, bars, security = (
                    ap.split(":")[:1] + ap.rsplit(":", 7)[1:]
                )
                connected = inuse == "*"
                aps.append(
                    self.WiFiAP(
                        ssid=bssid,
                        signal=bars,
                        security=security,
                        connected=connected,
                    )
                )

        elif self.wifi_platform.platform == "darwin":
            for line in output.splitlines()[1:]:
                fields = line.split()
                if len(fields) >= 5:
                    ssid = fields[0]
                    signal = fields[2]
                    security = fields[6] if len(fields) > 6 else "NONE"
                    connected = False  # Need to check against current connection
                    aps.append(
                        self.WiFiAP(
                            ssid=ssid,
                            signal=signal,
                            security=security,
                            connected=connected,
                        )
                    )

        return aps

    @staticmethod
    def scanConnections() -> None:
        if sys.platform == "linux":
            runDetachedProcess(["nmcli", "device", "wifi", "rescan"])
        elif sys.platform == "darwin":
            runDetachedProcess(
                [
                    "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport",
                    "-s",
                ]
            )

    def handleTriggerQuery(self, query: Query):
        if query.isValid:
            m = Matcher(query.string)

            if query.string.startswith(("list", "ls")):
                aps = self.getAPs()
                m = Matcher(
                    query.string.removeprefix("list")
                    .removeprefix("ls")
                    .removeprefix(" ")
                )

                aps = [ap for ap in aps if m.match(ap.ssid)]
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

        if sys.platform == "linux":
            commandline = ["nmcli", "connection", command, name]
        elif sys.platform == "darwin":
            networksetup_path = "/usr/sbin/networksetup"
            if command == "up":
                commandline = [networksetup_path, "-setairportpower", "en0", "on"]
                commandline.extend(
                    [networksetup_path, "-setairportnetwork", "en0", name]
                )
            else:
                commandline = [networksetup_path, "-setairportpower", "en0", "off"]

        return StandardItem(
            id=f"wifi-{command}-{con.uuid}",
            text=("º " if con.connected else "") + name,
            subtext=text,
            iconUrls=["xdg:network-wireless"],
            inputActionText=name,
            actions=[
                Action(
                    "run", text=text, callable=lambda: runDetachedProcess(commandline)
                ),
                Action(
                    "scan", text="Scan APs", callable=lambda: Plugin.scanConnections()
                ),
            ],
        )

    @staticmethod
    def _build_ap_item(con: WiFiAP) -> Item:
        name = con.ssid
        command = "disconnect" if con.connected else "connect"
        text = (
            f"Connect to {name}" if command == "connect" else f"Disconnect from {name}"
        )

        if sys.platform == "linux":
            commandline = ["nmcli", "device", "wifi", command, con.ssid]
        elif sys.platform == "darwin":
            networksetup_path = "/usr/sbin/networksetup"
            if command == "connect":
                commandline = [networksetup_path, "-setairportpower", "en0", "on"]
                commandline.extend(
                    [networksetup_path, "-setairportnetwork", "en0", name]
                )
            else:
                commandline = [networksetup_path, "-setairportpower", "en0", "off"]

        return StandardItem(
            id=f"wifi-{command}-{con.ssid}",
            text=("º " if con.connected else "") + name,
            subtext=text,
            iconUrls=["xdg:network-wireless"],
            inputActionText=name,
            actions=[
                Action(
                    "run", text=text, callable=lambda: runDetachedProcess(commandline)
                ),
                Action(
                    "scan", text="Scan APs", callable=lambda: Plugin.scanConnections()
                ),
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

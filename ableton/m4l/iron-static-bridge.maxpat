{
  "patcher": {
    "fileversion": 1,
    "appversion": {
      "major": 8,
      "minor": 6,
      "revision": 2,
      "architecture": "x64",
      "modernui": 1
    },
    "rect": [0.0, 0.0, 640.0, 280.0],
    "bglocked": 0,
    "openinpresentation": 1,
    "default_fontsize": 12.0,
    "default_fontface": 0,
    "default_fontname": "Arial",
    "gridonopen": 1,
    "gridsize": [15.0, 15.0],
    "gridsnaponopen": 1,
    "objectsnaprange": 25.0,
    "magnetictoedge": 0,
    "subpatcher_template": "",
    "assistshowspatchername": 0,
    "classnamespace": "box",
    "boxes": [
      {
        "box": {
          "id": "obj-init",
          "maxclass": "newobj",
          "text": "live.thisdevice",
          "numinlets": 0,
          "numoutlets": 2,
          "outlettype": ["bang", "bang"],
          "patching_rect": [30.0, 30.0, 110.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-defer",
          "maxclass": "newobj",
          "text": "deferlow",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [30.0, 65.0, 70.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-js",
          "maxclass": "newobj",
          "text": "js ironstaticbridge.js",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["", ""],
          "patching_rect": [30.0, 150.0, 175.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-udp-rx",
          "maxclass": "newobj",
          "text": "udpreceive 7400",
          "numinlets": 0,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [230.0, 65.0, 130.0, 22.0],
          "presentation": 0,
          "hint": "Receives OSC commands from Python scripts"
        }
      },
      {
        "box": {
          "id": "obj-udp-tx",
          "maxclass": "newobj",
          "text": "udpsend 127.0.0.1 7401",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [30.0, 195.0, 180.0, 22.0],
          "presentation": 0,
          "hint": "Sends OSC responses back to Python scripts"
        }
      },
      {
        "box": {
          "id": "obj-print",
          "maxclass": "newobj",
          "text": "print iron-static-bridge",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [230.0, 195.0, 185.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-plugin-in",
          "maxclass": "newobj",
          "text": "plugin~",
          "numinlets": 0,
          "numoutlets": 2,
          "outlettype": ["signal", "signal"],
          "patching_rect": [460.0, 195.0, 55.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-plugin-out",
          "maxclass": "newobj",
          "text": "plugout~",
          "numinlets": 2,
          "numoutlets": 0,
          "patching_rect": [460.0, 235.0, 60.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-title",
          "maxclass": "comment",
          "text": "IRON STATIC\niron-static-bridge",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [400.0, 25.0, 210.0, 40.0],
          "presentation": 1,
          "presentation_rect": [10.0, 8.0, 210.0, 40.0],
          "fontsize": 13.0,
          "fontface": 1,
          "textcolor": [0.8, 0.3, 0.1, 1.0]
        }
      },
      {
        "box": {
          "id": "obj-ports",
          "maxclass": "comment",
          "text": "rx :7400  →  tx :7401",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [400.0, 70.0, 200.0, 20.0],
          "presentation": 1,
          "presentation_rect": [10.0, 50.0, 200.0, 20.0],
          "fontsize": 11.0,
          "textcolor": [0.4, 0.8, 0.4, 1.0]
        }
      },
      {
        "box": {
          "id": "obj-cmd-label",
          "maxclass": "comment",
          "text": "Commands:  /ping  /transport/play|stop|tempo  /scene/fire  /clip/create|clear|write|append  /reporter/dump",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [400.0, 100.0, 580.0, 20.0],
          "presentation": 1,
          "presentation_rect": [10.0, 72.0, 580.0, 20.0],
          "fontsize": 9.0,
          "textcolor": [0.5, 0.5, 0.5, 1.0]
        }
      }
    ],
    "lines": [
      {
        "patchline": {
          "source": ["obj-init", 0],
          "destination": ["obj-defer", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-defer", 0],
          "destination": ["obj-js", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-udp-rx", 0],
          "destination": ["obj-js", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-js", 0],
          "destination": ["obj-udp-tx", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-js", 1],
          "destination": ["obj-print", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-plugin-in", 0],
          "destination": ["obj-plugin-out", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-plugin-in", 1],
          "destination": ["obj-plugin-out", 1]
        }
      }
    ]
  }
}

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
    "rect": [0.0, 0.0, 680.0, 340.0],
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
          "text": "js pattern_injector.js",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["", ""],
          "patching_rect": [30.0, 100.0, 175.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-inject-btn",
          "maxclass": "button",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": ["bang"],
          "patching_rect": [30.0, 185.0, 40.0, 40.0],
          "presentation": 1,
          "presentation_rect": [15.0, 90.0, 40.0, 40.0],
          "bgcolor": [0.8, 0.2, 0.1, 1.0]
        }
      },
      {
        "box": {
          "id": "obj-inject-label",
          "maxclass": "comment",
          "text": "INJECT",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [80.0, 197.0, 60.0, 20.0],
          "presentation": 1,
          "presentation_rect": [60.0, 100.0, 60.0, 20.0],
          "fontsize": 11.0,
          "fontface": 1
        }
      },
      {
        "box": {
          "id": "obj-status-label",
          "maxclass": "newobj",
          "text": "print pattern-injector",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [230.0, 100.0, 185.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-err-label",
          "maxclass": "newobj",
          "text": "print pattern-injector-err",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [230.0, 130.0, 200.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-status-display",
          "maxclass": "comment",
          "text": "— status —",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [430.0, 120.0, 220.0, 20.0],
          "presentation": 1,
          "presentation_rect": [15.0, 145.0, 330.0, 20.0],
          "fontsize": 10.0,
          "textcolor": [0.4, 0.9, 0.4, 1.0]
        }
      },
      {
        "box": {
          "id": "obj-title",
          "maxclass": "comment",
          "text": "IRON STATIC\npattern-injector",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [400.0, 25.0, 230.0, 40.0],
          "presentation": 1,
          "presentation_rect": [10.0, 8.0, 230.0, 40.0],
          "fontsize": 13.0,
          "fontface": 1,
          "textcolor": [0.8, 0.3, 0.1, 1.0]
        }
      },
      {
        "box": {
          "id": "obj-subtitle",
          "maxclass": "comment",
          "text": "Send:  set_profile <path>   set_target <track> <slot>   set_mode replace|append",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [400.0, 70.0, 580.0, 20.0],
          "presentation": 1,
          "presentation_rect": [10.0, 56.0, 580.0, 20.0],
          "fontsize": 9.0,
          "textcolor": [0.5, 0.5, 0.5, 1.0]
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
          "patching_rect": [520.0, 260.0, 55.0, 22.0],
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
          "patching_rect": [520.0, 300.0, 60.0, 22.0],
          "presentation": 0
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
          "source": ["obj-inject-btn", 0],
          "destination": ["obj-js", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-js", 0],
          "destination": ["obj-status-label", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-js", 1],
          "destination": ["obj-err-label", 0]
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

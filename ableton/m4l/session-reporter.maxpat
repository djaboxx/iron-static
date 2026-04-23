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
    "rect": [
      0.0,
      0.0,
      480.0,
      250.0
    ],
    "bglocked": 0,
    "openinpresentation": 1,
    "default_fontsize": 12.0,
    "default_fontface": 0,
    "default_fontname": "Arial",
    "gridonopen": 1,
    "gridsize": [
      15.0,
      15.0
    ],
    "gridsnaponopen": 1,
    "objectsnaprange": 25.0,
    "magnetictoedge": 0,
    "subpatcher_template": "",
    "assistshowspatchername": 0,
    "boxes": [
      {
        "box": {
          "id": "obj-init",
          "maxclass": "newobj",
          "text": "live.thisdevice",
          "numinlets": 0,
          "numoutlets": 2,
          "outlettype": [
            "bang",
            "bang"
          ],
          "patching_rect": [
            30.0,
            30.0,
            110.0,
            22.0
          ],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-btn",
          "maxclass": "button",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [
            "bang"
          ],
          "patching_rect": [
            30.0,
            75.0,
            40.0,
            40.0
          ],
          "presentation": 1,
          "presentation_rect": [
            20.0,
            25.0,
            40.0,
            40.0
          ],
          "hint": "Dump session state to outputs/live_state.json"
        }
      },
      {
        "box": {
          "id": "obj-btn-label",
          "maxclass": "comment",
          "text": "Dump State",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            80.0,
            85.0,
            90.0,
            20.0
          ],
          "presentation": 1,
          "presentation_rect": [
            68.0,
            33.0,
            90.0,
            20.0
          ],
          "fontsize": 11.0
        }
      },
      {
        "box": {
          "id": "obj-title",
          "maxclass": "comment",
          "text": "IRON STATIC\nsession-reporter",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            220.0,
            25.0,
            200.0,
            40.0
          ],
          "presentation": 1,
          "presentation_rect": [
            170.0,
            10.0,
            200.0,
            40.0
          ],
          "fontsize": 13.0,
          "fontface": 1,
          "textcolor": [
            0.8,
            0.3,
            0.1,
            1.0
          ]
        }
      },
      {
        "box": {
          "id": "obj-status",
          "maxclass": "comment",
          "text": "ready",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            30.0,
            200.0,
            300.0,
            20.0
          ],
          "presentation": 1,
          "presentation_rect": [
            20.0,
            75.0,
            320.0,
            20.0
          ],
          "fontsize": 10.0,
          "textcolor": [
            0.5,
            0.5,
            0.5,
            1.0
          ]
        }
      },
      {
        "box": {
          "id": "obj-js",
          "maxclass": "newobj",
          "text": "js session_reporter.js",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            30.0,
            145.0,
            160.0,
            22.0
          ],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-print",
          "maxclass": "newobj",
          "text": "print session-reporter",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            30.0,
            185.0,
            160.0,
            22.0
          ],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-osc-in",
          "maxclass": "newobj",
          "text": "udpreceive 7400",
          "numinlets": 0,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            220.0,
            75.0,
            130.0,
            22.0
          ],
          "presentation": 0,
          "hint": "OSC trigger: /reporter/dump"
        }
      },
      {
        "box": {
          "id": "obj-route",
          "maxclass": "newobj",
          "text": "route /reporter/dump",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            ""
          ],
          "patching_rect": [
            220.0,
            108.0,
            155.0,
            22.0
          ],
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
          "outlettype": [
            "signal",
            "signal"
          ],
          "patching_rect": [
            350.0,
            175.0,
            55.0,
            22.0
          ],
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
          "patching_rect": [
            350.0,
            215.0,
            60.0,
            22.0
          ],
          "presentation": 0
        }
      }
    ],
    "lines": [
      {
        "patchline": {
          "source": [
            "obj-btn",
            0
          ],
          "destination": [
            "obj-js",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-js",
            0
          ],
          "destination": [
            "obj-print",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-osc-in",
            0
          ],
          "destination": [
            "obj-route",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-route",
            0
          ],
          "destination": [
            "obj-btn",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-plugin-in",
            0
          ],
          "destination": [
            "obj-plugin-out",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-plugin-in",
            1
          ],
          "destination": [
            "obj-plugin-out",
            1
          ]
        }
      }
    ],
    "parameters": {
      "inherited_shortname": 0,
      "parameter_invisible": 0,
      "parameter_type": 0
    },
    "dependency_cache": [
      {
        "name": "session_reporter.js",
        "bootpath": "ableton/m4l",
        "patcherrelativepath": ".",
        "type": "TEXT",
        "implicit": 1
      }
    ],
    "autosave": 0,
    "classnamespace": "box"
  }
}
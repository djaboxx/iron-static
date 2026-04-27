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
    "rect": [0.0, 0.0, 640.0, 320.0],
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
          "patching_rect": [30.0, 68.0, 70.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-js",
          "maxclass": "newobj",
          "text": "js unihuman.js",
          "numinlets": 5,
          "numoutlets": 4,
          "outlettype": ["", "", "", ""],
          "patching_rect": [30.0, 110.0, 175.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-notein",
          "maxclass": "newobj",
          "text": "notein",
          "numinlets": 0,
          "numoutlets": 3,
          "outlettype": ["int", "int", "int"],
          "patching_rect": [240.0, 30.0, 55.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-noteout",
          "maxclass": "newobj",
          "text": "noteout",
          "numinlets": 3,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [240.0, 215.0, 60.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-dial-corrupt",
          "maxclass": "live.dial",
          "long_name": "Corrupt",
          "short_name": "CRP",
          "minimum": 0.0,
          "maximum": 100.0,
          "parameter_enable": 1,
          "initial_enable": 1,
          "initial": [30.0],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["", "dictionary"],
          "patching_rect": [370.0, 30.0, 44.0, 44.0],
          "presentation": 1,
          "presentation_rect": [13.0, 56.0, 44.0, 44.0]
        }
      },
      {
        "box": {
          "id": "obj-dial-mode",
          "maxclass": "live.dial",
          "long_name": "Mode",
          "short_name": "MOD",
          "minimum": 0.0,
          "maximum": 2.0,
          "parameter_enable": 1,
          "initial_enable": 1,
          "initial": [1.0],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["", "dictionary"],
          "patching_rect": [430.0, 30.0, 44.0, 44.0],
          "presentation": 1,
          "presentation_rect": [73.0, 56.0, 44.0, 44.0]
        }
      },
      {
        "box": {
          "id": "obj-toggle-cascade",
          "maxclass": "live.toggle",
          "long_name": "Cascade",
          "short_name": "CAS",
          "parameter_enable": 1,
          "initial_enable": 1,
          "initial": [0],
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [370.0, 100.0, 30.0, 30.0],
          "presentation": 1,
          "presentation_rect": [135.0, 64.0, 28.0, 28.0]
        }
      },
      {
        "box": {
          "id": "obj-toggle-feedback",
          "maxclass": "live.toggle",
          "long_name": "Feedback",
          "short_name": "FBK",
          "parameter_enable": 1,
          "initial_enable": 1,
          "initial": [0],
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [420.0, 100.0, 30.0, 30.0],
          "presentation": 1,
          "presentation_rect": [188.0, 64.0, 28.0, 28.0]
        }
      },
      {
        "box": {
          "id": "obj-pre-corrupt",
          "maxclass": "newobj",
          "text": "prepend corrupt",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [370.0, 150.0, 100.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-pre-mode",
          "maxclass": "newobj",
          "text": "prepend mode",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [430.0, 150.0, 88.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-pre-cascade",
          "maxclass": "newobj",
          "text": "prepend cascade",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [370.0, 180.0, 104.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-pre-feedback",
          "maxclass": "newobj",
          "text": "prepend feedback",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [420.0, 180.0, 108.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-load-display",
          "maxclass": "live.numbox",
          "long_name": "Load",
          "short_name": "LD",
          "minimum": 0.0,
          "maximum": 100.0,
          "parameter_enable": 0,
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["", "dictionary"],
          "patching_rect": [240.0, 160.0, 55.0, 22.0],
          "presentation": 1,
          "presentation_rect": [248.0, 68.0, 55.0, 20.0]
        }
      },

      {
        "box": {
          "id": "obj-title",
          "maxclass": "comment",
          "text": "UNIHUMAN  \u00b7  query-state processor",
          "fontsize": 13.0,
          "fontface": 1,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [550.0, 10.0, 300.0, 20.0],
          "presentation": 1,
          "presentation_rect": [0.0, 5.0, 335.0, 20.0]
        }
      },
      {
        "box": {
          "id": "obj-subtitle",
          "maxclass": "comment",
          "text": "E PHRYGIAN  \u00b7  108 BPM  \u00b7  IGNITION POINT",
          "fontsize": 9.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [550.0, 34.0, 300.0, 14.0],
          "presentation": 1,
          "presentation_rect": [0.0, 24.0, 335.0, 14.0]
        }
      },
      {
        "box": {
          "id": "obj-label-corrupt",
          "maxclass": "comment",
          "text": "CORRUPT",
          "fontsize": 9.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [550.0, 52.0, 55.0, 14.0],
          "presentation": 1,
          "presentation_rect": [10.0, 43.0, 55.0, 14.0]
        }
      },
      {
        "box": {
          "id": "obj-label-mode",
          "maxclass": "comment",
          "text": "MODE",
          "fontsize": 9.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [550.0, 68.0, 55.0, 14.0],
          "presentation": 1,
          "presentation_rect": [76.0, 43.0, 55.0, 14.0]
        }
      },
      {
        "box": {
          "id": "obj-label-cascade",
          "maxclass": "comment",
          "text": "CASCADE",
          "fontsize": 9.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [550.0, 84.0, 58.0, 14.0],
          "presentation": 1,
          "presentation_rect": [128.0, 43.0, 58.0, 14.0]
        }
      },
      {
        "box": {
          "id": "obj-label-feedback",
          "maxclass": "comment",
          "text": "FEEDBACK",
          "fontsize": 9.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [550.0, 100.0, 62.0, 14.0],
          "presentation": 1,
          "presentation_rect": [180.0, 43.0, 62.0, 14.0]
        }
      },
      {
        "box": {
          "id": "obj-label-load",
          "maxclass": "comment",
          "text": "LOAD %",
          "fontsize": 9.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [550.0, 116.0, 55.0, 14.0],
          "presentation": 1,
          "presentation_rect": [248.0, 43.0, 55.0, 14.0]
        }
      },
      {
        "box": {
          "id": "obj-mode-legend",
          "maxclass": "comment",
          "text": "0=b2  1=TRT  2=b7",
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [550.0, 132.0, 110.0, 12.0],
          "presentation": 1,
          "presentation_rect": [60.0, 102.0, 110.0, 12.0]
        }
      }
    ],
    "lines": [
      { "patchline": { "source": ["obj-init",           0], "destination": ["obj-defer",        0] } },
      { "patchline": { "source": ["obj-defer",          0], "destination": ["obj-js",           4] } },
      { "patchline": { "source": ["obj-notein",         0], "destination": ["obj-js",           0] } },
      { "patchline": { "source": ["obj-notein",         1], "destination": ["obj-js",           1] } },
      { "patchline": { "source": ["obj-notein",         2], "destination": ["obj-js",           2] } },
      { "patchline": { "source": ["obj-dial-corrupt",   0], "destination": ["obj-pre-corrupt",  0] } },
      { "patchline": { "source": ["obj-pre-corrupt",    0], "destination": ["obj-js",           3] } },
      { "patchline": { "source": ["obj-dial-mode",      0], "destination": ["obj-pre-mode",     0] } },
      { "patchline": { "source": ["obj-pre-mode",       0], "destination": ["obj-js",           3] } },
      { "patchline": { "source": ["obj-toggle-cascade", 0], "destination": ["obj-pre-cascade",  0] } },
      { "patchline": { "source": ["obj-pre-cascade",    0], "destination": ["obj-js",           3] } },
      { "patchline": { "source": ["obj-toggle-feedback",0], "destination": ["obj-pre-feedback", 0] } },
      { "patchline": { "source": ["obj-pre-feedback",   0], "destination": ["obj-js",           3] } },
      { "patchline": { "source": ["obj-js",             0], "destination": ["obj-noteout",      0] } },
      { "patchline": { "source": ["obj-js",             1], "destination": ["obj-noteout",      1] } },
      { "patchline": { "source": ["obj-js",             2], "destination": ["obj-noteout",      2] } },
      { "patchline": { "source": ["obj-js",             3], "destination": ["obj-load-display", 0] } }
    ]
  }
}

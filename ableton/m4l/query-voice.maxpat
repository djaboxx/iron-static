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
    "rect": [0.0, 0.0, 640.0, 240.0],
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
          "patching_rect": [20.0, 20.0, 110.0, 22.0],
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
          "patching_rect": [20.0, 60.0, 70.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-js",
          "maxclass": "newobj",
          "text": "js query-voice.js",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [20.0, 100.0, 150.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-print",
          "maxclass": "newobj",
          "text": "print qv",
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [20.0, 140.0, 70.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-plugin",
          "maxclass": "newobj",
          "text": "plugin~",
          "numinlets": 0,
          "numoutlets": 2,
          "outlettype": ["signal", "signal"],
          "patching_rect": [200.0, 20.0, 60.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-plugout",
          "maxclass": "newobj",
          "text": "plugout~",
          "numinlets": 2,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [200.0, 60.0, 65.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-pre-texture",
          "maxclass": "newobj",
          "text": "prepend texture",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [300.0, 20.0, 112.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-pre-tension",
          "maxclass": "newobj",
          "text": "prepend tension",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [300.0, 50.0, 112.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-pre-breath",
          "maxclass": "newobj",
          "text": "prepend breath",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [300.0, 80.0, 108.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-pre-burn",
          "maxclass": "newobj",
          "text": "prepend burn",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [300.0, 110.0, 96.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-pre-tail",
          "maxclass": "newobj",
          "text": "prepend tail",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [300.0, 140.0, 88.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-pre-drift",
          "maxclass": "newobj",
          "text": "prepend drift",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [300.0, 170.0, 88.0, 22.0],
          "presentation": 0
        }
      },
      {
        "box": {
          "id": "obj-dial-texture",
          "maxclass": "live.dial",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["", "dictionary"],
          "patching_rect": [450.0, 20.0, 44.0, 44.0],
          "presentation": 1,
          "presentation_rect": [30.0, 60.0, 44.0, 44.0],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "Texture",
              "parameter_shortname": "TEX",
              "parameter_minimum": 0.0,
              "parameter_maximum": 1.0,
              "parameter_initial": [0.2],
              "parameter_initial_enable": 1,
              "parameter_type": 0,
              "parameter_unitstyle": 0
            }
          }
        }
      },
      {
        "box": {
          "id": "obj-dial-tension",
          "maxclass": "live.dial",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["", "dictionary"],
          "patching_rect": [450.0, 75.0, 44.0, 44.0],
          "presentation": 1,
          "presentation_rect": [128.0, 60.0, 44.0, 44.0],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "Tension",
              "parameter_shortname": "TNS",
              "parameter_minimum": 0.0,
              "parameter_maximum": 1.0,
              "parameter_initial": [0.28],
              "parameter_initial_enable": 1,
              "parameter_type": 0,
              "parameter_unitstyle": 0
            }
          }
        }
      },
      {
        "box": {
          "id": "obj-dial-breath",
          "maxclass": "live.dial",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["", "dictionary"],
          "patching_rect": [450.0, 130.0, 44.0, 44.0],
          "presentation": 1,
          "presentation_rect": [226.0, 60.0, 44.0, 44.0],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "Breath",
              "parameter_shortname": "BRH",
              "parameter_minimum": 0.0,
              "parameter_maximum": 1.0,
              "parameter_initial": [0.05],
              "parameter_initial_enable": 1,
              "parameter_type": 0,
              "parameter_unitstyle": 0
            }
          }
        }
      },
      {
        "box": {
          "id": "obj-dial-burn",
          "maxclass": "live.dial",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["", "dictionary"],
          "patching_rect": [510.0, 20.0, 44.0, 44.0],
          "presentation": 1,
          "presentation_rect": [324.0, 60.0, 44.0, 44.0],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "Burn",
              "parameter_shortname": "BRN",
              "parameter_minimum": 0.0,
              "parameter_maximum": 1.0,
              "parameter_initial": [0.57],
              "parameter_initial_enable": 1,
              "parameter_type": 0,
              "parameter_unitstyle": 0
            }
          }
        }
      },
      {
        "box": {
          "id": "obj-dial-tail",
          "maxclass": "live.dial",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["", "dictionary"],
          "patching_rect": [510.0, 75.0, 44.0, 44.0],
          "presentation": 1,
          "presentation_rect": [422.0, 60.0, 44.0, 44.0],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "Tail",
              "parameter_shortname": "TAIL",
              "parameter_minimum": 0.0,
              "parameter_maximum": 1.0,
              "parameter_initial": [0.48],
              "parameter_initial_enable": 1,
              "parameter_type": 0,
              "parameter_unitstyle": 0
            }
          }
        }
      },
      {
        "box": {
          "id": "obj-dial-drift",
          "maxclass": "live.dial",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["", "dictionary"],
          "patching_rect": [510.0, 130.0, 44.0, 44.0],
          "presentation": 1,
          "presentation_rect": [520.0, 60.0, 44.0, 44.0],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "Drift",
              "parameter_shortname": "DRF",
              "parameter_minimum": 0.0,
              "parameter_maximum": 1.0,
              "parameter_initial": [0.63],
              "parameter_initial_enable": 1,
              "parameter_type": 0,
              "parameter_unitstyle": 0
            }
          }
        }
      },
      {
        "box": {
          "id": "obj-title",
          "maxclass": "comment",
          "text": "QUERY VOICE  ·  chain macro controller",
          "fontsize": 13.0,
          "fontface": 1,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [600.0, 10.0, 400.0, 20.0],
          "presentation": 1,
          "presentation_rect": [0.0, 5.0, 400.0, 20.0]
        }
      },
      {
        "box": {
          "id": "obj-subtitle",
          "maxclass": "comment",
          "text": "E PHRYGIAN  ·  108 BPM  ·  Meld / Roar / Echo  →  Ignition Point",
          "fontsize": 9.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [600.0, 34.0, 500.0, 14.0],
          "presentation": 1,
          "presentation_rect": [0.0, 25.0, 560.0, 14.0]
        }
      },
      {
        "box": {
          "id": "lbl-texture",
          "maxclass": "comment",
          "text": "TEXTURE",
          "fontsize": 9.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [600.0, 60.0, 62.0, 14.0],
          "presentation": 1,
          "presentation_rect": [22.0, 45.0, 62.0, 14.0]
        }
      },
      {
        "box": {
          "id": "lbl-tension",
          "maxclass": "comment",
          "text": "TENSION",
          "fontsize": 9.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [600.0, 76.0, 62.0, 14.0],
          "presentation": 1,
          "presentation_rect": [120.0, 45.0, 62.0, 14.0]
        }
      },
      {
        "box": {
          "id": "lbl-breath",
          "maxclass": "comment",
          "text": "BREATH",
          "fontsize": 9.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [600.0, 92.0, 56.0, 14.0],
          "presentation": 1,
          "presentation_rect": [219.0, 45.0, 56.0, 14.0]
        }
      },
      {
        "box": {
          "id": "lbl-burn",
          "maxclass": "comment",
          "text": "BURN",
          "fontsize": 9.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [600.0, 108.0, 40.0, 14.0],
          "presentation": 1,
          "presentation_rect": [332.0, 45.0, 40.0, 14.0]
        }
      },
      {
        "box": {
          "id": "lbl-tail",
          "maxclass": "comment",
          "text": "TAIL",
          "fontsize": 9.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [600.0, 124.0, 35.0, 14.0],
          "presentation": 1,
          "presentation_rect": [432.0, 45.0, 35.0, 14.0]
        }
      },
      {
        "box": {
          "id": "lbl-drift",
          "maxclass": "comment",
          "text": "DRIFT",
          "fontsize": 9.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [600.0, 140.0, 40.0, 14.0],
          "presentation": 1,
          "presentation_rect": [528.0, 45.0, 40.0, 14.0]
        }
      },
      {
        "box": {
          "id": "sub-texture",
          "maxclass": "comment",
          "text": "osc · rough",
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [600.0, 160.0, 66.0, 12.0],
          "presentation": 1,
          "presentation_rect": [18.0, 107.0, 66.0, 12.0]
        }
      },
      {
        "box": {
          "id": "sub-tension",
          "maxclass": "comment",
          "text": "cutoff · q",
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [600.0, 174.0, 60.0, 12.0],
          "presentation": 1,
          "presentation_rect": [118.0, 107.0, 60.0, 12.0]
        }
      },
      {
        "box": {
          "id": "sub-breath",
          "maxclass": "comment",
          "text": "atk · rel",
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [600.0, 188.0, 55.0, 12.0],
          "presentation": 1,
          "presentation_rect": [218.0, 107.0, 55.0, 12.0]
        }
      },
      {
        "box": {
          "id": "sub-burn",
          "maxclass": "comment",
          "text": "drive · shaper",
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [600.0, 202.0, 76.0, 12.0],
          "presentation": 1,
          "presentation_rect": [308.0, 107.0, 76.0, 12.0]
        }
      },
      {
        "box": {
          "id": "sub-tail",
          "maxclass": "comment",
          "text": "fdbk · dark",
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [600.0, 216.0, 65.0, 12.0],
          "presentation": 1,
          "presentation_rect": [410.0, 107.0, 65.0, 12.0]
        }
      },
      {
        "box": {
          "id": "sub-drift",
          "maxclass": "comment",
          "text": "detune · lfo",
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [],
          "patching_rect": [600.0, 230.0, 65.0, 12.0],
          "presentation": 1,
          "presentation_rect": [510.0, 107.0, 65.0, 12.0]
        }
      }
    ],
    "lines": [
      { "patchline": { "source": ["obj-init",    0], "destination": ["obj-defer",       0] } },
      { "patchline": { "source": ["obj-defer",   0], "destination": ["obj-js",          0] } },
      { "patchline": { "source": ["obj-plugin",  0], "destination": ["obj-plugout",      0] } },
      { "patchline": { "source": ["obj-plugin",  1], "destination": ["obj-plugout",      1] } },
      { "patchline": { "source": ["obj-js",      0], "destination": ["obj-print",        0] } },
      { "patchline": { "source": ["obj-dial-texture", 0], "destination": ["obj-pre-texture", 0] } },
      { "patchline": { "source": ["obj-pre-texture",  0], "destination": ["obj-js",          0] } },
      { "patchline": { "source": ["obj-dial-tension", 0], "destination": ["obj-pre-tension", 0] } },
      { "patchline": { "source": ["obj-pre-tension",  0], "destination": ["obj-js",          0] } },
      { "patchline": { "source": ["obj-dial-breath",  0], "destination": ["obj-pre-breath",  0] } },
      { "patchline": { "source": ["obj-pre-breath",   0], "destination": ["obj-js",          0] } },
      { "patchline": { "source": ["obj-dial-burn",    0], "destination": ["obj-pre-burn",    0] } },
      { "patchline": { "source": ["obj-pre-burn",     0], "destination": ["obj-js",          0] } },
      { "patchline": { "source": ["obj-dial-tail",    0], "destination": ["obj-pre-tail",    0] } },
      { "patchline": { "source": ["obj-pre-tail",     0], "destination": ["obj-js",          0] } },
      { "patchline": { "source": ["obj-dial-drift",   0], "destination": ["obj-pre-drift",   0] } },
      { "patchline": { "source": ["obj-pre-drift",    0], "destination": ["obj-js",          0] } }
    ]
  }
}

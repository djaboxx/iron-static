> **Source**: https://docs.cycling74.com/apiref/lom/controlsurface/  
> **Fetched**: 2026-04-27  

# ControlSurface

A ControlSurface can be reached either directly by the root path `control_surfaces N` or by getting a list of active control surface IDs, via calling _get control_surfaces_ on an Application object.   
The latter list is in the same order in which control surfaces appear in Live's Link/MIDI Preferences. Note the same order is not guaranteed when getting a control surface via the `control_surfaces N` path.   
  
A control surface can be thought of as a software layer between the Live API and, in this case, Max for Live. Individiual controls on the surface are represented by objects that can be grabbed and released via Max for Live, to obtain and give back exclusive control (see _grab_control_ and _release_control_). In this way, parts of the hardware can be controlled via Max for Live while other parts can retain their default functionality.   
  
Additionally, Live offers a special `MaxForLive` control surface that has a _register_midi_control_ function. Using this, Max for Live developers can set up entirely custom control surfaces by adding and grabbing arbitrary controls.

## Canonical Path
[code] 
    control_surfaces N
    
[/code]

## Properties

### pad_layout symbol read-onlyobserve

The active pad layout.  
  
On Push 2 and 3, the layout can be changed with the Note and Session buttons and depends on the loaded instrument. Layout variants can be selected by pressing the Layout button.  
  
Available layouts are:\

  * Melodic mode - the device chain is empty or an Instrument is loaded  
`note.melodic.64_notes` \- Melodic: 64 Notes  
`note.melodic.64_notes_and_macro_variations` \- Melodic: 64 Notes + Macro Variations  
`note.melodic.sequencer` \- Melodic: Sequencer  
`note.melodic.sequencer_and_32_notes` \- Melodic: Sequencer + 32 Notes 

  * Drums mode - a Drum Rack is loaded  
`note.drums.macro_variations` \- Drums: Macro Variations  
`note.drums.64_pads` \- Drums: 64 Pads  
`note.drums.loop_selector` \- Drums: Loop Selector  
`note.drums.16_velocities` \- Drums: 16 Velocities  
`note.drums.16_pitches` \- Drums: 16 Pitches 

  * Session mode - the Session button was pressed  
`session` \- Session is active 




## Functions

### get_control

Parameter: `name`  
Returns the control with the given name.

### get_control_names

Returns the list of all control names.

### grab_control

Parameter: `control`  
Take ownership of the _control_. This releases all standard functionality of the control, so that it can be used exclusively via Max for Live.

### grab_midi

Forward MIDI messages received by the control surface script from the control surface to Max for Live.   
  
Note: the control surface script will only receive those channel messages from Live's engine that it explicitly requests. For example, a script might use a specific note message to toggle transport in Live; it will thus request that this note message be forwarded to it from Live.   
Messages used for purely real-time purposes, on the other hand, will often bypass the script and instead just be sent to Live's tracks; this is true, for example, of Push's pads in Note (but not Session) mode. Accordingly, the API object will not output these real-time pad messages; to work with track messages, use objects such as `midiin`.

### register_midi_control

Parameters:   
`name` [symbol]   
`status` [int]   
`number` [int]   
  
(_MaxForLive_ control surface only) Register a MIDI control defined by _status_ and _number_. Supported status codes are _144_ (note on), _176_ (continuous control) and _224_ (pitchbend).   
Returns the LOM ID associated with the control.   
Once a control is registered and grabbed via _grab_control_ , Live will forward associated MIDI messages that it receives to Max for Live. Max for Live can send values to the control (e.g. to light an LED) by calling _send_value_ on the control object.

### release_control

Parameter: `control`  
Re-establishes the standard functionality for the control.

### release_midi

Stop forwarding MIDI messages received from the control surface to Max for Live.

### send_midi

Parameter: `midi_message` [list of int]   
Send _midi_message_ to the control surface.

### send_receive_sysex

Parameters:   
`sysex_message` [list of int]   
`timeout` [symbol, int]   
Send _sysex_message_ to the control surface and await a response.   
If the message is followed by the word _timeout_ and a float, this sets the response timeout accordingly. The default timeout value is 0.2.   
If the response times out and MIDI has not been grabbed via _grab_midi_ , it's not forwarded to Max for Live. If MIDI has been grabbed via Max for Live, received messages are always forwarded, but the timeout is still reported.

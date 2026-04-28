> **Source**: https://docs.cycling74.com/reference/live.remote~/  
> **Fetched**: 2026-04-27  

_Package Max for Live_

# live.remote~

Realtime control of parameters in Ableton Live and Max for Live. 

## Description

The [live.remote~](</reference/live.remote~>) object allows you to remotely control parameters in Ableton Live and Max for Live in realtime. To understand more about Live's parameters, look up the DeviceParameter Object Class in the [Live Object Model](</userguide/m4l/live_api_overview#live-object-model>) . 

#### Discussion

A parameter in Live and Max for Live is selected using [live.path](</reference/live.path>) or [live.map](</reference/live.map>) and its id is sent to the right inlet of [live.remote~](</reference/live.remote~>) . An example path of a DeviceParameter is  live_set master_track mixer_device volume  . Alternatively, you can get the path to a parameter in Ableton Live's interface by right-clicking a parameter and selecting "Copy LOM Path" in the context-menu (available only in Ableton Live 12).   
  
Integer or float values are sent to the left inlet of [live.remote~](</reference/live.remote~>) , as messages or as an audio signal. The values are applied sample-accurately (if sent by the audio thread of Max) with a constant latency of a single audio buffer.   
  
A parameter is disabled in Live while it is controlled by a [live.remote~](</reference/live.remote~>) , just as if it were controlled by a Macro parameter (but without the green dot). This means that any parameter automation is disabled and the value in the Live set is not changed. Additionally, no undo steps are created. The envelopes remain active. To stop remote-controlling a device parameter and to re-enable it, send  id 0  to the right inlet of [live.remote~](</reference/live.remote~>) . 

## Arguments

None.

## Attributes

### 

smoothing[float]

Set the ramp time that is used for each incoming event. This also performs a temporal downsampling of any signal you send in. For example, a smoothing value of 1 ms will sample the incoming signal every 1 ms and send ramp events which output a linear approximation of the signal. This attribute defaults to 1 ms. 

### 

normalized[int]

Toggles the [live.remote~](</reference/live.remote~>) object's normalized mode, which automatically scales the input values to the target parameter range. When the normalized attribute is set to 1, sending a signal or values in the range 0 to 1 to [live.remote~](</reference/live.remote~>) will automatically scale the values to the range of the receiving parameter. If the normalized attribute is set to 0, automatic scaling is disabled. You will need to provide values between the minimum and maximum of the parameter in order to control it. 

### Common Box Attributes

Below is a list of attributes shared by all objects. If you want to change one of these attributes for an object based on the object box, you need to place the word  sendbox  in front of the attribute name, or use the object's [Inspector](</userguide/inspector>). 

### 

annotation[symbol]

Sets the text that will be displayed in the Clue window when the user moves the mouse over the object. 

### 

background[int]: 0

Adds or removes the object from the patcher's background layer.  background 1  adds the object to the background layer,  background 0  removes it. Objects in the background layer are shown behind all objects in the default foreground layer. 

### 

color[4 floats]

Sets the color for the object box outline. 

### 

fontface[int]

Sets the type style used by the object. The options are:   
  
plain   
bold   
italic   
bold italic   
Possible values:  
  
0 = 'regular'   
1 = 'bold'   
2 = 'italic'   
3 = 'bold italic' 

### 

fontname[symbol]

Sets the object's font. 

### 

fontsize[float]

Sets the object's font size (in points).   
Possible values:  
  
'8'   
'9'   
'10'   
'11'   
'12'   
'13'   
'14'   
'16'   
'18'   
'20'   
'24'   
'30'   
'36'   
'48'   
'64'   
'72' 

### 

hidden[int]: 0

Toggles whether an object is hidden when the patcher is locked. 

### 

hint[symbol]

Sets the text that will be displayed in as a pop-up hint when the user moves the mouse over the object in a locked patcher. 

### 

ignoreclick[int]: 0

Toggles whether an object ignores mouse clicks in a locked patcher. 

### 

jspainterfile[symbol]

You can override the default appearance of a user interface object by assigning a [JavaScript](</userguide/javascript>) file with code for painting the object. The file must be in the search path. 

### 

patching_rect[4 floats]: 0. 0. 100. 0.

Aliases: patching_position, patching_size

Sets the position and size of the object in the patcher window. 

### 

position[2 floats]

write-only

Sets the object's x and y position in both patching and presentation modes (if the object belongs to its patcher's presentation), leaving its size unchanged. 

### 

presentation[int]: 0

Sets whether an object belongs to the patcher's presentation. 

### 

presentation_rect[4 floats]: 0. 0. 0. 0.

Aliases: presentation_position, presentation_size

Sets the x and y position and width and height of the object in the patcher's presentation, leaving its patching position unchanged. 

### 

rect[4 floats]

write-only

Sets the x and y position and width and height of the object in both patching and presentation modes (if the object belongs to its patcher's presentation). 

### 

size[2 floats]

write-only

Sets the object's width and height in both patching and presentation modes (if the object belongs to its patcher's presentation), leaving its position unchanged. 

### 

textcolor[4 floats]

Sets the color for the object's text in RGBA format. 

### 

textjustification[int]

Sets the justification for the object's text.   
Possible values:  
  
0 = 'left'   
1 = 'center'   
2 = 'right' 

### 

valuepopup[int]: 0

For objects with single values, enabling valuepopup will display the object's current value in a popup caption when the mouse is over the object or it is being changed with the mouse. 

### 

valuepopuplabel[int]: 0

Sets the source of a text label shown in a value popup caption.   
Possible values:  
  
0 = 'None'   
1 = 'Hint'   
2 = 'Scripting Name'   
3 = 'Parameter Long Name'   
4 = 'Parameter Short Name' 

### 

varname[symbol]

Sets the patcher's scripting name, which can be used to address the object by name in [pattr](</reference/pattr>), scripting messages to [thispatcher](</reference/thispatcher>), and the [js](</reference/js>) object. 

## Inlets

### 

Left inlet

value (signal/float) Sets the value of the parameter object specified by  id  in the right inlet. For the valid range, refer to the min and max properties of the target parameter. The value curve is linear to the parameter's GUI control in Live. 

### 

Right inlet

id _nn_ Sets object  id  in the format  id _nn_ to select the target parameter (DeviceParameter Object) in Live and Max for Live to control.   
id 0  means no object, i.e. the remote stops controlling the target parameter. This is also the initial state. 

## Messages

### 

float

A floating point number value received in the left inlet will be applied to the selected Live parameter (DeviceParameter Object), if any, at the beginning of the next audio buffer, or at the end of a pending ramp (see smoothing). 

Arguments:

  * value [float]   




### 

int

An integer number value received in the left inlet will be applied to the selected Live parameter (DeviceParameter Object), if any, at the beginning of the next audio buffer, or at the end of a pending ramp (see smoothing). 

Arguments:

  * value [int]   




### 

list

Start a ramp with a list of two floats, similar to the [line~](</reference/line~>) object. Sending in “1 500” means that the value 1 will be reached in 500 ms, starting at the current value. New ramps will always override the current ramp, so if you want to cut short a ramp, send another value. 

Arguments:

  * target-value [float]   

  * delta-time [number]   




### 

signal

Signal input values received in the left inlet will be applied to the selected parameter (DeviceParameter Object), if any, in realtime. 

### 

id

In right inlet: Sets the selected object. The message has no effect if the id is not a parameter (DeviceParameter Object). 

Arguments:

  * parameter id [int]   




### 

getid

The mapped object's id is sent from the outlet, preceded by the word  id . If there is no mapped object,  id 0  will be sent. 

## Inspector

### 

Persistence

The [live.remote~](</reference/live.remote~>) object has a special entry in its inspector labeled "Use Persistent Mapping". This setting, when enabled, causes the  id  associated with the object, in this case the id of the parameter, to persist when the Ableton Live Set is saved and restored, and when the Max Device is moved between the Live application and the Max editor, or within the Live Set. Beginning in Live 8.2.2, Live API ids remain persistent between launches of Live, which in conjunction with the  Persistence  feature of [live.object](</reference/live.object>) , [live.observer](</reference/live.observer>) and [live.remote~](</reference/live.remote~>) , makes it possible to create simpler devices which retain their association with elements in the Ableton Live user interface. 

## See Also

Name | Description  
---|---  
[JS API](<https://appdocs.cycling74.com/apiref/js>) | JS API  
[Live API Overview](</userguide/m4l/live_api_overview>) | Live API Overview  
[Creating Devices that use the Live API](</userguide/m4l/live_api>) | Creating Devices that use the Live API  
[Live Object Model](<https://appdocs.cycling74.com/apiref/lom>) | Live Object Model  
[live.object](</reference/live.object>) |  Perform operations on Live objects   
[live.observer](</reference/live.observer>) |  Monitor changes in Live objects   
[live.path](</reference/live.path>) |  Navigate to objects in the Live application   
[live.modulate~](</reference/live.modulate~>) |  Modulate Ableton Live and Max for Live Parameters

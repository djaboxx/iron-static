> **Source**: https://docs.cycling74.com/reference/live.path/  
> **Fetched**: 2026-04-27  

_Package Max for Live_

# live.path

Navigate to objects in the Live application 

## Description

[live.path](</reference/live.path>) is used to navigate to Live objects on which the [live.object](</reference/live.object>), [live.observer](</reference/live.observer>) and [live.remote~](</reference/live.remote~>) objects operate. The navigation is purely path-based and is independent of the objects currently present in Live (navigating to a nonexistent path will result in the message  id 0  being sent out the left and middle outputs rather than an error message).   
  
_Note: The Live API runs in the main thread in Live, and all messages to and from the API are automatically deferred._

## Arguments

### 

initial path[symbol]

optional

Specify an initial path as argument to [live.path](</reference/live.path>), without any quotes. 

## Attributes

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

Single inlet

Gets all command messages described below. 

## Outlets

### 

Left outlet

Sends the message  id _nn_ in response to a  goto ,  bang  or  getid  message **only**. Use this outlet if you want to keep working with a particular object determined at goto or bang time, even if its position in Live changes.   
  
For example, consider a fresh Live set with two tracks, "1 Audio" as the leftmost track and "2 MIDI" to the right of it. If you navigate to the "2 MIDI" track ( goto live_set tracks 1 ) and you create a new Audio track between "1 Audio" and "2 MIDI", your original MIDI track now would be at  live_sets tracks 2 . But since the id number of the MIDI track would stay the same and no new id is sent out to the left outlet, the live.xxx objects connected to this outlet keep working with the MIDI track, until you sent another goto. 

### 

Middle outlet

Sends  id _nn_ whenever the id of the object at the current path changes (because the current path is changed or because the object at this place in Live has changed, for example. Use this outlet if you want to keep working with the same path, whatever object there might be. This outlet is very useful for things like  live_set view detail_clip .   
  
Consider the example above. If the live.xxx objects would be connected to the middle outlet of [live.path](</reference/live.path>), then they would work with the newly created audio track.   
  
The spontaneous sending of object ids out of the middle outlet, i.e. without an inlet message causing it, but caused by a change in Live, is called a notification.   
**Note:** It is not possible to modify the Live set from such a notification. 

### 

Right outlet

Sends responses to  getpath ,  getchildren ,  getcount . 

## Messages

### 

getid

TEXT_HERE 

### 

getcount

Arguments:   
child-name  is the name of a child of the object at the current path.   
  
Operation:   
Sends a count message to the right outlet, containing the name of the child and its number of entries.   
  
Remarks:   
The given child must be a list.   
  


Outlet  |  Output  |  Example   
---|---|---  
right  |  count _child-name_ _count_ |  count clip_slots 2   
  
Arguments:

  * child-name [symbol]   




### 

getchildren

Operation:   
Sends a list of children of the object at the current path, if any, to the right outlet.   
  
Remarks:   
The child names are the same names as used in the goto message.   
  


Outlet  |  Output  |  Example   
---|---|---  
right  |  children _list-of-child-names_ |  children canonical_parent clip_slots   
  
### 

getpath

Operation:   
Sends a path message with the current path to the right outlet.   
  


Outlet  |  Output  |  Example   
---|---|---  
right  |  path _path_ |  path live_set scenes 1   
  
### 

bang, getid

Operation:   
Sends the id of the object at the current path to left and middle outlets. Sends  id 0  if there is no object at the current path.   
  


Outlet  |  Output  |  Example   
---|---|---  
left  |  id _nn_ |  id 5   
middle  |  id _nn_ |  id 5   
  
### 

path

Same as  goto  but limited to absolute paths that start with a root object name like  live_app ,  live_set ,  this_device  or  control_surfaces _N_ . 

Arguments:

  * absolute-path [symbol]   




### 

goto

Arguments:   
_path_ is an absolute path (starts with live_app, live_set or control_surfaces _N_) or a relative path, or  up    
  
Operation:   
Navigates to given path and sends id of the object at that path out the left and middle outlets. If there is no object at the path,  id 0  is sent.   
  
Remarks:   
You cannot go to a list property, only to one of its members.   
invalid:  goto live_set scenes    
correct:  goto live_set scenes 3    
  


Outlet  |  Output  |  Example   
---|---|---  
left  |  id _nn_ |  id 5   
middle  |  id _nn_ |  id 5   
  
Arguments:

  * path [symbol]   




## See Also

Name | Description  
---|---  
[JS API](<https://appdocs.cycling74.com/apiref/js>) | JS API  
[Live API Overview](</userguide/m4l/live_api_overview>) | Live API Overview  
[Creating Devices that use the Live API](</userguide/m4l/live_api>) | Creating Devices that use the Live API  
[Live Object Model](<https://appdocs.cycling74.com/apiref/lom>) | Live Object Model  
[live.object](</reference/live.object>) |  Perform operations on Live objects   
[live.observer](</reference/live.observer>) |  Monitor changes in Live objects   
[live.remote~](</reference/live.remote~>) |  Realtime control of parameters in Ableton Live and Max for Live.

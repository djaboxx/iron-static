> **Source**: https://docs.cycling74.com/reference/live.observer/  
> **Fetched**: 2026-04-27  

_Package Max for Live_

# live.observer

Monitor changes in Live objects 

## Description

[live.observer](</reference/live.observer>) is used to listen to changes in the values of properties of Live objects. This object works in conjunction with the [live.path](</reference/live.path>) object, which sends  id _nn_ messages into the right inlet of [live.observer](</reference/live.observer>) .   
  
After an object id and property is specified, its value is sent out the left outlet. From this moment on, the value is sent on each change of the property ('notification') as well as in response to bang messages.   
  
The left outlet is reserved for value messages, all other output is sent to the right outlet.   
  
Not all properties can be observed, please consult the [Live Object Model](</userguide/m4l/live_api_overview#live-object-model>) to see which can. Also, it is not possible to modify the live set from a notification, i.e. while you are receiving a value message spontaneously sent by a [live.observer](</reference/live.observer>) 's outlet.   
  
Besides properties, it is also possible to observer children of Live objects. Their values are object ids or lists of them.   
  
_Note: The Live API runs in the main thread in Live, and all messages to and from the API are automatically deferred._

## Arguments

### 

property[symbol]

optional

Specify a property or child name as argument to [live.observer](</reference/live.observer>) . 

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

Left inlet

Gets all command messages described below. 

### 

Right inlet

Gets object id message  id _nn_ to select the object to operate upon. In response to the id message, the current value of the property, if a property was already selected, is sent out the left outlet.   
id 0  means no object, i.e. all messages to the left inlet are ignored, which is also the initial state. 

## Outlets

### 

Left outlet

Sends the current value of the selected property of the selected object. The value type depends on the property, as described in the Live Object Model, and may be int, float, symbol,  id _nn_ or lists of ids. 

### 

Right outlet

Sends responses to  getproperty  ,  gettype  ,  getid  . 

## Messages

### 

property

Arguments:   
_property_ the name of a property of the current object   
  
Operation:   
Selects the property to be observed. Outputs the current value to the left outlet if a proper Live object is selected.   
  
Remark:   
Not all properties can be observed.   
The types of the properties are given in the Live Object Model.   
  


Outlet  |  Output  |  Example   
---|---|---  
left  |  _value_ |  3.1415926   
  
Arguments:

  * property [symbol]   




### 

property

Arguments:   
_child_ the name of a child of the current object   
  
Operation:   
Selects the child id to be observed. Outputs the id (or "id 0") to the left outlet if the selected Live object has such a child.   
  
Remark:   
Not all children can be observed.   
  


Outlet  |  Output  |  Example   
---|---|---  
left  |  id _nn_ |  id 17   
  
Arguments:

  * child [symbol]   




### 

property

Arguments:   
_child_ the name of a child list of the current object   
  
Operation:   
Selects the child list to be observed. Outputs the id list (or nothing) to the left outlet if the selected Live object has such a list child.   
  
Remark:   
Not all child lists can be observed.   
  


Outlet  |  Output  |  Example   
---|---|---  
left  |  id _nn_ ... id _mm_ |  id 4 id 5   
  
Arguments:

  * list-child [symbol]   




### 

getproperty

Operation:   
Sends the name of the selected property (or child resp. list-child) out the right outlet.   
  


Outlet  |  Output  |  Example   
---|---|---  
right  |  property _property_ or    
property _child_ |  property name or   
property selected_track   
  
### 

gettype

Operation:   
Sends the type of currently observed property or child to the right outlet. The types of the properties and children are given in the Live Object Model.   
  
For list-children it just sends  type tuple  , w/o further type information. 

Outlet  |  Output  |  Example   
---|---|---  
right  |  type _property-type_ or   
type _object-type_ |  type int  or   
type Track   
  
### 

getid

Operation:   
Sends the id of the currently observed Live object to the right outlet.   
  


Outlet  |  Output  |  Example   
---|---|---  
right  |  id _nn_ |  id 20   
  
### 

bang

Operation:   
Sends current value of selected property of current object to the left outlet. Does nothing if no property or no Live object is selected or if they don't match.   
  


Outlet  |  Output  |  Example   
---|---|---  
left  |  _value_ |  Drums   
  
### 

id nn

Operation:   
Sets the current object. The message has the same effect if sent to both the right or the left inlet. For clarity it is suggested to always use the right inlet to supply the object id.   
  
\- no output - 

## Inspector

### 

Persistence

The [live.observer](</reference/live.observer>) object has a special entry in its inspector labelled "Use Persistent Mapping". This setting, when enabled, causes the  id  associated with the object to persist when the Live document is saved and restored, and when the Max Device is moved between the Live application and the Max editor, or within the Live Set. Beginning in Live 8.2.2, Live API ids remain persistent between launches of Live, which in conjunction with the  Persistence  feature of [live.object](</reference/live.object>) , [live.observer](</reference/live.observer>) and [live.remote~](</reference/live.remote~>) , makes it possible to create simpler devices which retain their association with elements in the Live user interface. 

## See Also

Name | Description  
---|---  
[JS API](<https://appdocs.cycling74.com/apiref/js>) | JS API  
[Live API Overview](</userguide/m4l/live_api_overview>) | Live API Overview  
[Creating Devices that use the Live API](</userguide/m4l/live_api>) | Creating Devices that use the Live API  
[Live Object Model](<https://appdocs.cycling74.com/apiref/lom>) | Live Object Model  
[live.path](</reference/live.path>) |  Navigate to objects in the Live application   
[live.object](</reference/live.object>) |  Perform operations on Live objects   
[live.remote~](</reference/live.remote~>) |  Realtime control of parameters in Ableton Live and Max for Live.

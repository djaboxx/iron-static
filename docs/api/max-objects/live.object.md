> **Source**: https://docs.cycling74.com/reference/live.object/  
> **Fetched**: 2026-04-27  

_Package Max for Live_

# live.object

Perform operations on Live objects 

## Description

[live.object](</reference/live.object>) is used to perform operations on Live objects that have been selected using the [live.path](</reference/live.path>) object. These operations include retrieving information on the current state of the Live API and setting values to control Live.   
  
_Note: The Live API runs in the main thread in Live, and all messages to and from the API are automatically deferred._

## Arguments

None.

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

Gets object id message  id _nn_ to select the object to operate upon.   
id 0  means no object, i.e. all messages to the left inlet are ignored, which is also the initial state. 

## Outlets

### 

Left outlet

Sends responses to  get ,  call ,  bang ,  getid ,  getinfo ,  gettype  and  getpath . 

## Messages

### 

getid

The current object's id is sent from the outlet, preceded by the word  id . If there is no current object,  id 0  will be sent. 

### 

id nn

Operation:   
Sets the current object. The message has the same effect if sent to both the right or the left inlet. For clarity it is suggested to always use the right inlet to supply the object id.   
  
\- no output - 

### 

getpath

Operation:   
Sends the canonical path of current object.   
  


Outlet  |  Output  |  Example   
---|---|---  
left  |  path _path_ |  path live_set return_tracks 0   
  
### 

gettype

Operation:   
Sends the type (a.k.a. class) of the current object.   
  


Outlet  |  Output  |  Example   
---|---|---  
left  |  type _object-type_ |  type Song   
  
### 

getinfo

Operation:   
Sends a description of the current object.   
  
Output to left outlet (most lines may occur multiple times, last line is  info done ):   
  
info id _nn_   
info type _object-type_   
info description _description_   
info children _list-child_ _object-type_   
info child _child_ _object-type_   
info property _property_ _property-type_   
info function _function_   
info done   
  
Example output:   
  
info id 3   
info type Scene   
info description This class represents a series of ClipSlots in Lives session view matrix   
info children clip_slots ClipSlot   
info child canonical_parent Song   
info property is_triggered bool   
info property name symbol   
info property tempo float   
info function fire   
info function fire_as_selected   
info function set_fire_button_state   
info done 

### 

bang, getid

Operation:   
Sends the id of the current Live object to the outlet.   
  


Outlet  |  Output  |  Example   
---|---|---  
left  |  id _nn_ |  id 5   
  
### 

call

Arguments:   
_function_ the name of the function   
_parameter-list_ an optional list of parameters   
  
Operation:   
Calls the given function of the current object, optionally with a list of parameters.   
  
Remark:   
The types of the parameters are given in the Live Object Model.   
  


Outlet  |  Output  |  Example   
---|---|---  
left  |  _function_ _value_ |  get_beats_loop_length 004.00.00.000   
  
Arguments:

  * function [symbol]   

  * parameter-list [list of different types]   




### 

set

Arguments:   
_list-child_ the name of a list child of the current object   
id _nn_... id _mm_ the new list of objects for the given name   
  
Operation:   
Set the list child to contain the given ids.   
  
Remark:   
Not all children can be set.   
  
\- no output - 

Arguments:

  * list-child [symbol]   

  * id nn ... id mm [id-list]   




### 

set

Arguments:   
_child_ the name of a child of the current object   
id _nn_ the new child object for this name   
  
Operation:   
Set the child name to point to the given child.   
  
Remark:   
Not all children can be set.   
  
\- no output - 

Arguments:

  * child [symbol]   

  * id nn [id]   




### 

set

Arguments:   
_list-property_ the name of a list property of the current object   
_value-list_ the new values for the property   
  
Operation:   
Set the given list property to the value list.   
  
Remark:   
Not all properties can be set. The types of the properties are given in the Live Object Model.   
  
\- no output - 

Arguments:

  * list-property [symbol]   

  * value-list [various types]   




### 

set

Arguments:   
_property_ the name of a single-value property of the current object   
_value_ the new value for the property   
  
Operation:   
Set the value of given property of the current object.   
  
Remark:   
Not all properties can be set. The types of the properties are given in the Live Object Model.   
  
\- no output - 

Arguments:

  * property [symbol]   

  * value [various types]   




### 

get

Arguments:   
_list-child_ the name of a list-child of the current object   
  
Operation:   
Sends the ids of the elements of the list-child of the current object.   
  


Outlet  |  Output  |  Example   
---|---|---  
left  |  _list-child_ id _nn_... id _mm_ |  clip_slots id 4 id 5   
  
Arguments:

  * list-child [symbol]   




### 

get

Arguments:   
_child_ the name of a child of the current object   
  
Operation:   
Sends the id of the child of the current object.   
  


Outlet  |  Output  |  Example   
---|---|---  
left  |  _child_ id _nn_ |  master_track id 10   
  
Arguments:

  * child [symbol]   




### 

get

Arguments:   
_list-property_ the name of a list property of the current object   
  
Operation:   
Sends the list of values of given property of the current object.   
  


Outlet  |  Output  |  Example   
---|---|---  
left  |  _list-property_ _list of values_ |  input_routings Ext. In Max Resampling 1-Audio A-Return Master No Input   
  
Arguments:

  * list-property [symbol]   




### 

get

Arguments:   
_property_ the name of a single-value property of the current object   
  
Operation:   
Sends value of given property of the current object.   
  


Outlet  |  Output  |  Example   
---|---|---  
left  |  _property_ _value_ |  name base solo 3   
  
Arguments:

  * property [symbol]   




## Inspector

### 

Persistence

The [live.object](</reference/live.object>) object has a special entry in its inspector labelled "Use Persistent Mapping". This setting, when enabled, causes the  id  associated with the object to persist when the Live document is saved and restored, and when the Max Device is moved between the Live application and the Max editor, or within the Live Set. Beginning in Live 8.2.2, Live API ids remain persistent between launches of Live, which in conjunction with the  Persistence  feature of [live.object](</reference/live.object>), [live.observer](</reference/live.observer>) and [live.remote~](</reference/live.remote~>), makes it possible to create simpler devices which retain their association with elements in the Live user interface. 

## See Also

Name | Description  
---|---  
[JS API](<https://appdocs.cycling74.com/apiref/js>) | JS API  
[Live API Overview](</userguide/m4l/live_api_overview>) | Live API Overview  
[Creating Devices that use the Live API](</userguide/m4l/live_api>) | Creating Devices that use the Live API  
[Live Object Model](<https://appdocs.cycling74.com/apiref/lom>) | Live Object Model  
[live.path](</reference/live.path>) |  Navigate to objects in the Live application   
[live.observer](</reference/live.observer>) |  Monitor changes in Live objects   
[live.remote~](</reference/live.remote~>) |  Realtime control of parameters in Ableton Live and Max for Live.

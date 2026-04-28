> **Source**: https://docs.cycling74.com/reference/live.thisdevice/  
> **Fetched**: 2026-04-27  

_Package Max for Live_

# live.thisdevice

Send a bang automatically when a Max Device is loaded, report device state 

## Description

[live.thisdevice](</reference/live.thisdevice>) reports three pieces of information about your Max Device. A  bang  message is automatically sent from the left outlet when the Max Device is opened and completely initialized, or when the containing patcher is part of another file that is opened. Additionally, a  bang  will be reported every time a new preset is loaded or the device is saved (and thus reloaded within the Live application). A  1  or  0  will be sent from the middle outlet when the Device is enabled or disabled, respectively. A  1  or  0  will be sent from the right outlet when preview mode for the Device is enabled or disabled, respectively. Used within Max, [live.thisdevice](</reference/live.thisdevice>) functions essentially like the [loadbang](</reference/loadbang>) object. The middle and right outlets are inactive in this case. 

## Arguments

None.

## Attributes

### 

openinpresentation[int]

Open in Presentation 

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

## Messages

### 

bang

Sending a  bang  message to a [live.thisdevice](</reference/live.thisdevice>) object causes it to output a  bang  message from the leftmost outlet. 

### 

(mouse)

Double-clicking on a  live.thisdevice  object causes it to output a  bang  message from the leftmost outlet. 

### 

getstate

Sending a  getstate  message to a [live.thisdevice](</reference/live.thisdevice>) object causes it to output the Max Device state from the rightmost outlet. 

### 

loadbang

Same as  bang . 

### 

setwidth

The setwidth message will dynamically set the width of the Max for Live device.   
**Note:** This width is not automatically saved as part of the preset and/or Live set.   
The message  setwidth 0  will return to the default condition where the width of the device is calculated by using the devices's visible objects. 

Arguments:

  * width [int]   




## See Also

Name | Description  
---|---  
[active](</reference/active>) |  Send 1 when patcher window is active, 0 when inactive   
[button](</reference/button>) |  Blink and send a bang   
[closebang](</reference/closebang>) |  Send a bang on close   
[freebang](</reference/freebang>) |  Send a bang when a patcher is freed   
[loadbang](</reference/loadbang>) |  Send a bang when a patcher is loaded   
[loadmess](</reference/loadmess>) |  Send a message when a patch is loaded   
[thispatcher](</reference/thispatcher>) |  Send messages to a patcher

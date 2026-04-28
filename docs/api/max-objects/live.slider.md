> **Source**: https://docs.cycling74.com/reference/live.slider/  
> **Fetched**: 2026-04-27  

_Package Max for Live_

# live.slider

Output numbers by moving a slider onscreen 

## Description

[live.slider](</reference/live.slider>) is a user interface object that resembles a sliding potentiometer. 

## Arguments

None.

## Attributes

### 

active[int]: 1

Toggles the object's active mode. When the  active  attribute is set to 0, the mouse action does not cause output and the inactive colors are used. 

### 

annotation_name[symbol]: 

The string that is prepended to annotations. This shows up in the Info pane in Live, and the clue window in Max. 

### 

focusbordercolor[4 floats]

Sets the border color in RGBA format to be used when the [live.slider](</reference/live.slider>) has the focus. 

### 

modulationcolor[4 floats]

Sets the modulation color of the [live.slider](</reference/live.slider>) object in RGBA format. 

### 

orientation[int]: 0

Defines the orientation of the [live.slider](</reference/live.slider>) object.   
Possible values:  
  
0 = 'Vertical' ( Vertical )  
Vertical orientation (the default).   
  
1 = 'Horizontal' ( Horizontal )  
Horizontal orientation (the default).   


### 

param_connect[symbol]: 

Establishes a two-way connection between the object and a parameter of a compatible object with parameters such as [gen~](</reference/gen~>) or [jit.gl.slab](</reference/jit.gl.slab>). The object can be used to change the value of the parameter and will update if the parameter value changes. The easiest way to set param_connect is with the attribute's menu in the [inspector](</userguide/inspector>) or the Connect submenu of the [Object Action menu](</userguide/action_menu>). The menu displays all available parameters of compatible objects.   
  
Setting the param_connect attribute with a message requires the target parameter's path, which is the host object's scriping name followed by two colons and the parameter name. For example, for a [gen~](</reference/gen~>) object with scripting name  gen~_AB , the path of the  freq  parameter would be  gen~_AB::freq . You can set a value for the param_connect before the host object or parameter exists, and the object will connect to the parameter once it exists. Refer to the user guide entry for [param_connect](</userguide/param_connect>) for more details. 

### 

parameter_mappable[int]: 1

When parameter_mappable is enabled, the object will be available for mapping to keyboard or MIDI input using the [Mappings feature](</userguide/mapping>). 

### 

relative[int]: 0

Sets the way that the [live.slider](</reference/live.slider>) object responds to mouse clicks.   
Possible values:  
  
0 = 'Absolute' ( Absolute )  
In absolute mode, the [live.slider](</reference/live.slider>) object will automatically jump directly to the clicked location.   
  
1 = 'Relative' ( Relative )  
In relative mode (the default), the [live.slider](</reference/live.slider>) object keeps its relative position when you click on it. Moving the mouse outputs higher or lower values in relation to that relative position.   


### 

showname[int]: 1

The word  showname , followed by the number 1 or 0, shows or hides the parameter name. 

### 

shownumber[int]: 1

The word  shownumber , followed by the number 1 or 0, shows or hides the parameter value. 

### 

slidercolor[4 floats]

Sets the slider color of the [live.slider](</reference/live.slider>) objectin RGBA format. 

### 

textcolor[4 floats]

Sets the display color for the [live.slider](</reference/live.slider>) object's text in RGBA format. 

### 

tribordercolor[4 floats]

Sets the triangle border color in RGBA format. This is only used when the [live.slider](</reference/live.slider>) object does not have the focus. 

### 

tricolor[4 floats]

Sets the triangle color in RGBA format. This is only used when the [live.slider](</reference/live.slider>) object does not have the focus. 

### 

trioncolor[4 floats]

Sets the triangle color in RGBA format. This is only used when the [live.slider](</reference/live.slider>) object does have the focus. 

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

### Parameter Attributes

### 

Orderint

Sets the order of recall of this parameter. Lower numbers are recalled first. The order of recall of parameters with the same order number is undefined. 

### 

Parameter Mode Enableint

Parameter Mode Enable (not available from Parameters window) 

### 

Link to Scripting Nameint

When checked, the Scripting Name is linked to the Long Name attribute. 

### 

Long Namesymbol

The long name of the parameter. This name must be unique per patcher hierarchy. 

### 

Short Namesymbol

Sets the short name for the object's visual display. The maximum length varies according to letter width, but is generally in a range of 5 to 7 characters. 

### 

Typeint

Specifies the data type. The data types used in Max for Live are:   
  
Float   
Int   
Enum (enumerated list)   
Blob   
  
Note: By convention, the Live application uses floating point numbers for its calculations; the native integer representation is limited to 256 values, with a default range of 0-255 (similar to the char data type used in Jitter). When working with Live UI objects whose integer values will exceed this range, the Type attribute should be set to Float, and the Unit Style attribute should be set to Int. 

### 

Range/Enumlist

When used with an integer or floating point data type, this field is used to specify the minimum and maximum values of the parameter.   
When used with an enumerated list (Enum) data type, this field contains a space-delimited list of the enumerated values (if list items contain a space or special characters, the name should be enclosed in double quotes). 

### 

Clip Modulation Modeint

Sets the Clip Modulation Mode used by the Live application. The modulation modes are:   
  
None   
Unipolar   
Bipolar   
Additive   
Absolute   
  


### 

Clip Modulation Rangelist

This parameter is only used with the Absolute modulation mode. It specifies defines the range of values used. 

### 

Initial Enableint

When checked (set to 1), the UI object can store an initialization value. The value is set using the Initial attribute (see below). 

### 

Initiallist

Sets the initial value to be stored and used when the Initial Enable attribute is checked. 

### 

Unit Styleint

Sets the unit style to be used when displaying values. The unit style values are: Int: displays integer values   
Float: displays floating point values   
Time: displays time values in milliseconds (ms)   
Hertz: displays frequency values (Hz/kHz).   
deciBel: displays loudness (dB)   
%: Percentage   
Pan: displays Left and Right values   
Semitones: displays steps (st)   
MIDI: displays pitch corresponding to the MIDI note number   
Custom: displays custom data type   
Native: defaults to floating point values 

### 

Custom Unitssymbol

Sets the units to be used with the 'Custom' unit style (see "Unit Style", above). Custom unit strings may be simple symbols (e.g. "Harmonic(s)"), in which case the parameter's value will be displayed in its 'Native' display mode, followed by the symbol (e.g. "12 Harmonic(s)" for an Int-typed parameter or "12.54 Harmonic(s)" for a Float-typed parameter). For additional control over the numerical component displayed, a sprintf-style string may be used (e.g. "%0.2f Bogon(s)", which would display a value such as ".87 Bogons"). 

### 

Exponentfloat

When set to a value other than 1., the parameter's input and output values will be exponentially scaled according to the factor entered in this column. 

### 

Stepsint

The number of steps available between the minimum and maximum values of a parameter. For instance, if the parameter has a range from 0.-64., with Steps set to 4, the user can only set the parameter to 0, 21.33, 42.66 and 64. 

### 

Control Surface Button Modesymbol

The behavior of control surface buttons, when the parameter is assigned with the [live.banks](</reference/live.banks>) object. Currently available modes are:   
Toggle : switches between minimum and maximum value (default)   
Trigger : outputs the maximum value, immediately followed by the minimum value   
Cycle : cycles through available enum values 

### 

Parameter Visibilityint

For automatable parameters (Int, Float, Enum), 'Stored Only' disables automation, although parameter values are stored in presets. 'Hidden' causes the parameter's value to be ignored when storing and recalling data. Non-automatable parameters (Blob) are 'Stored Only' by default, and can be set to 'Hidden', if desired. The 'Visible' and 'Visible (Not Stored)' visibility modes expose parameters to Live, but don't support automation. Practically, this means that they are visible to Push (and other control surfaces), but won't appear in Live's automation view. The 'Visible' mode also causes Live to store the parameter's value in presets and with the set for later restore. 'Visible (Not Stored)' does not store the value (useful for momentary controls). Note that these modes are only available for Float, Int and Enum parameter types. When using these 'Visible' modes, a new parameter attribute will become available in the object's inspector: 'Undo When Visible'. This is on by default, but when disabled, a Visible parameter becomes invisible to Live's Undo system. 

### 

Undo When Visibleint

When using the 'Visible' modes (see 'Parameter Visibility'), a this attribute is available in the object's inspector. It is on by default, but when disabled, a Visible parameter becomes invisible to Live's Undo system. 

### 

Update Limit (ms)int

Speed limits values triggered by automation. 

### 

Defer Automation Outputint

Defers values triggered by automation. 

## Messages

### 

bang

Sends the current value out the outlet. 

### 

int

The number received in the inlet is stored and displayed by the [live.slider](</reference/live.slider>) object and sent out the outlet. 

Arguments:

  * input [int]   




### 

float

The number received in the inlet is stored and displayed by the [live.slider](</reference/live.slider>) object and sent out the outlet. 

Arguments:

  * input [float]   




### 

assign

The word  assign , followed by a floating point value, causes that value to be displayed and sent out the [live.slider](</reference/live.slider>) object's outlet. The value, however, will not be stored. If the Parameter Visibility attribute is set to Stored Only, the  assign  message will not add the new value to the Live application’s undo chain. 

Arguments:

  * assign-input [float]   




### 

init

Restore and output the initial value. 

### 

(mouse)

Click and drag in the slider to change the value. Hold down the Shift key for more precise mouse control. 

### 

outputvalue

Sends the current value out the outlet. 

### 

rawfloat

A raw normalized value (between 0. and 1.) received in the inlet is converted to a real value, stored, displayed by [live.slider](</reference/live.slider>), and the current value is sent out the outlet. 

Arguments:

  * input [float]   




### 

set

Sets and displays the current value without triggering any output. 

Arguments:

  * set-input [float]   




## Output

### 

float

Out right outlet: when an output is triggered, a raw normalized value (between 0. and 1.) is sent out this outlet. 

### 

int/float

Out left outlet: Numbers received in the inlet or produced by clicking or dragging on [live.slider](</reference/live.slider>) with the mouse are sent out the outlet. The value sent is an integer if the  Parameter Type  is set to  INT  or  ENUM . 

## See Also

Name | Description  
---|---  
[live.numbox](</reference/live.numbox>) |  Display and output a number   
[live.dial](</reference/live.dial>) |  Output numbers by moving a dial onscreen   
[live.slider](</reference/live.slider>) |  Output numbers by moving a slider onscreen

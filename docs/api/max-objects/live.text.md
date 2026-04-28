> **Source**: https://docs.cycling74.com/reference/live.text/  
> **Fetched**: 2026-04-27  

_Package Max for Live_

# live.text

A user interface button/toggle 

## Description

[live.text](</reference/live.text>) object is a user interface object used to create buttons and toggles. 

## Arguments

None.

## Attributes

### 

active[int]: 1

Toggles the object's active mode. When  active  is set to 0, the mouse action does not cause output and the inactive colors are used. 

### 

activebgcolor[4 floats]

Sets the background color off displayed when the  active  attribute is set to 1. 

### 

activebgoncolor[4 floats]

Sets the background color on displayed when the  active  attribute is set to 1. 

### 

activetextcolor[4 floats]

Sets the display color for the [live.text](</reference/live.text>) object's text in RGBA format. 

### 

activetextoncolor[4 floats]

Sets the display color for the [live.text](</reference/live.text>) object's text when it is on. 

### 

annotation_name[symbol]: 

The string that is prepended to annotations. This shows up in the Info pane in Live, and the clue window in Max. 

### 

appearance[int]: 0

Defines the display style. The options are:   
  
0: Default. The text appears with the boundaries of the text box.   
1: Label. The text box appears as a square button, with the text appearing to the right.   
2: LCD. The text appears with the boundaries of the text box.   
Possible values:  
  
0 = 'Default'   
1 = 'Label'   
2 = 'LCD' 

### 

automation[symbol]: val1

Sets the automation "off" label that will appear in Live. 

### 

automationon[symbol]: val2

Sets the automation on label that will appear in Live. 

### 

bgcolor[4 floats]

Sets the background color "off" displayed when the  active  attribute is set to 0. 

### 

bgoncolor[4 floats]

Sets the background color on displayed when the  active  attribute is set to 0. 

### 

blinktime[int]: 100

Blink Time in Milliseconds 

### 

bordercolor[4 floats]

Sets the display color for the [live.text](</reference/live.text>) object's border in RGBA format. 

### 

focusbordercolor[4 floats]

Sets the display color for the [live.text](</reference/live.text>) object's border in RGBA format. 

### 

inactivelcdcolor[4 floats]

>= 8.0.0

Sets the display color in the RGBA format for the [live.text](</reference/live.text>) object in LCD mode when the  active  attribute is set to 0. In the off state this sets the text color, while in the on state it sets the background color. 

### 

labeltextcolor[4 floats]

>= 8.0.0

Sets the display color for the [live.text](</reference/live.text>) object's text when it is in the label display mode. 

### 

lcdbgcolor[4 floats]

>= 8.0.0

Sets the display color in the RGBA format for the [live.text](</reference/live.text>) object in LCD mode. In the off state this sets the background color, while in the on state it sets the text color. 

### 

lcdcolor[4 floats]

>= 8.0.0

Sets the display color in the RGBA format for the [live.text](</reference/live.text>) object in LCD mode when the  active  attribute is set to 1. In the off state this sets the text color, while in the on state it sets the background color. 

### 

mode[int]: 1

Sets the button mode. Button modes are:   
  
0: Button mode   
1: Toggle (switch) mode   
Possible values:  
  
0 = 'Button'   
1 = 'Toggle' 

### 

outputmode[int]: 0

>= 8.0.0

Sets the output mode for the [live.text](</reference/live.text>) object when it's  mode  attribute is set to 1 (toggle). When  outputmode  is set to 0, output occurs on mousedown, when set to 1, output occurs on mouseup.   
Possible values:  
  
0 = 'Mouse down'   
1 = 'Mouse up' 

### 

param_connect[symbol]: 

Establishes a two-way connection between the object and a parameter of a compatible object with parameters such as [gen~](</reference/gen~>) or [jit.gl.slab](</reference/jit.gl.slab>). The object can be used to change the value of the parameter and will update if the parameter value changes. The easiest way to set param_connect is with the attribute's menu in the [inspector](</userguide/inspector>) or the Connect submenu of the [Object Action menu](</userguide/action_menu>). The menu displays all available parameters of compatible objects.   
  
Setting the param_connect attribute with a message requires the target parameter's path, which is the host object's scriping name followed by two colons and the parameter name. For example, for a [gen~](</reference/gen~>) object with scripting name  gen~_AB , the path of the  freq  parameter would be  gen~_AB::freq . You can set a value for the param_connect before the host object or parameter exists, and the object will connect to the parameter once it exists. Refer to the user guide entry for [param_connect](</userguide/param_connect>) for more details. 

### 

parameter_mappable[int]: 1

When parameter_mappable is enabled, the object will be available for mapping to keyboard or MIDI input using the [Mappings feature](</userguide/mapping>). 

### 

pictures[2 symbols]: <none> <none>

Sets the paths for pictures used when the  usepicture  attribute is set to 1. Bitmap images such as PNG or vectorized images (SVG) can be used. 

### 

remapsvgcolors[int]: 0

>= 8.0.0

Sets the SVG image colors to use when drawing the image. If  remapsvgcolors  is set to 0, the colors supplied by the SVG file are used; if set to 1, the color attributes for the appropriate display mode are used. 

### 

rounded[float]

Set the roundness of the border 

### 

text[symbol]: A

Sets the button label when the button is in the off state. 

### 

textcolor[4 floats]

Sets the display color for the [live.text](</reference/live.text>) object's text when the  active  attribute is set to 0. 

### 

textoffcolor[4 floats]

>= 8.0.0

Sets the display color for the [live.text](</reference/live.text>) object's text when it is in the off state and the  active  attribute is set to 0. 

### 

texton[symbol]: B

Sets the button label when the button is in the "on" state. 

### 

transition[int]: 0

The parameter automation of [live.text](</reference/live.text>) stores 0 and 1 values. The  transition  attribute specifies when a  bang  will be sent to the outlet.   
Possible values:  
  
0 = 'Zero->One'   
1 = 'One->Zero'   
2 = 'Both' 

### 

usepicture[int]: 0

Toggles the use of pictures instead of text for display. Note that you need to provide enough pictures by setting the  pictures  attribute properly. 

### 

usesvgviewbox[int]: 0

>= 8.0.0

Sets the viewbox for the svg files when  usepicture  is set to 1. If  usesvgviewbox  is set to 0, Max determines the viewbox; if set to 1, uses the viewbox flag supplied by the svg file. 

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

A bang message will toggle the state of the object. If it is off, it will switch on and output a 1. If it is on, it will switch off and output a 0. 

### 

int

In the  toggle  mode, any non-zero number will toggle the button to the "on" position, send the button text out the middle outlet and send a 1 out the left outlet. A zero sets the toggle to the "off" position, sends the button text out the middle outlet and sends a 0 out the left outlet. 

Arguments:

  * input [int]   




### 

float

Converted to  int . 

Arguments:

  * input [float]   




### 

assign

The word  assign , followed by a floating point value, causes that value to be displayed and sent out the [live.text](</reference/live.text>) object's outlet. The value, however, will not be stored. If the Parameter Visibility attribute is set to Stored Only, the  assign  message will not add the new value to the Live application’s undo chain. 

Arguments:

  * assign-input [float]   




### 

init

Restore and output the initial value. 

### 

(mouse)

In  button  mode, a mouse click on [live.text](</reference/live.text>) highlights it for as long as the mouse is held down, sending the text out the second outlet and a  bang  message out the left outlet.   
In  toggle  mode, a mouse click behaves the same as a [live.toggle](</reference/live.toggle>). When the mouse is clicked, the [live.text](</reference/live.text>) object will send a 1 out the left outlet if the cursor is inside of the [live.text](</reference/live.text>) object's rectangle, and a 0 if it is not. The button text is also sent out the second outlet on mouse click. 

### 

outputvalue

Sends the current value out the outlet. 

### 

rawfloat

A raw normalized value (between 0. and 1.) received in the inlet is converted to a real value, and then functions like any other received int value in toggle mode. 

Arguments:

  * input-value [float]   




### 

set

In the  toggle  mode, the  set  messages toggles the "on" or "off" state without sending anything out the outlets. The word  set , followed by any non-zero number, sets toggle to on. The message  set 0  sets it to "off". 

Arguments:

  * set-input [float]   




### 

setsymbol

In the  toggle  mode, the word  setsymbol , followed by a symbol that specifies a button text item, causes [live.text](</reference/live.text>) to display that symbol and act as though the object were toggled to that state. 

Arguments:

  * button-text-item [list]   




### 

symbol

In the  toggle  mode, the word  symbol , followed by a symbol that specifies a button text item, causes [live.text](</reference/live.text>) to display that symbol and sends the current values out the outlets. 

Arguments:

  * button-text-item [list]   




## See Also

Name | Description  
---|---  
[live.button](</reference/live.button>) |  Flash on any message, send a bang   
[live.tab](</reference/live.tab>) |  A user interface tab/multiple button object in the style of Ableton Live.   
[live.toggle](</reference/live.toggle>) |  Switch between off and on (0/1)   
[textbutton](</reference/textbutton>) |  Button with text

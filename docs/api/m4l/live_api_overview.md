> **Source**: https://docs.cycling74.com/userguide/m4l/live_api_overview/  
> **Fetched**: 2026-04-27  

# Live API Overview

Besides building new instruments and effects to be used in Live, Max For Live also allows to access Live itself, its tracks, clips, devices and hardware control surfaces. This chapter defines some basic terms used throughout the whole Live API and introduces the Max objects representing the Live API.

## Live Object Model

The accessible parts of Live are represented by a hierarchy of objects called the _Live Object Model (LOM)_.

The model describes the hierarchy of objects inside Live, as seen from the Max devices. There are various types of objects in the model, like `Track` or `Clip`. For certain objects only a single instance exists, for other multiple instances are held in lists.

The [Live Object Model reference](</apiref/lom/>) shows how to navigate from a number of root objects down a path to the particular object of interest, and what to do with it. Not all of Live's parameters are accessible via Live's API, the reference should give you an idea of what can and can't be done via Max for Live.

## Object Path

Live objects are accessed using paths according to the Live Object Model. For example, the first clip in the third track can be accessed by the path `live_set tracks 2 clip_slots 0 clip`. Alternatively, it can be accessed via `live_set scenes 0 clip_slots 2 clip`. Or, if the clip is shown in the detail view, via `live_set view detail_clip`.

As you can see, different paths can point to the same Live object. Only one of these paths is the _canonical path_ (see below).

When communicating with the Live API, no quotes are used in paths. List indexes start with 0.

When navigating through the object model, besides these _absolute_ paths, _relative_ paths can be used. These determine a subpath beginning at the current position in the object hierarchy.

## Root objects

(Absolute) paths to all objects start with one of `live_app`, `live_set`, `control_surfaces N` or `this_device`. These are the _root_ objects.

`live_app` : allows you to access controls of the Live application itself. This can be useful if you want to toggle the browser view, zoom or scroll features in Live. `live_set` : allows you to access various parameters within Live, for example Track Volume, Clip parameters (including launching Clips), etc. `control_surfaces` : allows you to access various control surface features (depending on your controller). `this_device` : allows you to construct API paths relative to the device you are in.

## Canonical Path

Different paths can lead to the same object. `live_set view selected_track` and `live_set tracks 3` are the same object if the fourth track is selected.

Each object has a unique canonical path, `live_set tracks 3` in this case. The canonical path is sent out of [live.object](</reference/live.object> "live.object") in reponse to `getpath`. In the Live Object Model, the canonical path is shown by bold connectors.

## Canonical Parent

Additionally to what is described in the LOM, all objects have a `canonical_parent` child which is used by Live to determine the canonical path of an object. The canonical parents are get-only and useful for patching, too. For example, `goto this_device canonical_parent` is the perfect way to get the own track object.

## Object ids

An object id identifies a particular object instance in Live like a track or a clip.

To get an id, a [live.path](</reference/live.path> "live.path") object must be used to navigate to the Live object. When a [live.path](</reference/live.path> "live.path") object sees this Live object the first time, an id is assigned to it.

The id is only valid inside the device with the [live.path](</reference/live.path> "live.path") and remains unchanged as long the object exists. If the object is moved in Live, its id usually remains unchanged. There may be exceptions if the movement is implemented as a delete/create sequence, though. When an object is deleted and a new object is created at its place, it will get a new id.

An id is never reused in the scope of a Max device. Ids are not stored. Therefore, after loading a saved device, the [live.path](</reference/live.path> "live.path") object must navigate to the object again.

An object id consists of the word `id` and a number, separated by a space, like `id 3`. `id 0` refers to _no object_. In Max terms it's a list of the symbol `id` and an integer.

## Object Types

Each Live object is of a particular object type (or _class_), like `Track` or `Clip`. This object type determines what kind of object that is and what children, properties and functions it has. The object types are described in detail in the Live Object Model.

When [live.object](</reference/live.object> "live.object") refers to a Live object, sending it `getinfo` will send all the Live object's children, properties and functions to its left outlet.

## Children

Live objects have children identified by name. Some names, like `master_track` for the `Song` object type, point to single objects. Others, like `scenes`, point to a list of objects. The child name hints at which object type you can expect to find there.

List names are in plural, whereas single child names are in singular. Lists may be empty. Sending `getcount child_name` to [live.path](</reference/live.path> "live.path") allows to find out how many children are in the list.

Single children names may point to no object, in which case you get `id 0` if you navigate there or send `get child_name` to [live.object](</reference/live.object> "live.object").

Most children can be monitored using [live.observer](</reference/live.observer> "live.observer").

## Properties

Live objects have properties which describe its actual state. Properties are accessed by sending `get` and `set` messages to [live.object](</reference/live.object> "live.object"). Not all properties can be set, though.

Many properties can be monitored using [live.observer](</reference/live.observer> "live.observer").

## Functions

Many Live objects have functions which can be called by sending `call` and the function name to [live.object](</reference/live.object> "live.object"), like `call create_scene` for a `Song` object. A function call may have parameters (a list of values). The return value will be sent out from the outlet of [live.object](</reference/live.object> "live.object").

## Datatypes

Properties and function parameters or return values used in the Live Object Model and by the Max objects to access the Live API have one of the following data types:

Datatype| Description  
---|---  
bool| 0 for false and 1 for true  
symbol| a string with unicode character setUse double quotes in message boxes to create symbols with spaces: `set name "Smooth Synth"` Double quotes in symbols are to be _prefixed_ by backslashes: `set name "Smooth \"Baby\" Synth"` Backslashes are to be included as double backslashes: `alpha beta \"gamma\" \\x\\` creates the symbol `alpha beta "gamma" \x\`.  
int| a 32 bit signed integer  
float| a 32 bit float value  
double| a 64 bit float value (maily used for timing values)  
beats| song beat time counted in quarter notes, represented as double  
time| song time in seconds, represented as doubleTime is given in seconds: `time = beats * 60 / tempo_in_bpm`, or sometimes in milliseconds: `time = 1000 * beats * 60 / tempo_in_bpm`  
list| a space separated list of the types above  
  
## Notifications

When Max devices need to know the state of the Live application and its objects, they can actively poll the state by navigating through the object hierarchy and getting object properties or calling functions.

But changes happen in Live while the Max device is passive. To allow the Max device to react on these changes in Live, notifications are sent from Live to the Max device. Notifications are spontaneous in the sense that messages are sent to outlets spontaneously, _not_ in response to a message received at an inlet.

The notifications include object ids sent when the Live object at a certain path changes and values sent when a property changes.

Note: changes to a Live Set and its contents are not possible from a notification. The error message in the Max Console is 'Changes cannot betriggered by notifications'. In many cases putting a [deferlow](</reference/deferlow/> "deferlow") between the notification outlet and the actual change helps to resolve the issue.

## Max Objects

Four Max objects interact in a certain way to allow Max devices to access the Live objects.

Max object| Purpose  
---|---  
[live.path](</reference/live.path> "live.path")| select objects in the Live object hierarchy  
[live.object](</reference/live.object> "live.object")| get and set properties and children, call functions  
[live.observer](</reference/live.observer> "live.observer")| monitor properties and children  
[live.remote~](</reference/live.remote~> "live.remote~")| control Live device parameters in real time  
  
The following patch shows the typical interconnections between the Live API objects. [live.path](</reference/live.path> "live.path") is sending object ids out of its leftmost outlet connected to the rightmost inlet of [live.object](</reference/live.object> "live.object"), [live.observer](</reference/live.observer> "live.observer") and [live.remote~](</reference/live.remote~> "live.remote~"). This causes these objects to operate on the object selected by [live.path](</reference/live.path> "live.path").

### live.path

[live.path](</reference/live.path> "live.path") objects are used to navigate to the Live objects on which [live.object](</reference/live.object> "live.object"), [live.observer](</reference/live.observer> "live.observer") and [live.remote~](</reference/live.remote~> "live.remote~") are supposed to operate. For this purpose, navigation messages like `goto live_set` are sent to [live.path](</reference/live.path> "live.path"), which replies by sending an object id to the left outlet.

[live.path](</reference/live.path> "live.path") can also observe the given path, and when the object at this path changes, its id is sent to the middle outlet. This is particularly useful for paths like `live_set view selected_track` which point to the currently selected track.

### live.object

[live.object](</reference/live.object> "live.object") is used to operate on a particular Live object which id has been received from [live.path](</reference/live.path> "live.path"). It allows to get or set properties of the Live object and to call its functions with parameters.

### live.observer

[live.observer](</reference/live.observer> "live.observer") monitors the state of a particular Live object which id has been received from [live.path](</reference/live.path> "live.path"). After telling [live.observer](</reference/live.observer> "live.observer") which property to observe it recognizes all changes of the property and sends the current values to its left outlet.

### live.remote~

[live.remote~](</reference/live.remote~> "live.remote~") receives the id of a DeviceParameter object from [live.path](</reference/live.path> "live.path") and then allows to feed this parameter with new values by sending them into the left inlet, in realtime, without effects on the undo history or the parameter automation, which is deactivated.

DeviceParameter objects are children of Live devices, including Max devices, and also of tracks, like volume and pan.

## LiveAPI

The [Live API](</apiref/js/liveapi/>) Javascript object is available in code written for the [js](</reference/js/> "js") object. It provides a succinct means of communicating with the Live API functions from JavaScript, incorporating the functionality provided by the [live.path](</reference/live.path> "live.path"), [live.object](</reference/live.object> "live.object") and [live.observer](</reference/live.observer> "live.observer") objects.

## Examples

Here are some examples of accessing Live from Max.

### Controlling the volume slider of the selected track

#### Getting the volume of a track

To get the volume of a track in Live, we first need to find the path to the volume parameter of the track's mixer device.

In the [Live Object Model reference](</apiref/lom/>), the graph can be navigated starting at the `live_set` root node. From the `Song` object, we use `tracks` to get the list of `Track` children. We select the second track with `1` (note that indexing starts at 0). We then use `mixer_device` to get its `MixerDevice` object, and finally by using `volume`, we get to the volume `DeviceParameter` object.

We can now send this path to a [live.path](</reference/live.path> "live.path") with the following message: `path live_set tracks 1 mixer_device volume`. [live.path](</reference/live.path> "live.path") will give us back `id n` (where n is an integer), which represents the `DeviceParameter` object we need. It gives us access to the properties of the mixer device's volume control, like its range (`min` and `max`), default value (`default_value`) or current value (`value`).

When we send this id to the right inlet of a [live.object](</reference/live.object> "live.object"), we can get the properties of the DeviceParameter object with `get` messages. By sending `get value` to the [live.object](</reference/live.object> "live.object"), it will send the current volume value to its left outlet as a number between 0 and 1.

#### Initializing a path when the device loads

If we want to make sure the [live.object](</reference/live.object> "live.object") is set to the path we specified as soon as the device is loaded, we might be tempted to use [loadbang](</reference/loadbang/> "loadbang") to send the `path` message to [live.path](</reference/live.path> "live.path"). It is important to know that we need to use [live.thisdevice](</reference/live.thisdevice> "live.thisdevice") instead, to make sure the Live API is initialized before interacting with it.

#### Getting the volume of the _selected_ track

In the previous example we hard-coded getting the volume value of the second track. However, if we would like to get the value of the _selected_ track, we can use the `selected_track` child of the Song View instead.

After finding the `selected_track` keyword in the [Live Object Model reference](</apiref/lom/>), we see that it is a child of `Song.View`. In the graph we see that the `Song.View` can be reached from the `Song` object type with the `view` keyword. So we send the following message to [live.path](</reference/live.path> "live.path") : `path live_set view selected_track mixer_device volume`. This will send the id of the currently selected track to the left outlet, which we send to [live.object](</reference/live.object> "live.object").

#### Knowing when a different track is selected

In the previous example, we got the id of the selected track once. However, if we select a different track, this id is no longer up to date. If we want the id from a path containing a dynamic element like `selected_track` to stay up to date, we can use the second outlet of [live.path](</reference/live.path> "live.path").

Hovering the mouse cursor over the outlets over an object will show you what they send out. The second outlet of [live.path](</reference/live.path> "live.path") reads `id: follows path`. When instead of the [live.path](</reference/live.path> "live.path") 's left outlet we connect its second outlet to [live.object](</reference/live.object> "live.object"), the [live.object](</reference/live.object> "live.object") will be kept up to date, even after selecting a different track.

**There is one catch** , as mentioned under Notifications. Since the second outlet of [live.path](</reference/live.path> "live.path") sends us notifications from Live, when we connect it to another Live API object like [live.object](</reference/live.object> "live.object"), we need to add a [deferlow](</reference/deferlow/> "deferlow") in-between to make sure the next API interaction is not attempted before the first is finished.

#### Setting the volume of a track

In much the same way as getting the current volume of a track like above, we can also _change_ the value of a volume fader.

We can add a slider with a range between 0 and 1, connected to a message box saying `set value $1`. We can then connect this to the [live.object](</reference/live.object> "live.object") as set up above, and now our slider will control the volume slider in Live.

#### Observing the volume of a track

We might want to get an update in our device whenever a Live user changes a volume slider. For this, we can send the id from the previously set up [live.path](</reference/live.path> "live.path") to a [live.observer](</reference/live.observer> "live.observer") that has its argument set to the property `value`. Now, the up to date volume values will be output from the [live.observer](</reference/live.observer> "live.observer") 's left outlet.

Finally, we can set this value to the slider we created earlier. We now have a device with a slider that mimics and changes the volume slider of the selected track in Live.

### Triggering a clip with MIDI notes

#### Navigating to a specific clip and triggering it

Apart from children and properties, Live objects also have _functions_. Looking at the [Live Object Model reference](</apiref/lom/>), under `Clip`, in the Functions section, we can find the `fire` function. To call this function, we first need to refer a [live.object](</reference/live.object> "live.object") to the clip we want to launch. For this, we need the clip's id.

Getting an id is done with [live.path](</reference/live.path> "live.path"). Finding out what path to supply is most easily done by looking at the LOM graph. In the graph, we find the `Clip` object. To reach it, we start at the Song root node (`live_set`), go to its list of `Track` children and pick the first (`track 0`). Next we go to the list of `ClipSlot` children and pick, for example, the fourth (`clip_slots 3`), and finally we navigate to the `Clip` contained by this clip slot (`clip`). So the message we send to [live.path](</reference/live.path> "live.path") will be `path live_set tracks 0 clip_slots 3 clip`.

We send the id output from the left outlet of [live.path](</reference/live.path> "live.path") to [live.object](</reference/live.object> "live.object") 's second inlet. There are no dynamic elements in the path, so we don't need to use [live.path](</reference/live.path> "live.path") 's second outlet. And now that we are ready to launch the clip, we simply send `call fire` to the left inlet of the [live.object](</reference/live.object> "live.object").

#### Adding control of which clip to fire and checking if it exists

We might want to use two [live.numbox](</reference/live.numbox> "live.numbox") es to control the track number and the clip slot number that we want to launch. The outputs of the numboxes can be sent to [pak](</reference/pak/> "pak") and we can swap the hardcoded numbers in the path above with replaceable arguments: `path live_set track $1 clip_slots $2 clip`.

Of course, with this approach, the user of this device will be able to select tracks or clip slots that don't exist in the Live set. To show a toggle that is on when the selection exists and off otherwise, we can use that `id 0` is output for paths that don't exist.

Finally, to make this a functional device, we can place this patch in a MIDI effect and use [notein](</reference/notein/> "notein") to trigger the selected clip. If the velocity is not 0, we know a note on comes in. So then, if the selected clip exists, we send `call fire` to it.

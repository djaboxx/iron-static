> **Source**: https://docs.cycling74.com/userguide/m4l/live_api/  
> **Fetched**: 2026-04-27  

# Creating Devices that use the Live API

Max for Live provides two different ways to access the Live application directly through the Live API:

  * You can use a trio of Max for Live objects - ([live.object](</reference/live.object> "live.object"), [live.observer](</reference/live.observer> "live.observer"), and [live.path](</reference/live.path> "live.path")) to access, observe, and control the Live application.

  * You can use the Max [js](</reference/js/> "js") object to write code using the [Live API](</apiref/js/liveapi/>) Javascript object that exposes the [Live Object Model](</apiref/lom/>).




Regardless of which method you decide to use, online documentation for the [Live Object Model](</apiref/lom/>) describes the properties and functions of a Live session that can be queried and set and observed. You can get or set values, call functions, and observe the status of properties using the Live API from any kind of Max for Live device on any channel. The Live API is described in [this overview](</userguide/m4l/live_api_overview/>).

The Live Object Model divides the Live application into several basic functional units (_properties_) associated with aspects of the Live application - the application itself, Songs, Tracks, Clip slots, Clips, Devices, Device Parameters, the Mixer Device, Scenes, Cue Points, And Control Surfaces. The Live API provides ways to access some properties of the application to control how the Live application displays them to you (Application.View, Song.View, and Track.View). Your use of the Live API involves one of four kinds of different operations:

  * You can query (_get_) the current state of a property of your current Live session.

  * You can _set_ the state of some properties of your current Live session

  * Some properties can be controlled using _functions_ that perform various actions (e.g. firing a clip).

  * Some properties can be _observed_ (i.e. their current state is reported and updated automatically). The [Live Object Model](</apiref/lom/>) provides a complete reference to which objects can be queried, set, and observed, as well as a listing of the functions associated with them.




## Querying the Live API (getting data) using Max for Live objects

You can use the Max for Live [live.path](</reference/live.path> "live.path") and [live.object](</reference/live.object> "live.object") objects to find out the current state of any property defined in the Live Object Model reference.

The [live.path](</reference/live.path> "live.path") object is used to navigate to the Live object properties you wish to query. Each property of the Live object model in a session is associated with an id specific to that particular Song, Track, Clip, Clip Slot, Device, etc. Sending a message to a [live.path](</reference/live.path> "live.path") object results in an object id being sent out the left outout (where the id follows the object) or middle outlet (where the id follows the path). In turn, the [live.object](</reference/live.object> "live.object") object takes the id message from the [live.path](</reference/live.path> "live.path") object and lets you use `get` messages to get information about the properties of the object. The result of the query is sent out the outlet of the [live.object](</reference/live.object> "live.object") object, preceded by the name of the query.

## Querying the Live API

  * Using the Live Object Model, find the canonical path listing for the property (in this case, the Track properties). This part of the Live Object Model listing displays its canonical path - the syntax for queries about the Track in a Live session.



  * Find the listing in the Live Object Model page for the query you want to make (in this example, we want to to see whether or not Track 3 is muted).



The listing from the Live Object Model listing for the `mute` property of a Live Track lists its Type as _bool_ (boolean, 0 = off, 1 = on), and its Access as _get, set, observe_ , which means that this property can be queried or set or observed (there's also an indication that Live Master Tracks cannot be queried or set).

  * Use a[message box](</reference/message/>)to construct a message to be sent to the [live.path](</reference/live.path> "live.path") object telling it the name of the property we want to query - Track 3 (by convention, track numbering in the Live API starts from 0). In this case, the message is `path live_set tracks 2` .



The [live.path](</reference/live.path> "live.path") object responds with the message `id N`, where _N_ is the id number associated with Track 3.

  * use a Max [trigger](</reference/trigger/> "trigger") object to set up a sequence of operations. When the [trigger](</reference/trigger/> "trigger") object receives the list output, it sends the id message to the [live.object](</reference/live.object> "live.object") object's right inlet, and then sends a bang message to the[message box](</reference/message/>)containing the symbol `get`, followed by the name of the property being queried. In response, the [live.object](</reference/live.object> "live.object") object sends the message `mute 0` out the left outlet of the [live.object](</reference/live.object> "live.object") object



## Setting a property in the Live API using Max for Live objects

You can also use the Max for Live [live.path](</reference/live.path> "live.path") and [live.object](</reference/live.object> "live.object") objects to set the current state of many properties defined in the Live Object Model reference. The [live.path](</reference/live.path> "live.path") object is used to navigate to the Live objects you wish to query. Each property of the Live object model in a session is associated with an id specific to that particular Song, Track, Clip, Clip Slot, Device, etc. Sending a message to a [live.path](</reference/live.path> "live.path") object results in an object id being sent out the left outout (where the id follows the object) or middle outlet (where the id follows the path). In turn, the [live.object](</reference/live.object> "live.object") object takes the id message from the [live.path](</reference/live.path> "live.path") object and lets you use `set` messages, followed by arguments that specify the new setting to set the state of a property. In this example, we'll use a `set` message to mute Track 3 of a Live session.

## Setting a Live API property

  * Using the Live Object Model, find the canonical path listing for the property (in this case, the Track properties). This part of the Live Object Model listing displays its canonical path - the syntax for queries about the Track in a Live session.



  * Find the listing in the Live Object Model page for the query you want to make (in this example, we want to to see whether or not Track 3 is muted).



The listing from the Live Object Model listing for the `mute` property of a Live Track lists its Type as _bool_ (boolean, 0 = off, 1 = on), and its Access as _get, set, observe_ , which means that this property can be set as well as queried and observed (there's also an indication that Live Master Tracks cannot be queried or set).

  * Use a[message box](</reference/message/>)to construct a message to be sent to the [live.path](</reference/live.path> "live.path") object telling it the name of the property we want to query - Track 3 (by convention, track numbering in the Live API starts from 0). In this case, the message is `path live_set tracks 3` .



The [live.path](</reference/live.path> "live.path") object responds with the message `id N`, where _N_ is the id number associated with Track 3.

  * Use a Max [trigger](</reference/trigger/> "trigger") object to set up a sequence of operations. When the [trigger](</reference/trigger/> "trigger") object receives the list output, it sends the id message to the [live.object](</reference/live.object> "live.object") object's right inlet, and then sends a bang message to the[message box](</reference/message/>)containing the message `set`, followed by the name of the property we want to set and its new value - in this case, `set mute 1` .



When you save and close the device and click on the upper message box, Track 3 will be muted.

## Observing a property in the Live API using Max for Live objects

Some properties in the Live API can be _observed_. The Live API not only reports the current state of a property in response to a query when it is observed, but also subsequently updates the state of that property if it changes. Observing a property using the Live API uses the [live.path](</reference/live.path> "live.path") object also used for getting and setting properties, but also uses the [live.observer](</reference/live.observer> "live.observer") objects to perform the task. The [live.path](</reference/live.path> "live.path") object is used to navigate to the Live objects whose functions you want to call. Each property of the Live object model in a session is associated with an id specific to that particular Song, Track, Clip, Clip Slot, Device, etc. Sending a message to a [live.path](</reference/live.path> "live.path") object results in an object id being sent out the left outout (where the id follows the object) or middle outlet (where the id follows the path). In turn, the [live.observer](</reference/live.observer> "live.observer") object takes the id message from the [live.path](</reference/live.path> "live.path") object and lets you use `property` messages to define what property of the object you want to observe. In this example, we'll observe whether or not Track 3 of our session is muted or not.

## Observing a Live API property

  * Using the Live Object Model, find the canonical path listing for the property (in this case, the Track properties). This part of the Live Object Model listing displays its canonical path - the syntax for queries about the Track in a Live session.



  * Find the listing in the Live Object Model page for the property you wish to observe. Not all properties may be observed via the Live API (in this example, we want to to observe the behavior of muting on Track 3).



The listing from the Live Object Model listing for the `mute` property of a Live Track lists its Type as _bool_ (boolean, 0 = off, 1 = on), and its Access as _get, set, observe_ , which means that this property can be observed (there's also an indication that Live Master Tracks cannot be observed).

  * Use a[message box](</reference/message/>)to construct a message to be sent to the [live.path](</reference/live.path> "live.path") object telling it the name of the property we want to query - Track 3 (by convention, track numbering in the Live API starts from 0). In this case, the message is `path live_set tracks 3` .



The [live.path](</reference/live.path> "live.path") object responds with the message `id N`, where _N_ is the id number associated with Track 3.

  * Use a Max [trigger](</reference/trigger/> "trigger") object to set up a sequence of operations. When the [trigger](</reference/trigger/> "trigger") object receives the list output, it sends the id message to the [live.observer](</reference/live.observer> "live.observer") object's right inlet, and then sends a bang message to the[message box](</reference/message/>)containing the message `property`, followed by the name of the property we want to observe - in this case, `property mute` .



When you save and close the device and click on the upper message box while Track 3 is playing, you'll notice that the patch displays a 0 (unmuted). If you mute the track by clicking on the Track Activator button, you'll see the output of the [live.observer](</reference/live.observer> "live.observer") object change to a 1 (muted). As you unmute and mute the track, the value will change.

## Calling a function in the Live API using Max for Live objects

The Live API also includes various kinds of functions that are used to perform activities such as changing various aspects of the Live application's interface display (View) or controlling the playing of clips or scenes. You can also use the Max for Live [live.path](</reference/live.path> "live.path") and [live.object](</reference/live.object> "live.object") objects to _call_ (perform) these functions. The [live.path](</reference/live.path> "live.path") object is used to navigate to the Live objects whose functions you want to call. Each property of the Live object model in a session is associated with an id specific to that particular Song, Track, Clip, Clip Slot, Device, etc. Sending a message to a [live.path](</reference/live.path> "live.path") object results in an object id being sent out the left outout (where the id follows the object) or middle outlet (where the id follows the path). In turn, the [live.object](</reference/live.object> "live.object") object takes the id message from the [live.path](</reference/live.path> "live.path") object and lets you use `call` messages, followed by arguments that specify the name of the function you're calling and any data for the function in the form of arguments to execute the function. In this example, we'll use a `fire` function to play the clip in slot 2 or Track 2 of a Live session.

## Calling a function of a Live API property

  * Using the Live Object Model, find the canonical path listing for the property (in this case, the ClipSlot properties). This part of the Live Object Model listing displays its canonical path - the syntax for queries about the ClipSlot in a Live session.



  * Find the listing in the Live Object Model page for the property's functions (in this example, we want to fire (launch) the clip in clip slot 2 on Track 2).



The listing from the Live Object Model listing for the `fire` function of the ClipSlot property indicates that it needs no other data arguments.

  * Use a[message box](</reference/message/>)to construct a message to be sent to the [live.path](</reference/live.path> "live.path") object telling it the name of the property we want to query - Clip Slot 2 or Track 2 (by convention, all numbering in the Live API starts from 0). In this case, the message is `path live_set tracks 1 clip_slots 1` .



The [live.path](</reference/live.path> "live.path") object responds with the message `id N`, where _N_ is the id number associated with Clip Slot 2 of Track 2.

  * Use a Max [trigger](</reference/trigger/> "trigger") object to set up a sequence of operations. When the [trigger](</reference/trigger/> "trigger") object receives the list output, it sends the id message to the [live.observer](</reference/live.observer> "live.observer") object's right inlet, and then sends a bang message to the[message box](</reference/message/>)containing the message `call`, followed by the name of the function - in this case, `call fire` .



When you save and close the device and click on the upper message box while Track any other clip in any other clip slot in Track 2 is playing, you'll notice that the clip in Clip Slot 2 is launched.

## Automating device parameters at signal rate

The [live.object](</reference/live.object> "live.object") is designed to mimic user interactions with the Live Session (and adds to undo history), so there are some situations that involve rapid modulation of device parameters where the object may not be appropriate. The [live.remote~](</reference/live.remote~> "live.remote~") object allows you to directly modulate the parameters of any "remotely mappable" control in Live at signal rate. As with setting values and calling functions, the [live.path](</reference/live.path> "live.path") object is used to navigate to the Live objects whose functions you want to control. Each property of the Live object model in a session is associated with an id specific to that particular Song, Track, Clip, Clip Slot, Device, etc. Sending a message to a [live.path](</reference/live.path> "live.path") object results in an object id being sent out the left outout (where the id follows the object) or middle outlet (where the id follows the path). In turn, the [live.remote~](</reference/live.remote~> "live.remote~") object takes the id message from the [live.path](</reference/live.path> "live.path") object and accepts signal data in its left inlet which is used to modulate or control the Live API property. In the following example, we'll use the output of a [cycle~](</reference/cycle~/> "cycle~") object to control the sends on an audio track.

## Controlling a property using the live.remote~ object

  * Using the Live Object Model, find the canonical path listing for the property (in this case, the MixerDevice properties). This part of the Live Object Model listing displays its canonical path - the syntax for queries about the Track in a Live session.



  * Find the listing in the Live Object Model page for the property you wish to control (in this example, we want to to control the first send on Track 1). Remember that numbering in the Live API starts from zero by convention.

  * Use a[message box](</reference/message/>)to construct a message to be sent to the [live.path](</reference/live.path> "live.path") object telling it the name of the property we want to control. In this case, the message is `path live_set tracks 0 mixer_device sends 0` .




The [live.path](</reference/live.path> "live.path") object responds with the message `id N`, where _N_ is the id number associated with the first send on Track 1.

  * Add some logic to produce signal-rate data to control the property. In this case, we're using a [cycle~](</reference/cycle~/> "cycle~") device to use a sinusoidal waveform and then using the [abs~](</reference/abs~/> "abs~") (absolute value) object to keep the output in the positive signal range.



When you save and close the device and click on the upper message box while Track 1 is playing, you'll notice that the dial for Send A on Track one moves at the rate you specify for the [cycle~](</reference/cycle~/> "cycle~") object.

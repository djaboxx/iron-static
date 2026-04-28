# 36. Synchronizing with Link, Tempo Follower, and MIDI


## 36.1 Synchronizing via Link


### 36.1.1 Setting up Link

36. Synchronizing with Link, Tempo
Follower, and MIDI
36.1 Synchronizing via Link
Ableton Link is a technology that keeps devices in time over a wired or wireless network. Link is built
into Live as well as a growing number of iOS applications, and any Link-enabled software can play in
time with any other Link-enabled software simply by joining the same network.
When using Link, you can start and stop playback of each device or application independently of
every other connected device or application. Link-enabled software will remain in tempo as well as at
the correct position in relation to the global launch quantization of all participants.
36.1.1 Setting up Link
To configure Live to use Link, first make sure that your computer is connected to the same network as
any other devices that you will use Link with. This can either be a local network or an ad-hoc
(computer-to-computer) connection. Then open Live’s Link, Tempo & MIDI Settings and enable the
button next to “Show Link Toggle.”
Showing the Link Toggle in Live’s Settings.
It is possible to sync start and stop commands across all connected apps that have Start Stop Sync
enabled. To do this, click the button next to “Start Stop Sync”.
918


### 36.1.2 Using Link

The Start Stop Sync Toggle in Live’s Settings.
36.1.2 Using Link
The Link toggle in Live’s Control Bar will appear. Click to toggle Link on or off.
Link Toggle.
When on, the toggle will update to show the number of other Link-enabled apps or instances of Live
that are on the same network.
Link Indicator Showing Another Connection.
If at least one other Link-enabled app or instance of Live is connected, the Arrangement Position
display will show a moving “progress bar” whenever Live’s transport is not running. This bar is a
representation of the Live Set’s global launch quantization in relation to that of the other participants in
the Link session. After you trigger playback, Live will wait until this bar is filled before starting.
Arrangement Position Shows Relation to Link Timeline.
The first app or Live instance to join a Link session will set the initial tempo for the others. Any Link-
enabled apps or instances of Live can then change their tempo at any time and all others will follow. If
multiple participants try to change the tempo simultaneously, everyone else will try to follow, but the
last one who changes the tempo will “win.”
919


## 36.2 Synchronizing via Tempo Follower


### 36.2.1 Setting Up Tempo Follower

Tempo changes made by any participant in a Link session will override tempo automation in your Live
Set.
Note that the metronome’s recording count-in cannot be used when Link is enabled.
In most cases, Link will work without issues as soon as it is enabled and will provide reliable
synchronization under all conditions. If you have further questions or run into issues, we recommend
checking out the Link FAQ in the Knowledge Base.
36.2 Synchronizing via Tempo Follower
You might encounter situations where a Link connection or MIDI Clock are not available. Or,
sometimes you might prefer not to use a rigid, computer-generated clock. For example, you might like
Live’s tempo to follow the natural push and pull of a drummer in your band, or you might be trying to
synchronize to a set of turntables during a DJ performance. This is where Tempo Follower comes in.
Tempo Follower analyzes an incoming audio signal in real-time and interprets its tempo, allowing Live
to follow along and keep in time.
36.2.1 Setting Up Tempo Follower
To set an external audio input as a source for Tempo Follower, first open Live’s Link, Tempo & MIDI
Settings. In the Tempo Follower section, set the Input Channel (Ext. In) to the input on your audio
interface that is connected to the source you wish to follow. For a drum kit, this might be a dedicated
overhead microphone. For turntables, you might choose to use a record output or effects loop from a
DJ mixer. Note that while Tempo Follower’s algorithm is optimized for use with audio signals that have
a clear rhythm, you can also be creative and experiment with different sources.
Tempo Follower Settings in Live’s Settings.
920


## 36.3 Synchronizing via MIDI

When the “Show Tempo Follower Toggle” switch is set to “Show”, you will see a “Follow” button
appear in the Control Bar, alongside the other tempo-related parameters, at the left-hand side.
The Follow Button in the Control Bar.
Activating the “Follow” button will turn on Tempo Follower, and Live will begin listening to the
configured audio source and interpreting its tempo. Note that Tempo Follower does not run when the
Follow button is hidden.
When Tempo Follower cannot be connected to the audio input device channel specified in the
Settings, the feature is disabled and the Follow button will appear grayed out.
Note: Link, Tempo Follower, and External Sync are mutually exclusive; the Link and the External Sync
switches are disabled when Tempo Follower is enabled. Live can still send MIDI clock information to
external devices when Tempo Follower is enabled, but it cannot receive it.
36.3 Synchronizing via MIDI
If you’re working with devices that don’t support Link, you can synchronize via MIDI. The MIDI
protocol defines two ways to synchronize sequencers, both of which are supported by Live. Both
protocols work with the notion of a sync host, which delivers a sync signal that is tracked by the sync 
device(s).
MIDI Clock: MIDI Clock works like a metronome ticking at a fast rate. The rate of the incoming ticks is
tempo-dependent: Changing the tempo at the sync host (e.g., a drum machine) will cause the device
to follow the change. The MIDI Clock protocol also provides messages that indicate the song position.
With respect to MIDI Clock, Live can act as both a MIDI sync host and device.
MIDI Timecode: MIDI Timecode is the MIDI version of the SMPTE protocol, the standard means of
synchronizing tape machines and computers in the audio and film industry. A MIDI Timecode
message specifies a time in seconds and frames (subdivisions of a second). Live will interpret a
Timecode message as a position in the Arrangement. Timecode messages carry no meter-related
information; when slaving Live to another sequencer using MIDI Timecode, you will have to adjust the
tempo manually. Tempo changes cannot be tracked. Detailed MIDI Timecode Settings are explained 
later in this chapter. With respect to MIDI Timecode, Live can only act as a MIDI sync device, not a
host.
921


### 36.3.1 Synchronizing External MIDI Devices to Live


### 36.3.2 Synchronizing Live to External MIDI Devices

36.3.1 Synchronizing External MIDI Devices to Live
Live can send MIDI Clock messages to an external MIDI sequencer (or drum machine). After
connecting the sequencer to Live and setting it up to receive MIDI sync, turn the device on as a sync
destination in Live’s Link, Tempo & MIDI Settings.
Choosing a MIDI Device for Live.
The lower indicator LED next to the Control Bar’s EXT button will flash when Live is sending sync
messages to external sequencers.
36.3.2 Synchronizing Live to External MIDI Devices
Live can be synchronized via MIDI to an external sequencer. After connecting the sequencer to Live
and setting it up to send sync, use Live’s Link, Tempo & MIDI Settings to tell Live about the connection.
Setting up Live as a MIDI Device.
When an external sync source has been enabled, the EXT button appears in the Control Bar. You can
then activate external sync either by switching on this button or by using the External Sync command
in the Options menu. The upper indicator LED next to the EXT button will flash if Live receives useable
sync messages.
The External Sync Switch.
When Live is synced to an external MIDI device, it can accept song position pointers from this device,
syncing it not only in terms of tempo but in terms of its position in the song. If the host jumps to a new
position within the song, Live will do the same. However, if the Control Bar’s Loop switch is activated,
playback will be looped, and song position pointers will simply be “wrapped“ into the length of the
loop.
922


#### 36.3.2.1 MIDI Timecode Options


### 36.3.3 Sync Delay

When Link is enabled, Live can send MIDI clock information to external devices, but cannot receive it;
the External Sync switch is disabled when Link is enabled.
36.3.2.1 MIDI Timecode Options
Timecode options can be set up per MIDI device. Select a MIDI device from the Link, Tempo & MIDI
Settings’ MIDI Ports list to access the settings.
The MIDI Timecode Frame Rate setting is relevant only if “MIDI Timecode“ is chosen from the MIDI
Sync Type menu. The MIDI Timecode Rate chooser selects the type of Timecode to which Live will
synchronize. All of the usual SMPTE frame rates are available. When the Rate is set to “SMPTE All,“
Live will auto-detect the Timecode format of incoming sync messages and interpret the messages
accordingly. Note that you can adjust the Timecode format that is used for display in the Arrangement
View: Go to the Options menu, and then access the Time Ruler Format sub-menu.
The MIDI Timecode Offset setting is also only relevant if “MIDI Timecode“ is chosen from the Sync
Type menu. You can specify a SMPTE time offset using this control. Live will interpret this value as the
Arrangement’s start time.
36.3.3 Sync Delay
The Sync Delay controls, which are separately available for each MIDI device, allow you to delay
Live’s internal time base against the sync signal. This can be useful in compensating for delays incurred
by the signal transmission. The Sync Delay for a specific MIDI device appears as you select the MIDI
device from the Link, Tempo & MIDI Settings’ MIDI Ports list. To adjust the delay, have both Live and
the other sequencer play a rhythmical pattern with pronounced percussive sounds. While listening to
the output from both, adjust the Sync Delay control until both sounds are in perfect sync.
Adjusting Sync Delay.
923

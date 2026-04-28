# 22. Stem Separation


## 22.1 How Stem Separation Works in Live


## 22.2 Separating Audio Files and Clips

22. Stem Separation
With Live’s built-in stem separation, you can easily extract the main elements of any recorded audio
material — such as a song, loop, or sample — into individual parts. Stems can be treated like any
other audio clip: you can warp, chop, and rearrange them, as well as process them using effects.
Splitting a multi-layered audio recording into stems can be useful for a variety of creative
applications. You can isolate vocals for remixes or mashups, deconstruct melodies and rhythms,
extract individual instruments for samples, blend stems for DJ mixes, and more.
22.1 How Stem Separation Works in Live
Stem separation, also called music source separation or stem splitting, analyzes the spectral and
temporal characteristics of an audio signal and extracts the detected components into parts, which are
referred to as stems.
In Live, this process uses a deep learning model specifically trained for source separation. It functions
similarly to existing architectures that are used for music source separation but has been optimized for
local use. This means you can split audio into stems directly within Live without being connected to the
internet or needing to install any other external tools.
Any mono or stereo audio file can be separated into four stems: Vocals, Drums, Bass, and Others. The
Others stem contains all parts of the audio that are not detected as vocals, drums, or bass.
Throughout this chapter, we refer to splitting stems for songs as an example, but keep in mind you can
use stem separation with any recorded audio material.
22.2 Separating Audio Files and Clips
You can separate audio files from the browser or separate audio clips from the Session or
Arrangement View using the Separate Stems to New Audio Tracks command in the context menu or
the Create menu.
415

Separate an Audio File From the Browser.
Separate an Audio Clip From the Arrangement or Session View.
Once the command has been selected, a dialog appears containing different options for the
separation process.
416

The Separate Stems Dialog.
Use the Vocals, Drums, Bass, and Others toggles to determine which elements of the song are
included in the separation.
Choose whether you want the separation process to be based on speed or quality using the quality
mode selector. You may want to use High Speed mode for quick drafts and edits, or use High Quality
mode when more detailed results are needed.
Click the Separate button to proceed with the process. Note that if playback is running, it will stop
once the stem separation begins.
Each stem is rendered onto its own track in a new Group Track. The stem clips and tracks use the
corresponding colors from the toggles in the stem separation dialog, while the Group Track uses the
source clip’s track color.
417


### 22.2.1 Separation Speed vs. Quality

Separated Stems in the Arrangement View.
Any audio effects from the source track are added to the Group Track and therefore aren’t rendered in
the stems themselves. Additionally, track automation is copied to the new Group Track, while clip
envelope automation and modulation are copied to the individual stem clips.
Once the stems are rendered, the source clip is deactivated to avoid doubled output. If you want to
reactivate it, select the clip and then press the 0  key.
If you only separate one part of the song, the vocals for example, a single track containing the new
stem is created instead of a Group Track.
When splitting a song from the browser, the resulting stems are added to the Session or Arrangement
View, depending on which view is in focus.
The audio files for separated stems are stored in the Current Project folder under Samples →
Processed → Stems.
22.2.1 Separation Speed vs. Quality
In the Separate Stems dialog, you can choose between two quality modes: High Speed and High
Quality. The mode determines whether the separation process prioritizes quickness or accuracy.
When set to High Speed, the process will be faster, though it may still take several minutes on older
system configurations. In this mode, all stems are separated in a single pass.
When set to High Quality, the separation accuracy is improved (as measured by a higher Signal-to-
Distortion Ratio, i.e., SDR score), at the cost of slower processing. In this mode, the Vocals, Drums, and
Bass parts are processed through their own dedicated separation passes. The Others stem is then
created from the remaining audio after the three passes.
418

With either mode, you can reduce the processing time by cropping the sample before running the
separation. For example, if you only want the stems from the chorus of a song, you can shorten the
clip to the desired area using the Crop Clip Sample to Time Selection command in the Sample Editor.
You can also crop a clip from a time selection in the Arrangement using the Crop Clip command in a
track’s context menu. The corresponding shortcut for both Crop commands is Ctrl
Shift
J
(Win) / Cmd
Shift
J  (Mac).
When using High Quality mode, you can shorten the processing time by separating only the stems
you need. That being said, if the Others stem is included, all parts are processed so that the remaining
audio can be accurately rendered. For example, separating only the Vocals and Others stems takes
the same amount of time as processing all parts because the Drums and Bass stems are still rendered.
The Vocals and Others stems are added to the Set, while the Drums and Bass stems are stored in the
Stems folder within the Current Project.
Generally speaking, the overall amount of time required for the separation process highly depends on
your system configuration. Stem separation may take a while on older Windows computers, Intel
Macs, and Mac computers running macOS 11 Big Sur.
Due to the nature of the separation process, you may occasionally notice that certain elements of the
audio end up in stems you didn’t expect. For example, you may hear the high frequencies from hi-hats
in the Others stem, or synth sounds with chorus effects in the Vocals stem. This kind of overlap between
stems can happen for a variety of reasons ranging from the quality mode used to the tonal
characteristics of the source material. Depending on how you want to use the stems, you can try
splitting a song using High Speed mode and then running the separation again with High Quality
mode to see which results you prefer.
419

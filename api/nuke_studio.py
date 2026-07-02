import hiero.core
import hiero.ui
import hiero.exporters
import os
import re


def get_or_create_bin(project, name):
    """Get existing bin or create a new one in the project's clip bin"""
    for item in project.clipsBin().items():
        if isinstance(item, hiero.core.Bin) and item.name() == name:
            return item

    new_bin = hiero.core.Bin(name)
    project.clipsBin().addItem(new_bin)
    return new_bin


def load_sequence(seq_path):
    """
    Load an image sequence as a clip and add it to the project

    :param seq_path: Path to a frame in the sequence
                     Example: "I:/projects/SRV_TST/sequences/MNF/mnf_sh014/Paint/dailies/jayanthk/mnf_sh014_Paint/v047/exr_Write1/mnf_sh014_Paint_v047.10001.exr"
    :return: Clip object or None if failed
    """

    if not os.path.exists(seq_path):
        print(f"Path does not exist: {seq_path}")
        return None

    # Convert single frame → sequence pattern (e.g., .10001. → .%05d.)
    match = re.search(r'\.(\d+)\.', seq_path)
    if not match:
        print(f"Could not find frame number in path: {seq_path}")
        return None

    padding = len(match.group(1))
    seq_pattern = re.sub(r'\.\d+\.', f'.%0{padding}d.', seq_path)
    print(f"Sequence pattern: {seq_pattern}")

    # Get or create project
    if hiero.core.projects():
        project = hiero.core.projects()[-1]
    else:
        project = hiero.core.newProject("Project")

    # Get or create the "Imported Plates" bin
    media_bin = get_or_create_bin(project, "Imported Plates")

    try:
        media_source = hiero.core.MediaSource(seq_pattern)
        clip = hiero.core.Clip(media_source)
        bin_item = hiero.core.BinItem(clip)
        media_bin.addItem(bin_item)

        print(f"Successfully loaded clip: {clip.name()}")
        return clip

    except Exception as e:
        print(f'Unable to load sequence: {e}')
        import traceback
        traceback.print_exc()
        return None


def get_current_project():
    """Get the current active project"""
    if hiero.core.projects():
        return hiero.core.projects()[0]
    else:
        return hiero.core.newProject("Project")


def get_sequence_by_name(project, seq_name):
    """
    Get an existing sequence by name, or create a new one if it doesn't exist

    :param project: hiero.core.Project object
    :param seq_name: Name of the sequence
    :return: Sequence object (existing or newly created)
    """
    # Check if sequence already exists
    all_seq = project.sequences()
    for seq in all_seq:
        if seq.name() == seq_name:
            print(f"Found existing sequence: {seq_name}")
            return seq

    # Create new sequence if not found
    print(f"Creating new sequence: {seq_name}")
    seq = hiero.core.Sequence(seq_name)

    # Add sequence to project's clips bin
    clips_bin = get_or_create_bin(project, "Sequences")
    bin_item = hiero.core.BinItem(seq)
    clips_bin.addItem(bin_item)

    print(f"Sequence created and added to bin: {seq_name}")
    return seq


def load_single_clip(clip_path):
    """Creates a brand new sequence and loads exactly one clip onto it."""
    if not os.path.exists(clip_path):
        print(f"Error: File not found at {clip_path}")
        return

    my_project = hiero.core.projects()[-1] if hiero.core.projects() else hiero.core.newProject()

    # Create sequence and add to project bin
    my_sequence = hiero.core.Sequence("Single_Clip_Timeline")
    my_project.clipsBin().addItem(hiero.core.BinItem(my_sequence))

    # Import media source and create clip container
    media_source = hiero.core.MediaSource(clip_path)
    my_clip = hiero.core.Clip(media_source)
    my_project.clipsBin().addItem(hiero.core.BinItem(my_clip))

    # Build track and add track item
    video_track = hiero.core.VideoTrack("Video 1")
    my_sequence.addTrack(video_track)

    track_item = video_track.createTrackItem(my_clip.name())
    track_item.setSource(my_clip)

    clip_duration = my_clip.duration()
    track_item.setTimelineIn(0)
    track_item.setTimelineOut(clip_duration - 1)
    track_item.setSourceIn(0)
    track_item.setSourceOut(clip_duration - 1)

    video_track.addItem(track_item)
    hiero.ui.openInViewer(my_sequence)


def load_multiple_clips_for_compare(clip_paths_list):
    """
    Takes a list of file paths, creates a new sequence, and stacks
    each clip on its own video track starting at frame 0 for easy comparison.
    """
    valid_paths = [p for p in clip_paths_list if os.path.exists(p)]
    if not valid_paths:
        print("Error: No valid paths provided for comparison.")
        return

    my_project = hiero.core.projects()[-1] if hiero.core.projects() else hiero.core.newProject()

    # Create a dedicated compare sequence
    my_sequence = hiero.core.Sequence("Compare_Timeline")
    my_project.clipsBin().addItem(hiero.core.BinItem(my_sequence))

    # Stack each clip on a separate track layer
    for index, path in enumerate(valid_paths):
        media_source = hiero.core.MediaSource(path)
        my_clip = hiero.core.Clip(media_source)
        my_project.clipsBin().addItem(hiero.core.BinItem(my_clip))

        # Name tracks distinctly (e.g., Video 1_v01, Video 2_v02)
        track_name = f"Video {index + 1}_{my_clip.name()}"
        video_track = hiero.core.VideoTrack(track_name)
        my_sequence.addTrack(video_track)

        # Build track item
        track_item = video_track.createTrackItem(my_clip.name())
        track_item.setSource(my_clip)

        clip_duration = my_clip.duration()
        track_item.setTimelineIn(0)
        track_item.setTimelineOut(clip_duration - 1)
        track_item.setSourceIn(0)
        track_item.setSourceOut(clip_duration - 1)

        video_track.addItem(track_item)

    hiero.ui.openInViewer(my_sequence)


def load_sequence_dailies(clip_paths_list, trackName, seqName):
    """
    Loads all clips sequentially onto a single video track —
    one after another like a dailies reel.

    Timeline result:
        Video 1: [clip_001][clip_002][clip_003][clip_004] ...

    :param clip_paths_list: list of file paths (mov, exr sequence, etc.)
    """
    valid_paths = [p for p in clip_paths_list if os.path.exists(p)]
    if not valid_paths:
        print("Error: No valid paths provided.")
        return

    my_project = hiero.core.projects()[-1] if hiero.core.projects() else hiero.core.newProject()

    # Create sequence and add to project bin
    my_sequence = hiero.core.Sequence(seqName)
    my_project.clipsBin().addItem(hiero.core.BinItem(my_sequence))

    # Single video track for all clips
    video_track = hiero.core.VideoTrack(trackName)
    my_sequence.addTrack(video_track)

    current_frame = 0  # tracks where next clip starts on the timeline

    for path in valid_paths:
        try:
            media_source = hiero.core.MediaSource(path)
            my_clip = hiero.core.Clip(media_source)
            my_project.clipsBin().addItem(hiero.core.BinItem(my_clip))

            track_item = video_track.createTrackItem(my_clip.name())
            track_item.setSource(my_clip)

            clip_duration = my_clip.duration()
            track_item.setTimelineIn(current_frame)
            track_item.setTimelineOut(current_frame + clip_duration - 1)
            track_item.setSourceIn(0)
            track_item.setSourceOut(clip_duration - 1)

            video_track.addItem(track_item)

            current_frame += clip_duration  # advance by this clip's duration

        except Exception as e:
            print(f"[load_sequence_dailies] failed to load {path}: {e}")
            continue

    hiero.ui.openInViewer(my_sequence)
    # print(f"[load_sequence_dailies] loaded {len(valid_paths)} clips onto single track")


def export_clips_with_annotations(
        export_path="D:/annotations/v001",
        preset_name="Basic Nuke Shot With Annotations",
        submission_name="Single Render Process"
):
    """
    Automates: Right-click > Export > Custom Export >
               Process as Shots > Basic Nuke Shot With Annotations
    - Strips TranscodeExporter task (jpeg) to avoid frame number errors
    - Restores preset after export so UI is unchanged
    """
    project = hiero.core.projects()[-1]

    # Collect all shots
    track_items = []
    for seq in project.sequences():
        for track in seq.videoTracks():
            for item in track.items():
                track_items.append(hiero.core.ItemWrapper(item))

    if not track_items:
        print("No shots found.")
        return

    print(f"Found {len(track_items)} shots to export.")

    # Find preset
    registry = hiero.core.taskRegistry
    preset = None
    for p in registry.localPresets():
        if p.name() == preset_name:
            preset = p
            break

    if not preset:
        print(f"Preset '{preset_name}' not found.")
        return

    print(f"Using preset: {preset.name()}")

    # Strip TranscodeExporter, keep only NukeAnnotations task
    original_template = preset.properties().get("exportTemplate", [])
    preset.properties()["exportTemplate"] = [
        task for task in original_template
        if "TranscodeExporter" not in str(task[1])
    ]
    preset.properties()["exportRoot"] = export_path

    try:
        registry.createAndExecuteProcessor(preset, track_items, submission_name, synchronous=True)
        print(f" Export COMPLETE → {export_path}")
    except Exception as e:
        print(f" Export failed: {e}")
    finally:
        # Always restore preset even if export fails
        preset.properties()["exportTemplate"] = original_template
        print("Preset restored.")

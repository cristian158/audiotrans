"""
Audio Transcoder

A GTK-based application for transcoding audio files between different formats.
Supports MP3, WAV, OGG, AAC, and FLAC formats with configurable bitrate and sample rate.

Features:
- Drag and drop file support
- Batch processing
- Progress tracking
- Configurable output settings
- Disk space checking
- FFmpeg validation

Requirements:
- Python 3.6+
- GTK 3.0
- FFmpeg
"""

# - 'Select output Dir' next to 'Select Input Files'
# - Max accuracy on loading bars (120% and 0.0%???)
# - Make cli version
# - Handle CtrlC in gtk 



import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk
import subprocess
import json
import os
import logging
from typing import List, Optional
import urllib.parse
import threading
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants
SUPPORTED_FORMATS = ["MP3", "WAV", "OGG", "AAC", "FLAC"]
DEFAULT_BITRATES = ["64k", "128k", "192k", "256k", "320k"]
DEFAULT_SAMPLERATES = ["22050", "44100", "48000", "96000"]
DEFAULT_WINDOW_SIZE = (600, 400)

def check_ffmpeg_available():
    """Check if FFmpeg is installed and accessible."""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_disk_space(path, required_size_mb=100):
    """Check if there's enough disk space for transcoding."""
    try:
        stat = shutil.disk_usage(path)
        free_space_mb = stat.free / (1024 * 1024)
        return free_space_mb > required_size_mb
    except Exception:
        return False

class AudioFile:
    """Represents an audio file to be transcoded."""
    def __init__(self, path: str):
        self.path = path
        self.size_mb = os.path.getsize(path) / (1024 * 1024) if os.path.exists(path) else 0

class TranscodeSettings:
    """Stores the settings for audio transcoding."""
    def __init__(self):
        self.output_format = "mp3"
        self.bitrate = "192k"
        self.samplerate = "44100"
        self.output_directory: Optional[str] = None

class AudioTranscoder(Gtk.Window):
    """Main application window for the audio transcoder."""
    def __init__(self):
        Gtk.Window.__init__(self, title="Audio Transcoder")
        self.set_border_width(10)
        self.set_default_size(*DEFAULT_WINDOW_SIZE)
        self.set_resizable(True)

        if not check_ffmpeg_available():
            self.show_error_dialog("FFmpeg is not installed or not accessible. Please install FFmpeg to use this application.")
            return

        self.input_files: List[AudioFile] = []
        self.settings = TranscodeSettings()
        self.is_transcoding = False
        self.total_files = 0
        self.current_file_index = 0
        self.transcode_lock = threading.Lock()
        self.current_process = None

        self.setup_ui()
        self.connect("delete-event", self.on_window_delete)

    def on_window_delete(self, widget, event):
        """Handle window close event."""
        if self.is_transcoding:
            if self.current_process:
                self.current_process.terminate()
            self.is_transcoding = False
        return False

    def setup_ui(self):
        """Set up the user interface."""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        # Create a scrolled window for the main content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        vbox.pack_start(scrolled, True, True, 0)

        # Main content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        scrolled.add(content_box)

        self.setup_input_selection(content_box)
        self.setup_file_list(content_box)
        self.setup_clear_button(content_box)
        self.setup_output_format(content_box)
        self.setup_custom_parameters(content_box)
        self.setup_output_directory(content_box)
        self.setup_transcode_button(content_box)
        self.setup_progress_bars(content_box)
        self.setup_status_label(content_box)

        # Add a status bar at the bottom
        self.statusbar = Gtk.Statusbar()
        vbox.pack_end(self.statusbar, False, False, 0)

    def setup_input_selection(self, vbox):
        input_button = Gtk.Button(label="Select Input Files")
        input_button.connect("clicked", self.on_input_files_clicked)
        vbox.pack_start(input_button, False, False, 0)

    def setup_file_list(self, vbox):
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.file_list = Gtk.ListBox()
        scrolled_window.add(self.file_list)
        vbox.pack_start(scrolled_window, True, True, 0)

        self.file_list.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.file_list.connect("drag-data-received", self.on_drag_data_received)
        self.file_list.drag_dest_add_uri_targets()

    def setup_clear_button(self, vbox):
        clear_button = Gtk.Button(label="Clear File List")
        clear_button.connect("clicked", self.on_clear_clicked)
        vbox.pack_start(clear_button, False, False, 0)

    def setup_output_format(self, vbox):
        hbox = Gtk.Box(spacing=6)
        hbox.pack_start(Gtk.Label(label="Output Format:"), False, False, 0)
        self.format_combo = Gtk.ComboBoxText()
        for fmt in SUPPORTED_FORMATS:
            self.format_combo.append_text(fmt)
        self.format_combo.set_active(0)
        hbox.pack_start(self.format_combo, False, False, 0)
        vbox.pack_start(hbox, False, False, 0)

    def setup_custom_parameters(self, vbox):
        hbox = Gtk.Box(spacing=6)
        hbox.pack_start(Gtk.Label(label="Bitrate:"), False, False, 0)
        self.bitrate_combo = Gtk.ComboBoxText()
        for br in DEFAULT_BITRATES:
            self.bitrate_combo.append_text(br)
        self.bitrate_combo.set_active(2)
        hbox.pack_start(self.bitrate_combo, False, False, 0)

        hbox.pack_start(Gtk.Label(label="Sample Rate:"), False, False, 0)
        self.samplerate_combo = Gtk.ComboBoxText()
        for sr in DEFAULT_SAMPLERATES:
            self.samplerate_combo.append_text(sr)
        self.samplerate_combo.set_active(1)
        hbox.pack_start(self.samplerate_combo, False, False, 0)
        
        vbox.pack_start(hbox, False, False, 0)

    def setup_output_directory(self, vbox):
        hbox = Gtk.Box(spacing=6)
        output_button = Gtk.Button(label="Select Output Directory")
        output_button.connect("clicked", self.on_output_directory_clicked)
        hbox.pack_start(output_button, False, False, 0)
        self.output_label = Gtk.Label(label="Default: Same as input")
        hbox.pack_start(self.output_label, True, True, 0)
        vbox.pack_start(hbox, False, False, 0)

    def setup_transcode_button(self, vbox):
        self.transcode_button = Gtk.Button(label="Transcode")
        self.transcode_button.connect("clicked", self.on_transcode_clicked)
        vbox.pack_start(self.transcode_button, False, False, 0)

    def setup_progress_bars(self, vbox):
        self.total_progressbar = Gtk.ProgressBar()
        vbox.pack_start(self.total_progressbar, False, False, 0)
        self.total_progressbar.set_text("Total Progress")
        self.total_progressbar.set_show_text(True)

        self.file_progressbar = Gtk.ProgressBar()
        vbox.pack_start(self.file_progressbar, False, False, 0)
        self.file_progressbar.set_text("Current File Progress")
        self.file_progressbar.set_show_text(True)

    def setup_status_label(self, vbox):
        self.status_label = Gtk.Label()
        vbox.pack_start(self.status_label, False, False, 0)

    def on_input_files_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(title="Please choose files", parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.set_select_multiple(True)

        filter_audio = Gtk.FileFilter()
        filter_audio.set_name("Audio files")
        filter_audio.add_mime_type("audio/*")
        dialog.add_filter(filter_audio)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_files = [AudioFile(f) for f in dialog.get_filenames()]
            self.add_files(new_files)
        dialog.destroy()

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        uris = data.get_uris()
        files = [AudioFile(self.uri_to_path(uri)) for uri in uris if self.uri_to_path(uri)]
        self.add_files(files)

    def add_files(self, new_files):
        for file in new_files:
            if file.path not in [f.path for f in self.input_files]:
                self.input_files.append(file)
        self.update_file_list()

    def update_file_list(self):
        for child in self.file_list.get_children():
            self.file_list.remove(child)
        for audio_file in self.input_files:
            self.file_list.add(Gtk.Label(label=os.path.basename(audio_file.path)))
        self.file_list.show_all()

    @staticmethod
    def uri_to_path(uri):
        path = urllib.parse.unquote(uri)
        if path.startswith('file://'):
            return path[7:]
        return None

    def on_clear_clicked(self, widget):
        self.input_files.clear()
        self.update_file_list()

    def on_output_directory_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(title="Please choose output directory", parent=self, action=Gtk.FileChooserAction.SELECT_FOLDER)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.settings.output_directory = dialog.get_filename()
            self.output_label.set_text(self.settings.output_directory)
        dialog.destroy()

    def on_transcode_clicked(self, widget):
        if not self.input_files:
            self.show_error_dialog("No input files selected")
            return

        # Check disk space
        output_dir = self.settings.output_directory or os.path.dirname(self.input_files[0].path)
        total_size_mb = sum(f.size_mb for f in self.input_files)
        if not check_disk_space(output_dir, total_size_mb * 2):  # Double the size for safety
            self.show_error_dialog("Not enough disk space for transcoding")
            return

        self.settings.output_format = self.format_combo.get_active_text().lower()
        self.settings.bitrate = self.bitrate_combo.get_active_text()
        self.settings.samplerate = self.samplerate_combo.get_active_text()

        self.transcode_button.set_sensitive(False)
        self.is_transcoding = True
        self.total_progressbar.set_fraction(0)
        self.file_progressbar.set_fraction(0)
        self.status_label.set_text("Transcoding...")

        self.total_files = len(self.input_files)
        self.current_file_index = 0

        # Start the transcoding process in a single thread
        threading.Thread(target=self.transcode_next_file, daemon=True).start()

    def transcode_next_file(self):
        with self.transcode_lock:
            if not self.is_transcoding:
                return

            # Check if we've processed all files
            if self.current_file_index >= len(self.input_files):
                GLib.idle_add(self.finish_transcoding)
                return

            audio_file = self.input_files[self.current_file_index]
            output_filename = os.path.splitext(os.path.basename(audio_file.path))[0] + "." + self.settings.output_format
            output_dir = self.settings.output_directory or os.path.dirname(audio_file.path)
            output_path = os.path.join(output_dir, output_filename)

            if os.path.exists(output_path):
                if not self.show_overwrite_dialog(output_path):
                    self.current_file_index += 1
                    GLib.idle_add(self.update_total_progress)
                    self.transcode_next_file()
                    return

            # Start the transcoding process
            self.transcode_file(audio_file, output_path)

    def transcode_file(self, audio_file, output_path):
        try:
            command = [
                "ffmpeg", "-i", audio_file.path,
                "-y", "-b:a", self.settings.bitrate,
                "-ar", self.settings.samplerate,
                "-progress", "pipe:1",
                output_path
            ]
            
            self.current_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            
            # Start progress monitoring in a separate thread
            progress_thread = threading.Thread(
                target=self.monitor_progress,
                args=(self.current_process, audio_file.path),
                daemon=True
            )
            progress_thread.start()
            
            # Wait for process to complete
            self.current_process.wait()
            progress_thread.join(timeout=1)  # Give progress thread a moment to finish
            
            if self.current_process.returncode == 0:
                logging.info(f"Successfully transcoded: {output_path}")
                self.current_file_index += 1
                GLib.idle_add(self.update_total_progress)
                GLib.idle_add(self.transcode_next_file)
            else:
                error = self.current_process.stderr.read()
                GLib.idle_add(lambda: self.show_error_dialog(f"Transcoding failed: {error}"))
                GLib.idle_add(self.finish_transcoding)
                
        except Exception as e:
            logging.error(f"Error during transcoding: {str(e)}")
            GLib.idle_add(lambda: self.show_error_dialog(f"Error during transcoding: {str(e)}"))
            GLib.idle_add(self.finish_transcoding)

    def monitor_progress(self, process, input_path):
        """Monitor the transcoding progress in a separate thread."""
        duration = self.get_audio_duration(input_path)
        if not duration:
            return

        while process.poll() is None:  # While process is running
            try:
                line = process.stdout.readline()
                if not line:
                    continue

                if "out_time_ms" in line:
                    time_str = line.split("=")[1].strip()
                    try:
                        current_time = float(time_str) / 1000000.0  # Convert to seconds
                        progress = min(1.0, current_time / duration)
                        # Update both progress bars immediately
                        GLib.idle_add(self.update_progress_bars, progress)
                    except (ValueError, ZeroDivisionError):
                        pass
            except Exception as e:
                logging.error(f"Error monitoring progress: {str(e)}")
                break

    def update_progress_bars(self, progress):
        """Update progress bars safely from the main thread."""
        try:
            # Ensure progress is between 0 and 1
            progress = max(0.0, min(1.0, progress))
            
            # Update file progress
            self.file_progressbar.set_fraction(progress)
            self.file_progressbar.set_text(f"Current File: {progress * 100:.1f}%")
            
            # Update total progress
            if self.total_files > 0:
                total_progress = (self.current_file_index + progress) / self.total_files
                total_progress = max(0.0, min(1.0, total_progress))
                self.total_progressbar.set_fraction(total_progress)
                self.total_progressbar.set_text(f"Total Progress: {total_progress * 100:.1f}%")
                
            # Update status label with current file
            if self.current_file_index < len(self.input_files):
                current_file = os.path.basename(self.input_files[self.current_file_index].path)
                self.status_label.set_text(f"Processing: {current_file}")
        except Exception as e:
            logging.error(f"Error updating progress bars: {str(e)}")

    def get_audio_duration(self, file_path):
        try:
            command = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            logging.error(f"Error getting duration for {file_path}: {str(e)}")
        return None

    def update_total_progress(self):
        """Update the total progress bar when a file is completed."""
        try:
            if self.total_files > 0:
                progress = self.current_file_index / self.total_files
                progress = max(0.0, min(1.0, progress))
                self.total_progressbar.set_fraction(progress)
                self.total_progressbar.set_text(f"Total Progress: {progress * 100:.1f}%")
        except Exception as e:
            logging.error(f"Error updating total progress: {str(e)}")

    def show_error_dialog(self, message):
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            message_format=message
        )
        dialog.run()
        dialog.destroy()

    def show_completion_dialog(self):
        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.INFO,
                                   buttons=Gtk.ButtonsType.OK, text="All files have been transcoded successfully!")
        dialog.run()
        dialog.destroy()

    def show_overwrite_dialog(self, file_path):
        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.WARNING,
                                   buttons=Gtk.ButtonsType.YES_NO, 
                                   text=f"File already exists: {os.path.basename(file_path)}\nDo you want to overwrite it?")
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    def finish_transcoding(self):
        """Clean up after transcoding is complete."""
        self.is_transcoding = False
        self.transcode_button.set_sensitive(True)
        self.status_label.set_text("Transcoding completed!")
        self.current_process = None
        # Reset progress bars
        self.file_progressbar.set_fraction(0)
        self.total_progressbar.set_fraction(0)
        GLib.idle_add(self.show_completion_dialog)

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        filename='audio_transcoder.log', filemode='w')
    win = AudioTranscoder()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()


# tried encoding 70 files, the gui freezes, when the encoding finishes, the program sends lots of 'all files have been transcoded successfully' messages
# also when it's done, the gui catches up and starts to show the progress bar
# the transcoding seems to be working fine
# Also it froze and the messages cannot be exited unless I stop the whole software by CtrlC on the terminal that launched it 

#  show what file is being currently transcoded

#  make sure both progress bar work correctly: the 1st one is for overall progress, 2nd is for the current file.
#  they keep glitching --> the 1st one with 200% and the 2nd going back and forth with the percentages

#  being able to delete individual files from the list

#  move the 'Select Output Directory' btn under 'Select Input Files' btn. Also make it so it indicates Default: same as input.

#  now it doesn't give me 23423 messages but still 2 messages even if it's only one file 

#  CtrlC gracefully

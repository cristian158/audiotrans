# Audio Transcoder

# - 'Select output Dir' next to 'Select Input Files'
# - Two success messages, unnecessary
# - Max accuracy on loading bars (120% and 0.0%???)



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

# Constants
SUPPORTED_FORMATS = ["MP3", "WAV", "OGG", "AAC", "FLAC"]
DEFAULT_BITRATES = ["64k", "128k", "192k", "256k", "320k"]
DEFAULT_SAMPLERATES = ["22050", "44100", "48000", "96000"]
DEFAULT_WINDOW_SIZE = (600, 400)

class AudioFile:
    def __init__(self, path: str):
        self.path = path

class TranscodeSettings:
    def __init__(self):
        self.output_format = "mp3"
        self.bitrate = "192k"
        self.samplerate = "44100"
        self.output_directory: Optional[str] = None

class AudioTranscoder(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Audio Transcoder")
        self.set_border_width(10)
        self.set_default_size(*DEFAULT_WINDOW_SIZE)

        self.input_files: List[AudioFile] = []
        self.settings = TranscodeSettings()
        self.is_transcoding = False
        self.total_files = 0
        self.current_file_index = 0

        self.setup_ui()

    def setup_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        self.setup_input_selection(vbox)
        self.setup_file_list(vbox)
        self.setup_clear_button(vbox)
        self.setup_output_format(vbox)
        self.setup_custom_parameters(vbox)
        self.setup_output_directory(vbox)
        self.setup_transcode_button(vbox)
        self.setup_progress_bars(vbox)
        self.setup_status_label(vbox)

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

        # Start the transcoding process
        GLib.idle_add(self.transcode_next_file)
        
        threading.Thread(target=self.transcode_next_file, daemon=True).start()

    def transcode_next_file(self):
        if not self.is_transcoding or not self.input_files:
            if self.current_file_index == self.total_files:
                self.finish_transcoding()
            return False

        audio_file = self.input_files[self.current_file_index]
        output_filename = os.path.splitext(os.path.basename(audio_file.path))[0] + "." + self.settings.output_format
        output_dir = self.settings.output_directory or os.path.dirname(audio_file.path)
        output_path = os.path.join(output_dir, output_filename)

        if os.path.exists(output_path):
            if not self.show_overwrite_dialog(output_path):
                self.current_file_index += 1
                self.update_total_progress()
                return GLib.idle_add(self.transcode_next_file)

        # Start the transcoding process in a new thread
        threading.Thread(target=self.transcode_file, args=(audio_file, output_path), daemon=True).start()
        return False# Don't call this function again from idle_add
    
    def transcode_file(self, audio_file, output_path):
        command = [
            "ffmpeg", "-i", audio_file.path,
            "-y", "-b:a", self.settings.bitrate,
            "-ar", self.settings.samplerate,
            "-progress", "pipe:1"
        ]

        if self.settings.output_format == "mp3":
            command.extend(["-codec:a", "libmp3lame"])
        elif self.settings.output_format == "ogg":
            command.extend(["-codec:a", "libvorbis"])
        elif self.settings.output_format == "aac":
            command.extend(["-codec:a", "aac"])
        elif self.settings.output_format == "flac":
            command.extend(["-codec:a", "flac"])

        command.append(output_path)

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            self.monitor_progress(process, audio_file.path)
            process.wait()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, command)

            logging.info(f"Successfully transcoded: {output_path}")
            GLib.idle_add(self.file_complete)
        except subprocess.CalledProcessError as e:
            error_message = f"Error transcoding {audio_file.path}: {e}"
            logging.error(error_message)
            GLib.idle_add(self.show_error_dialog, f"Error transcoding {os.path.basename(audio_file.path)}")
            GLib.idle_add(self.file_complete)
        
    def finish_transcoding(self):
        self.is_transcoding = False
        self.transcode_button.set_sensitive(True)
        self.status_label.set_text("Transcoding completed!")
        # Only show one completion dialog
        GLib.idle_add(self.show_completion_dialog)

    def file_complete(self):
        self.current_file_index += 1
        self.update_total_progress()
        if self.current_file_index < self.total_files:
            GLib.idle_add(self.transcode_next_file)
        else:
            self.finish_transcoding()
        return False

    def monitor_progress(self, process, input_path):
        duration = self.get_audio_duration(input_path)
        
        while process.poll() is None:
            line = process.stdout.readline()
            if not line:
                continue
                
            parts = line.split('=')
            if len(parts) == 2 and parts[0] == 'out_time_ms':
                try:
                    value = parts[1].strip()
                    if value != 'N/A':
                        progress = min(int(value) / (duration * 1000000), 1.0)
                        GLib.idle_add(self.update_progress_bars, progress)
                    else:
                        GLib.idle_add(self.file_progressbar.pulse)
                except (ValueError, TypeError):
                    GLib.idle_add(self.file_progressbar.pulse)
                    logging.warning(f"Could not parse progress value: {value}")

    def update_progress_bars(self, progress):
        self.file_progressbar.set_fraction(progress)
        self.file_progressbar.set_text(f"{progress:.1%}")
    
    def get_audio_duration(self, file_path):
        try:
            result = subprocess.run([
                'ffprobe', 
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ], capture_output=True, text=True)
            
            data = json.loads(result.stdout)
            duration = float(data['format']['duration'])
            return duration
        except (subprocess.CalledProcessError, KeyError, ValueError, json.JSONDecodeError):
            logging.error(f"Failed to get duration for {file_path}")
            return None
        
    def update_progress_periodically(self, process, input_path):
        def update():
            line = process.stdout.readline()
            if line == '' and process.poll() is not None:
                return False
            if line:
                parts = line.split('=')
                if len(parts) == 2:
                    key, value = parts
                    if key == 'out_time_ms':
                        duration = self.get_audio_duration(input_path)
                        if duration:
                            progress = min(int(value) / (duration * 1000000), 1.0)
                            GLib.idle_add(self.file_progressbar.set_fraction, progress)
                            GLib.idle_add(self.file_progressbar.set_text, f"{progress:.1%}")
                        else:
                            # Handle the case where duration couldn't be determined
                            GLib.idle_add(self.file_progressbar.pulse)
            return True

        GLib.idle_add(update)

    def update_total_progress(self):
        progress = self.current_file_index / self.total_files
        self.total_progressbar.set_fraction(progress)
        self.total_progressbar.set_text(f"{progress:.1%}")

    def show_error_dialog(self, message):
        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.OK, text=message)
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

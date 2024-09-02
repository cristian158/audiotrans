import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk
import subprocess
import os
import re
import json
import urllib.parse
import threading
import shutil

class AudioTranscoder(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Audio Transcoder")
        self.set_border_width(10)
        self.set_default_size(600, 400)

        self.last_folder = os.path.expanduser("~")
        self.input_files = []
        self.process = None
        self.current_file_index = 0
        self.total_duration = 0
        self.current_duration = 0

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        # Input file selection
        input_box = Gtk.Box(spacing=6)
        self.input_button = Gtk.Button(label="Select Input Files")
        self.input_button.connect("clicked", self.on_input_files_clicked)
        input_box.pack_start(self.input_button, False, False, 0)
        self.input_label = Gtk.Label(label="No files selected")
        input_box.pack_start(self.input_label, True, True, 0)
        vbox.pack_start(input_box, False, False, 0)

        # File list
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.file_list = Gtk.ListBox()
        scrolled_window.add(self.file_list)
        vbox.pack_start(scrolled_window, True, True, 0)

        # Enable drag and drop
        self.file_list.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.file_list.connect("drag-data-received", self.on_drag_data_received)
        self.file_list.drag_dest_add_uri_targets()

        # Clear file list button
        self.clear_button = Gtk.Button(label="Clear File List")
        self.clear_button.connect("clicked", self.on_clear_clicked)
        vbox.pack_start(self.clear_button, False, False, 0)

        # Output format selection
        format_box = Gtk.Box(spacing=6)
        format_label = Gtk.Label(label="Output Format:")
        format_box.pack_start(format_label, False, False, 0)
        self.format_combo = Gtk.ComboBoxText()
        formats = ["MP3", "WAV", "OGG", "AAC", "FLAC"]
        for fmt in formats:
            self.format_combo.append_text(fmt)
        self.format_combo.set_active(0)
        format_box.pack_start(self.format_combo, False, False, 0)
        vbox.pack_start(format_box, False, False, 0)

        # Custom parameters
        params_box = Gtk.Box(spacing=6)
        
        bitrate_label = Gtk.Label(label="Bitrate:")
        params_box.pack_start(bitrate_label, False, False, 0)
        self.bitrate_combo = Gtk.ComboBoxText()
        bitrates = ["64k", "128k", "192k", "256k", "320k"]
        for br in bitrates:
            self.bitrate_combo.append_text(br)
        self.bitrate_combo.set_active(2)  # Default to 192k
        params_box.pack_start(self.bitrate_combo, False, False, 0)
        
        samplerate_label = Gtk.Label(label="Sample Rate:")
        params_box.pack_start(samplerate_label, False, False, 0)
        self.samplerate_combo = Gtk.ComboBoxText()
        samplerates = ["22050", "44100", "48000", "96000"]
        for sr in samplerates:
            self.samplerate_combo.append_text(sr)
        self.samplerate_combo.set_active(1)  # Default to 44100
        params_box.pack_start(self.samplerate_combo, False, False, 0)
        
        vbox.pack_start(params_box, False, False, 0)

        # Output directory selection
        output_box = Gtk.Box(spacing=6)
        self.output_button = Gtk.Button(label="Select Output Directory")
        self.output_button.connect("clicked", self.on_output_directory_clicked)
        output_box.pack_start(self.output_button, False, False, 0)
        self.output_label = Gtk.Label(label="Default: Same as input")
        output_box.pack_start(self.output_label, True, True, 0)
        vbox.pack_start(output_box, False, False, 0)

        # Transcode button
        self.transcode_button = Gtk.Button(label="Transcode")
        self.transcode_button.connect("clicked", self.on_transcode_clicked)
        vbox.pack_start(self.transcode_button, False, False, 0)

        # Progress bar
        self.progressbar = Gtk.ProgressBar()
        vbox.pack_start(self.progressbar, False, False, 0)

        # Status label
        self.status_label = Gtk.Label()
        vbox.pack_start(self.status_label, False, False, 0)

        # Cancel button
        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.connect("clicked", self.on_cancel_clicked)
        self.cancel_button.set_sensitive(False)
        vbox.pack_start(self.cancel_button, False, False, 0)

        self.output_directory = None
        self.is_transcoding = False
        self.transcode_thread = None

        # Check if FFmpeg is installed
        if not self.check_ffmpeg():
            self.show_error_dialog("FFmpeg is not installed. Please install FFmpeg to use this application.")
            self.transcode_button.set_sensitive(False)

    def check_ffmpeg(self):
        return shutil.which("ffmpeg") is not None

    def on_input_files_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose files", parent=self, action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        dialog.set_current_folder(self.last_folder)
        dialog.set_select_multiple(True)

        filter_audio = Gtk.FileFilter()
        filter_audio.set_name("Audio files")
        filter_audio.add_mime_type("audio/*")
        dialog.add_filter(filter_audio)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_files = dialog.get_filenames()
            self.input_files.extend([f for f in new_files if f not in self.input_files])
            self.last_folder = os.path.dirname(self.input_files[0])
            self.update_file_list()
        
        dialog.destroy()
    
    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        files = data.get_uris()
        for file_uri in files:
            file_path = self.uri_to_path(file_uri)
            if file_path and file_path not in self.input_files and self.is_audio_file(file_path):
                self.input_files.append(file_path)
        self.update_file_list()

    def uri_to_path(self, uri):
        path = urllib.parse.unquote(uri)  # Decode URL-encoded characters
        if path.startswith('file://'):
            return path[7:]  # Remove 'file://' prefix
        return None

    def is_audio_file(self, file_path):
        audio_extensions = ['.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a', '.wma']
        return os.path.splitext(file_path)[1].lower() in audio_extensions

    def update_file_list(self):
        for child in self.file_list.get_children():
            self.file_list.remove(child)

        for file_path in self.input_files:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
            row.add(hbox)
            label = Gtk.Label(label=os.path.basename(file_path), xalign=0)
            hbox.pack_start(label, True, True, 0)
            self.file_list.add(row)

        self.file_list.show_all()
        self.input_label.set_text(f"{len(self.input_files)} files selected")

    def on_clear_clicked(self, widget):
        self.input_files.clear()
        self.update_file_list()

    def on_output_directory_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose output directory",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        dialog.set_current_folder(self.last_folder)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.output_directory = dialog.get_filename()
            self.output_label.set_text(self.output_directory)
        
        dialog.destroy()

    def on_transcode_clicked(self, widget):
        if not self.input_files:
            self.show_error_dialog("No input files selected")
            return

        self.current_file_index = 0
        self.total_duration = 0
        self.is_transcoding = True
        self.transcode_button.set_sensitive(False)
        self.cancel_button.set_sensitive(True)
        self.transcode_thread = threading.Thread(target=self.transcode_files)
        self.transcode_thread.start()

    def transcode_files(self):
        for i, input_file in enumerate(self.input_files):
            if not self.is_transcoding:
                break

            self.current_file_index = i
            self.current_duration = self.get_file_duration(input_file)
            self.total_duration += self.current_duration

            output_format = self.format_combo.get_active_text().lower()
            output_file = os.path.splitext(os.path.basename(input_file))[0] + "." + output_format
            if self.output_directory:
                output_file = os.path.join(self.output_directory, output_file)
            else:
                output_file = os.path.join(os.path.dirname(input_file), output_file)

            bitrate = self.bitrate_combo.get_active_text()
            samplerate = self.samplerate_combo.get_active_text()

            command = [
                "ffmpeg",
                "-i", input_file,
                "-y",  # Overwrite output file if it exists
                "-b:a", bitrate,
                "-ar", samplerate
            ]

            if output_format == "mp3":
                command.extend(["-codec:a", "libmp3lame"])
            elif output_format == "ogg":
                command.extend(["-codec:a", "libvorbis"])
            elif output_format == "aac":
                command.extend(["-codec:a", "aac"])
            elif output_format == "flac":
                command.extend(["-codec:a", "flac"])

            command.append(output_file)

            GLib.idle_add(self.status_label.set_text, f"Transcoding file {i + 1} of {len(self.input_files)}...")
            
            try:
                self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                while True:
                    output = self.process.stdout.readline()
                    if output == '' and self.process.poll() is not None:
                        break
                    if output:
                        self.update_progress(output)
                if self.process.returncode != 0:
                    GLib.idle_add(self.show_error_dialog, f"Error transcoding file: {input_file}")
            except Exception as e:
                GLib.idle_add(self.show_error_dialog, f"Error transcoding file: {input_file}\n{str(e)}")

        GLib.idle_add(self.finish_transcoding)

    def get_file_duration(self, file_path):
        command = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", file_path]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            format_info = data.get('format', {})
            return float(format_info.get('duration', 0))
        except subprocess.CalledProcessError:
            GLib.idle_add(self.show_error_dialog, f"Error getting duration for file: {file_path}")
            return 0
        except json.JSONDecodeError:
            GLib.idle_add(self.show_error_dialog, f"Error parsing duration for file: {file_path}")
            return 0

    def update_progress(self, output):
        time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})", output)
        if time_match:
            hours, minutes, seconds = map(float, time_match.groups())
            current_time = hours * 3600 + minutes * 60 + seconds
            file_progress = current_time / self.current_duration
            overall_progress = (self.total_duration * (self.current_file_index / len(self.input_files)) + current_time) / self.total_duration
            GLib.idle_add(self.progressbar.set_fraction, min(overall_progress, 1.0))

    def finish_transcoding(self):
        self.is_transcoding = False
        self.transcode_button.set_sensitive(True)
        self.cancel_button.set_sensitive(False)
        self.status_label.set_text("Transcoding completed!")
        self.show_completion_dialog()

    def on_cancel_clicked(self, widget):
        if self.is_transcoding:
            self.is_transcoding = False
            if self.process:
                self.process.terminate()
            self.status_label.set_text("Transcoding cancelled.")
            self.transcode_button.set_sensitive(True)
            self.cancel_button.set_sensitive(False)
            self.progressbar.set_fraction(0)

    def show_error_dialog(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message,
        )
        dialog.run()
        dialog.destroy()

    def show_completion_dialog(self):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="All files have been transcoded successfully!",
        )
        dialog.run()
        dialog.destroy()

win = AudioTranscoder()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
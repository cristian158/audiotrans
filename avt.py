## Audio Video Transcoder


## add a qtip note that explains the quality factor
# actualkkly do the transcoding button
# make it all in just one page maybe (cons: small screens)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk
import subprocess
import os
import json
import threading
import shutil
import re
import urllib.parse 
from datetime import datetime

class AudioVideoTranscoder(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Audio/Video Transcoder")
        self.set_default_size(800, 600)

        self.notebook = Gtk.Notebook()
        self.add(self.notebook)

        self.input_files = []
        self.output_directory = None
        self.is_transcoding = False
        self.process = None
        self.transcode_thread = None

        self.create_input_tab()
        self.create_output_tab()
        self.create_quality_tab()
        self.create_summary_tab()
        self.create_tags_tab()
        self.create_log_tab()

        self.create_transcode_button()

    def create_input_tab(self):
        input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.notebook.append_page(input_box, Gtk.Label(label="Input"))

        # File list
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.file_list = Gtk.ListBox()
        scrolled_window.add(self.file_list)
        input_box.pack_start(scrolled_window, True, True, 0)

        # Enable drag and drop
        self.file_list.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.file_list.connect("drag-data-received", self.on_drag_data_received)
        self.file_list.drag_dest_add_uri_targets()

        # Buttons
        button_box = Gtk.Box(spacing=6)
        add_button = Gtk.Button(label="Add Files")
        add_button.connect("clicked", self.on_add_files_clicked)
        button_box.pack_start(add_button, False, False, 0)

        remove_button = Gtk.Button(label="Remove Selected")
        remove_button.connect("clicked", self.on_remove_selected_clicked)
        button_box.pack_start(remove_button, False, False, 0)

        clear_button = Gtk.Button(label="Clear All")
        clear_button.connect("clicked", self.on_clear_clicked)
        button_box.pack_start(clear_button, False, False, 0)

        input_box.pack_start(button_box, False, False, 0)

    def create_output_tab(self):
        output_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.notebook.append_page(output_box, Gtk.Label(label="Output"))

        # Output format selection
        format_box = Gtk.Box(spacing=6)
        format_label = Gtk.Label(label="Output Format:")
        format_box.pack_start(format_label, False, False, 0)
        self.format_combo = Gtk.ComboBoxText()
        formats = ["Same as source", "MP3", "WAV", "OGG", "AAC", "FLAC", "M4A", "WMA", "MKV", "AVI", "MP4"]
        for fmt in formats:
            self.format_combo.append_text(fmt)
        self.format_combo.set_active(0)
        format_box.pack_start(self.format_combo, False, False, 0)
        output_box.pack_start(format_box, False, False, 0)

        # Extract audio option
        self.extract_audio_check = Gtk.CheckButton(label="Extract audio from video")
        output_box.pack_start(self.extract_audio_check, False, False, 0)

        # Output directory selection
        dir_box = Gtk.Box(spacing=6)
        self.output_button = Gtk.Button(label="Select Output Directory")
        self.output_button.connect("clicked", self.on_output_directory_clicked)
        dir_box.pack_start(self.output_button, False, False, 0)
        self.output_label = Gtk.Label(label="Default: Same as input")
        dir_box.pack_start(self.output_label, True, True, 0)
        output_box.pack_start(dir_box, False, False, 0)

    def create_quality_tab(self):
        quality_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.notebook.append_page(quality_box, Gtk.Label(label="Quality"))

        # Quality Factor slider
        quality_label = Gtk.Label(label="Quality Factor:")
        quality_box.pack_start(quality_label, False, False, 0)
        self.quality_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.quality_scale.set_value(50)
        quality_box.pack_start(self.quality_scale, False, False, 0)

        # Bitrate selection
        bitrate_box = Gtk.Box(spacing=6)
        bitrate_label = Gtk.Label(label="Bitrate:")
        bitrate_box.pack_start(bitrate_label, False, False, 0)
        self.bitrate_combo = Gtk.ComboBoxText()
        bitrates = ["64k", "128k", "192k", "256k", "320k"]
        for br in bitrates:
            self.bitrate_combo.append_text(br)
        self.bitrate_combo.set_active(2)  # Default to 192k
        bitrate_box.pack_start(self.bitrate_combo, False, False, 0)
        quality_box.pack_start(bitrate_box, False, False, 0)

        # Sample rate selection
        samplerate_box = Gtk.Box(spacing=6)
        samplerate_label = Gtk.Label(label="Sample Rate:")
        samplerate_box.pack_start(samplerate_label, False, False, 0)
        self.samplerate_combo = Gtk.ComboBoxText()
        samplerates = ["22050", "44100", "48000", "96000"]
        for sr in samplerates:
            self.samplerate_combo.append_text(sr)
        self.samplerate_combo.set_active(1)  # Default to 44100
        samplerate_box.pack_start(self.samplerate_combo, False, False, 0)
        quality_box.pack_start(samplerate_box, False, False, 0)

        # Thread usage
        thread_box = Gtk.Box(spacing=6)
        thread_label = Gtk.Label(label="Threads:")
        thread_box.pack_start(thread_label, False, False, 0)
        self.thread_combo = Gtk.ComboBoxText()
        max_threads = os.cpu_count()
        for i in range(1, max_threads + 1):
            self.thread_combo.append_text(str(i))
        self.thread_combo.set_active(max_threads - 1)  # Default to max threads
        thread_box.pack_start(self.thread_combo, False, False, 0)
        quality_box.pack_start(thread_box, False, False, 0)

        # GPU acceleration
        self.gpu_check = Gtk.CheckButton(label="Use GPU acceleration (if available)")
        quality_box.pack_start(self.gpu_check, False, False, 0)

    def create_summary_tab(self):
        summary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.notebook.append_page(summary_box, Gtk.Label(label="Summary"))

        self.summary_text = Gtk.TextView()
        self.summary_text.set_editable(False)
        summary_scroll = Gtk.ScrolledWindow()
        summary_scroll.add(self.summary_text)
        summary_box.pack_start(summary_scroll, True, True, 0)

    def create_tags_tab(self):
        tags_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.notebook.append_page(tags_box, Gtk.Label(label="Tags"))

        self.tags_grid = Gtk.Grid()
        self.tags_grid.set_column_spacing(10)
        self.tags_grid.set_row_spacing(10)
        tags_box.pack_start(self.tags_grid, True, True, 0)

        self.tag_entries = {}
        tag_fields = ["Title", "Artist", "Album", "Year", "Genre", "Comment"]
        for i, field in enumerate(tag_fields):
            label = Gtk.Label(label=field)
            self.tags_grid.attach(label, 0, i, 1, 1)
            entry = Gtk.Entry()
            self.tags_grid.attach(entry, 1, i, 1, 1)
            self.tag_entries[field.lower()] = entry

        apply_button = Gtk.Button(label="Apply Tags")
        apply_button.connect("clicked", self.on_apply_tags_clicked)
        tags_box.pack_start(apply_button, False, False, 0)

    def create_log_tab(self):
        log_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.notebook.append_page(log_box, Gtk.Label(label="Log"))

        self.log_text = Gtk.TextView()
        self.log_text.set_editable(False)
        log_scroll = Gtk.ScrolledWindow()
        log_scroll.add(self.log_text)
        log_box.pack_start(log_scroll, True, True, 0)

        save_log_button = Gtk.Button(label="Save Log")
        save_log_button.connect("clicked", self.on_save_log_clicked)
        log_box.pack_start(save_log_button, False, False, 0)

    def create_transcode_button(self):
        transcode_box = Gtk.Box(spacing=6)
        self.transcode_button = Gtk.Button(label="Transcode")
        self.transcode_button.connect("clicked", self.on_transcode_clicked)
        transcode_box.pack_start(self.transcode_button, True, True, 0)

        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.connect("clicked", self.on_cancel_clicked)
        self.cancel_button.set_sensitive(False)
        transcode_box.pack_start(self.cancel_button, True, True, 0)

        self.file_progress = Gtk.ProgressBar()
        transcode_box.pack_start(self.file_progress, True, True, 0)

        self.overall_progress = Gtk.ProgressBar()
        transcode_box.pack_start(self.overall_progress, True, True, 0)

        self.add(transcode_box)

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        files = data.get_uris()
        for file_uri in files:
            file_path = self.uri_to_path(file_uri)
            if file_path and file_path not in self.input_files:
                self.input_files.append(file_path)
        self.update_file_list()

    def uri_to_path(self, uri):
        path = urllib.parse.unquote(uri)
        if path.startswith('file://'):
            return path[7:]
        return None

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

    def on_add_files_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose files", parent=self, action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        dialog.set_select_multiple(True)

        filter_media = Gtk.FileFilter()
        filter_media.set_name("Media files")
        filter_media.add_mime_type("audio/*")
        filter_media.add_mime_type("video/*")
        dialog.add_filter(filter_media)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_files = dialog.get_filenames()
            self.input_files.extend([f for f in new_files if f not in self.input_files])
            self.update_file_list()
        
        dialog.destroy()

    def on_remove_selected_clicked(self, widget):
        selected_row = self.file_list.get_selected_row()
        if selected_row:
            index = selected_row.get_index()
            del self.input_files[index]
            self.update_file_list()

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

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.output_directory = dialog.get_filename()
            self.output_label.set_text(self.output_directory)
        
        dialog.destroy()

    def on_apply_tags_clicked(self, widget):
        # Implementation for applying tags to selected files
        pass

    def on_save_log_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Save Log File",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        dialog.set_current_name("transcoder_log.txt")

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            buffer = self.log_text.get_buffer()
            text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
            with open(filename, 'w') as f:
                f.write(text)
        
        dialog.destroy()

    def on_transcode_clicked(self, widget):
        if not self.input_files:
            self.show_error_dialog("No input files selected")
            return

        self.is_transcoding = True
        self.transcode_button.set_sensitive(False)
        self.cancel_button.set_sensitive(True)
        self.transcode_thread = threading.Thread(target=self.transcode_files)
        self.transcode_thread.start()

    def transcode_files(self):
        total_files = len(self.input_files)
        input_files_copy = self.input_files.copy()  # Create a copy to preserve original list

        for i, input_file in enumerate(self.input_files):
            if not self.is_transcoding:
                break

            output_format = self.format_combo.get_active_text().lower()
            if output_format == "same as source":
                output_format = os.path.splitext(input_file)[1][1:]

            output_file = os.path.splitext(os.path.basename(input_file))[0] + "." + output_format
            if self.output_directory:
                output_file = os.path.join(self.output_directory, output_file)
            else:
                output_file = os.path.join(os.path.dirname(input_file), output_file)

            if os.path.exists(output_file):
                if not self.show_overwrite_dialog(output_file):
                    continue

            bitrate = self.bitrate_combo.get_active_text()
            samplerate = self.samplerate_combo.get_active_text()
            threads = self.thread_combo.get_active_text()
            quality = int(self.quality_scale.get_value())

            command = [
                "ffmpeg",
                "-i", input_file,
                "-y",  # Overwrite output file if it exists
                "-b:a", bitrate,
                "-ar", samplerate,
                "-threads", threads
            ]

            if self.gpu_check.get_active():
                command.extend(["-hwaccel", "auto"])

            if self.extract_audio_check.get_active():
                command.extend(["-vn"])

            # Add quality factor
            if output_format in ["mp3", "ogg", "aac"]:
                command.extend(["-q:a", str(quality / 10)])
            elif output_format in ["flac", "wav"]:
                command.extend(["-compression_level", str(quality // 10)])

            command.append(output_file)

            GLib.idle_add(self.log_message, f"Transcoding file {i + 1} of {total_files}: {input_file}")
            
            try:
                self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                while True:
                    output = self.process.stdout.readline()
                    if output == '' and self.process.poll() is not None:
                        break
                    if output:
                        self.update_progress(output, i, total_files)
                if self.process.returncode != 0:
                    GLib.idle_add(self.show_error_dialog, f"Error transcoding file: {input_file}")
            except Exception as e:
                GLib.idle_add(self.show_error_dialog, f"Error transcoding file: {input_file}\n{str(e)}")

            self.update_file_info(input_file)

        GLib.idle_add(self.finish_transcoding)

    def update_progress(self, output, current_file, total_files):
        # Use GLib.idle_add for all GUI updates to prevent freezing
        duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})", output)
        time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})", output)
        
        if duration_match:
            hours, minutes, seconds = map(float, duration_match.groups())
            self.total_duration = hours * 3600 + minutes * 60 + seconds
        
        if time_match:
            hours, minutes, seconds = map(float, time_match.groups())
            current_time = hours * 3600 + minutes * 60 + seconds
            if hasattr(self, 'total_duration') and self.total_duration > 0:
                file_progress = current_time / self.total_duration
                overall_progress = (current_file + file_progress) / total_files
                
                GLib.idle_add(self.file_progress.set_fraction, file_progress)
                GLib.idle_add(self.overall_progress.set_fraction, overall_progress)

    def update_file_info(self, file_path):
        command = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            info = f"File: {os.path.basename(file_path)}\n"
            info += f"Format: {data['format']['format_name']}\n"
            info += f"Duration: {data['format']['duration']} seconds\n"
            info += f"Size: {int(data['format']['size']) // 1024} KB\n"
            info += f"Bitrate: {data['format']['bit_rate']} bps\n"
            
            for stream in data['streams']:
                if stream['codec_type'] == 'audio':
                    info += f"Audio: {stream['codec_name']}, {stream['sample_rate']} Hz, {stream['channels']} channels\n"
                elif stream['codec_type'] == 'video':
                    info += f"Video: {stream['codec_name']}, {stream['width']}x{stream['height']}\n"
            
            creation_time = os.path.getctime(file_path)
            modification_time = os.path.getmtime(file_path)
            info += f"Created: {datetime.fromtimestamp(creation_time)}\n"
            info += f"Modified: {datetime.fromtimestamp(modification_time)}\n"
            
            GLib.idle_add(self.update_summary, info)
            GLib.idle_add(self.update_tags, data['format'].get('tags', {}))
        except subprocess.CalledProcessError:
            GLib.idle_add(self.show_error_dialog, f"Error getting info for file: {file_path}")
        except json.JSONDecodeError:
            GLib.idle_add(self.show_error_dialog, f"Error parsing info for file: {file_path}")

    def update_summary(self, info):
        buffer = self.summary_text.get_buffer()
        buffer.set_text(info)

    def update_tags(self, tags):
        for key, entry in self.tag_entries.items():
            entry.set_text(tags.get(key, ""))

    def finish_transcoding(self):
        self.is_transcoding = False
        self.transcode_button.set_sensitive(True)
        self.cancel_button.set_sensitive(False)
        self.log_message("Transcoding completed!")
        
        # Show completion dialog only once
        GLib.idle_add(self.show_completion_dialog)

    def show_completion_dialog(self):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Transcoding completed successfully!",
        )
        dialog.run()
        dialog.destroy()

    def on_cancel_clicked(self, widget):
        if self.is_transcoding:
            self.is_transcoding = False
            if self.process:
                self.process.terminate()
            self.log_message("Transcoding cancelled.")
            self.transcode_button.set_sensitive(True)
            self.cancel_button.set_sensitive(False)
            self.file_progress.set_fraction(0)
            self.overall_progress.set_fraction(0)

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

    def show_overwrite_dialog(self, file_path):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"File {file_path} already exists. Overwrite?",
        )
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    def log_message(self, message):
        buffer = self.log_text.get_buffer()
        end_iter = buffer.get_end_iter()
        buffer.insert(end_iter, message + "\n")
        self.log_text.scroll_to_iter(buffer.get_end_iter(), 0, False, 0, 0)

win = AudioVideoTranscoder()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
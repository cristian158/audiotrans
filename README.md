# AudioTranscoder

AudioTranscoder is a powerful yet user-friendly tool for transcoding audio files. It provides a simple GTK-based interface for easy drag-and-drop operations while offering advanced features for more specific needs.

## Features

- Audio transcoding to various formats (mp3, wav, ogg, aac, flac)
- Real-time progress tracking for both individual files and batch operations
- Configurable bitrate and sample rate settings
- Simple and intuitive interface with drag-and-drop support
- Disk space checking before transcoding
- FFmpeg validation and error handling
- Batch processing with proper thread management
- Detailed error reporting and logging

## Requirements

- Python 3.6+
- GTK 3.0
- FFmpeg

## Installation

1. Ensure you have Python 3.6 or higher installed
2. Install GTK 3.0 for your operating system
3. Install FFmpeg
4. Clone this repository
5. Install required Python packages: `pip install -r requirements.txt`

## Usage

Run the program with:
```bash
python at.py
```

Then use the GUI to:
1. Select input files (drag-and-drop or file chooser)
2. Choose output format and quality settings
3. Select output directory (optional)
4. Start transcoding

The program will show real-time progress for both the current file and the overall batch operation.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

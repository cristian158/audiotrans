# Audio Transcoder

## Version 1.0

A simple and user-friendly GUI application for transcoding audio files using FFmpeg.

## Features

- Select multiple input audio files
- Drag and drop support for adding files
- Choose output format (MP3, WAV, OGG, AAC, FLAC)
- Set custom bitrate and sample rate
- Select output directory
- Progress bar for transcoding process
- Cancel ongoing transcoding
- Error handling and informative dialogs

## Installation

1. Ensure you have Python 3.x installed on your system.
2. Install the required dependencies:
   ```
   pip install PyGObject
   ```
3. Install FFmpeg on your system:
   - For Ubuntu/Debian: `sudo apt-get install ffmpeg`
   - For macOS (using Homebrew): `brew install ffmpeg`
   - For Windows: Download from [FFmpeg official website](https://ffmpeg.org/download.html)
4. Clone this repository or download the source code.

## Usage

1. Run the script:
   ```
   python AudioTrans.py
   ```
2. Use the "Select Input Files" button to choose audio files for transcoding.
3. Optionally, drag and drop audio files into the application window.
4. Select the desired output format, bitrate, and sample rate.
5. Choose an output directory (optional, default is the same as input).
6. Click "Transcode" to start the process.
7. Monitor the progress and use the "Cancel" button if needed.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Acknowledgements

- [FFmpeg](https://ffmpeg.org/) for the powerful audio/video processing capabilities.
- [PyGObject](https://pygobject.readthedocs.io/) for the GTK+ 3 bindings for Python.

## Contact

For any questions or feedback, please open an issue on the GitHub repository.

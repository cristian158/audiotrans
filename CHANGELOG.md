# Changelog

All notable changes to this project will be documented in this file.

## [0.4] - 2024-04-28

### Added
- Real-time progress tracking for both individual files and batch operations
- Disk space checking before starting transcoding
- FFmpeg availability validation
- Improved error handling and logging
- Status bar showing current file being processed

### Fixed
- Progress bars not updating in real-time
- IndexError when completing file list
- Multiple success messages
- GUI freezing during transcoding
- Progress bar accuracy issues (120% and 0.0%)
- Thread safety issues in transcoding process

### Changed
- Improved thread management for better performance
- Enhanced progress monitoring system
- Better error reporting and user feedback
- Cleaner UI updates using GLib.idle_add

## [0.3] - 2024-03-26

### Fixed
- Overload of "successfully transcoded!" messages
- GUI Freezing During Transcoding: The main thread was blocked during transcoding operations, causing the GUI to freeze
- Moved the transcoding to a separate thread and using GLib.idle_add
- Progress bar updates

## [0.2] - 2024-03-15

### Added
- Video transcoding support
- Audio extraction from video files
- Quality Factor adjustment feature
- 'Summary' view for detailed file information
- 'Tags' view for metadata editing
- Total progress bar for batch operations
- Thread usage control
- Confirmation dialog for file overwrite prevention

### Changed
- Reorganized GUI into tabbed interface
- Enhanced error handling and logging system

### Fixed
- Issue with drag-and-drop not recognizing some file types
- Memory leak during long batch operations

## [0.1] - 2024-03-01

### Added
- Initial release with audio transcoding functionality
- Support for mp3, wav, ogg, aac, flac formats
- Drag-and-drop interface
- Basic progress tracking
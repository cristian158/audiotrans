# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2025-05-15
- 

### Fixed
- Overload of "successfully transcoded!" messages
- GUI Freezing During Transcoding: The main thread was blocked during transcoding operations, causing the GUI to freeze
- Moved the transcoding to a separate thread and using GLib.idle_add
- Progress bar updates




## [2.0.0] - 2024-05-15

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

## [1.0.0] - 2024-03-01

### Added
- Initial release with audio transcoding functionality
- Support for mp3, wav, ogg, aac, flac formats
- Drag-and-drop interface
- Basic progress tracking
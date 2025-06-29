#!/usr/bin/env python3
"""
YouTube Video Downloader with Trimming
A Python app to download YouTube videos in different resolutions with time-based trimming
"""

import os
import sys
import re
import yt_dlp
from pathlib import Path


class YouTubeDownloader:
    def __init__(self):
        self.download_path = Path("downloads")
        self.download_path.mkdir(exist_ok=True)

    def parse_time(self, time_str):
        """Parse time string (HH:MM:SS, MM:SS, or SS) to seconds"""
        if not time_str.strip():
            return None

        time_str = time_str.strip()

        # Handle different time formats
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 2:  # MM:SS
                try:
                    minutes, seconds = map(int, parts)
                    return minutes * 60 + seconds
                except ValueError:
                    return None
            elif len(parts) == 3:  # HH:MM:SS
                try:
                    hours, minutes, seconds = map(int, parts)
                    return hours * 3600 + minutes * 60 + seconds
                except ValueError:
                    return None
        else:  # Just seconds
            try:
                return int(time_str)
            except ValueError:
                return None

        return None

    def format_duration(self, seconds):
        """Convert seconds to HH:MM:SS format"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def get_trim_settings(self, duration):
        """Get trimming settings from user"""
        print(f"\n✂️  TRIMMING OPTIONS")
        print(f"Video duration: {self.format_duration(duration)}")
        print("Time format: HH:MM:SS, MM:SS, or SS (seconds)")
        print("Examples: 1:30 (1min 30sec), 0:45:30 (45min 30sec), 90 (90 seconds)")
        print("Leave blank to download full video")

        while True:
            start_input = input("\nStart time (leave blank for beginning): ").strip()
            end_input = input("End time (leave blank for end): ").strip()

            # Parse start time
            if start_input:
                start_time = self.parse_time(start_input)
                if start_time is None:
                    print("❌ Invalid start time format. Please try again.")
                    continue
                if start_time >= duration:
                    print(f"❌ Start time cannot be >= video duration ({self.format_duration(duration)})")
                    continue
            else:
                start_time = None

            # Parse end time
            if end_input:
                end_time = self.parse_time(end_input)
                if end_time is None:
                    print("❌ Invalid end time format. Please try again.")
                    continue
                if end_time > duration:
                    print(f"❌ End time cannot be > video duration ({self.format_duration(duration)})")
                    continue
                if start_time and end_time <= start_time:
                    print("❌ End time must be after start time.")
                    continue
            else:
                end_time = None

            # Confirm settings
            if start_time or end_time:
                start_str = self.format_duration(start_time) if start_time else "Beginning"
                end_str = self.format_duration(end_time) if end_time else "End"
                trim_duration = (end_time or duration) - (start_time or 0)

                print(f"\n📝 Trim Settings:")
                print(f"   From: {start_str}")
                print(f"   To: {end_str}")
                print(f"   Duration: {self.format_duration(trim_duration)}")

                confirm = input("\nConfirm these settings? (y/n): ").strip().lower()
                if confirm in ['y', 'yes']:
                    return start_time, end_time
                else:
                    continue
            else:
                return None, None

    def get_video_info(self, url):
        """Get video information and available formats"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            print(f"Error getting video info: {str(e)}")
            return None

    def get_available_formats(self, info):
        """Extract available video formats and resolutions"""
        formats = []
        seen_resolutions = set()

        if 'formats' in info:
            for f in info['formats']:
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':  # Has both video and audio
                    height = f.get('height')
                    if height and height not in seen_resolutions:
                        formats.append({
                            'format_id': f['format_id'],
                            'resolution': f"{height}p",
                            'height': height,
                            'ext': f.get('ext', 'mp4'),
                            'filesize': f.get('filesize', 'Unknown'),
                            'fps': f.get('fps', 'Unknown'),
                            'vcodec': f.get('vcodec', 'Unknown'),
                            'acodec': f.get('acodec', 'Unknown')
                        })
                        seen_resolutions.add(height)

        # Sort by resolution (highest first)
        formats.sort(key=lambda x: x['height'], reverse=True)
        return formats

    def format_filesize(self, size):
        """Convert bytes to human readable format"""
        if size == 'Unknown' or size is None:
            return "Unknown"

        try:
            size = int(size)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        except:
            return "Unknown"

    def display_formats(self, formats, title):
        """Display available formats to user"""
        print(f"\nVideo: {title}")
        print("=" * 60)
        print(f"{'#':<3} {'Resolution':<12} {'Format':<8} {'Size':<12} {'FPS':<6}")
        print("-" * 60)

        for i, fmt in enumerate(formats, 1):
            size_str = self.format_filesize(fmt['filesize'])
            fps_str = str(fmt['fps']) if fmt['fps'] != 'Unknown' else 'N/A'
            print(f"{i:<3} {fmt['resolution']:<12} {fmt['ext']:<8} {size_str:<12} {fps_str:<6}")

        print(f"{len(formats) + 1:<3} {'Audio Only':<12} {'mp3':<8} {'N/A':<12} {'N/A':<6}")
        print("-" * 60)

    def create_postprocessors(self, start_time, end_time):
        """Create FFmpeg postprocessors for trimming"""
        postprocessors = []

        if start_time is not None or end_time is not None:
            # FFmpeg options for trimming
            ffmpeg_args = []

            if start_time is not None:
                ffmpeg_args.extend(['-ss', str(start_time)])

            if end_time is not None:
                if start_time is not None:
                    duration = end_time - start_time
                    ffmpeg_args.extend(['-t', str(duration)])
                else:
                    ffmpeg_args.extend(['-to', str(end_time)])

            postprocessors.append({
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
                'when': 'after_video',
            })

            # Add custom FFmpeg args
            postprocessors.append({
                'key': 'FFmpegMetadata',
                'add_chapters': False,
            })

        return postprocessors, ffmpeg_args if start_time is not None or end_time is not None else []

    def download_video(self, url, format_choice, title, start_time=None, end_time=None):
        """Download video with selected format and optional trimming"""
        # Clean title for filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]  # Limit filename length

        # Add trim info to filename if trimming
        if start_time is not None or end_time is not None:
            start_str = f"{start_time}s" if start_time else "0s"
            end_str = f"{end_time}s" if end_time else "end"
            safe_title += f"_trim_{start_str}-{end_str}"

        # Create postprocessors and FFmpeg args
        postprocessors, ffmpeg_args = self.create_postprocessors(start_time, end_time)

        if format_choice == 'audio':
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(self.download_path / f'{safe_title}.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }

            # Add trimming for audio
            if ffmpeg_args:
                ydl_opts['postprocessor_args'] = {
                    'ffmpeg': ffmpeg_args
                }
        else:
            ydl_opts = {
                'format': format_choice,
                'outtmpl': str(self.download_path / f'{safe_title}.%(ext)s'),
            }

            # Add trimming postprocessors
            if postprocessors:
                ydl_opts['postprocessors'] = postprocessors

            # Add FFmpeg arguments for trimming
            if ffmpeg_args:
                ydl_opts['postprocessor_args'] = {
                    'ffmpeg': ffmpeg_args
                }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"\nDownloading to: {self.download_path.absolute()}")
                if start_time is not None or end_time is not None:
                    print("✂️  Trimming enabled - this may take longer...")
                print("Please wait...")
                ydl.download([url])
                print("✅ Download completed successfully!")
                return True
        except Exception as e:
            print(f"❌ Download failed: {str(e)}")
            print("💡 Note: Trimming requires FFmpeg to be installed")
            return False

    def run(self):
        """Main application loop"""
        print("🎥 YouTube Video Downloader with Trimming")
        print("=" * 50)
        print("📝 Features: Multiple resolutions, audio-only, video trimming")

        while True:
            try:
                # Get YouTube URL
                url = input("\nEnter YouTube URL (or 'quit' to exit): ").strip()

                if url.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye! 👋")
                    break

                if not url:
                    print("Please enter a valid URL.")
                    continue

                if 'youtube.com' not in url and 'youtu.be' not in url:
                    print("Please enter a valid YouTube URL.")
                    continue

                print("🔍 Getting video information...")

                # Get video info
                info = self.get_video_info(url)
                if not info:
                    print("❌ Could not retrieve video information. Please check the URL.")
                    continue

                title = info.get('title', 'Unknown Title')
                duration = info.get('duration', 0)
                uploader = info.get('uploader', 'Unknown')

                print(f"\n📹 Title: {title}")
                print(f"👤 Uploader: {uploader}")
                if duration:
                    print(f"⏱️  Duration: {self.format_duration(duration)}")

                # Get available formats
                formats = self.get_available_formats(info)

                if not formats:
                    print("❌ No suitable video formats found.")
                    continue

                # Display formats
                self.display_formats(formats, title)

                # Get user choice for format
                while True:
                    try:
                        choice = input(f"\nSelect format (1-{len(formats) + 1}): ").strip()
                        choice_num = int(choice)

                        if choice_num == len(formats) + 1:
                            # Audio only
                            selected_format = 'audio'
                            print("Selected: Audio Only (MP3)")
                            break
                        elif 1 <= choice_num <= len(formats):
                            selected_format = formats[choice_num - 1]['format_id']
                            selected_res = formats[choice_num - 1]['resolution']
                            print(f"Selected: {selected_res}")
                            break
                        else:
                            print(f"Please enter a number between 1 and {len(formats) + 1}")
                    except ValueError:
                        print("Please enter a valid number.")

                # Ask about trimming
                trim_choice = input("\nDo you want to trim the video? (y/n): ").strip().lower()

                start_time, end_time = None, None
                if trim_choice in ['y', 'yes']:
                    if duration:
                        start_time, end_time = self.get_trim_settings(duration)
                    else:
                        print("⚠️  Cannot trim - video duration unknown")

                # Download
                success = self.download_video(url, selected_format, title, start_time, end_time)

                if success:
                    continue_choice = input("\nDownload another video? (y/n): ").strip().lower()
                    if continue_choice not in ['y', 'yes']:
                        print("Goodbye! 👋")
                        break

            except KeyboardInterrupt:
                print("\n\nDownload interrupted by user.")
                break
            except Exception as e:
                print(f"An unexpected error occurred: {str(e)}")
                continue


def main():
    """Main function"""
    try:
        print("🔧 Checking dependencies...")

        # Check if FFmpeg is available for trimming
        import subprocess
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            print("✅ FFmpeg found - trimming enabled")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  FFmpeg not found - trimming will not work")
            print("   Install FFmpeg for trimming functionality")

        downloader = YouTubeDownloader()
        downloader.run()

    except ImportError:
        print("❌ Required library 'yt-dlp' not found.")
        print("Please install it using: pip install yt-dlp")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
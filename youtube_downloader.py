#!/usr/bin/env python3
"""
YouTube Video Downloader
A simple Python app to download YouTube videos in different resolutions
"""

import os
import sys
import yt_dlp
from pathlib import Path


class YouTubeDownloader:
    def __init__(self):
        self.download_path = Path("downloads")
        self.download_path.mkdir(exist_ok=True)

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

    def download_video(self, url, format_choice, title):
        """Download video with selected format"""
        # Clean title for filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]  # Limit filename length

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
        else:
            ydl_opts = {
                'format': format_choice,
                'outtmpl': str(self.download_path / f'{safe_title}.%(ext)s'),
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"\nDownloading to: {self.download_path.absolute()}")
                print("Please wait...")
                ydl.download([url])
                print("✅ Download completed successfully!")
                return True
        except Exception as e:
            print(f"❌ Download failed: {str(e)}")
            return False

    def run(self):
        """Main application loop"""
        print("🎥 YouTube Video Downloader")
        print("=" * 40)

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
                    minutes, seconds = divmod(duration, 60)
                    print(f"⏱️  Duration: {minutes:02d}:{seconds:02d}")

                # Get available formats
                formats = self.get_available_formats(info)

                if not formats:
                    print("❌ No suitable video formats found.")
                    continue

                # Display formats
                self.display_formats(formats, title)

                # Get user choice
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

                # Download
                success = self.download_video(url, selected_format, title)

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
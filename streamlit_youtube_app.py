#!/usr/bin/env python3
"""
Streamlit YouTube Video Downloader with Trimming
A web-based YouTube downloader with trimming functionality
"""

import streamlit as st
import os
import sys
import re
import yt_dlp
import subprocess
import tempfile
import zipfile
from pathlib import Path
import time
from datetime import datetime

# Configure Streamlit page
st.set_page_config(
    page_title="YouTube Downloader Pro",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)


class StreamlitYouTubeDownloader:
    def __init__(self):
        self.download_path = Path("downloads")
        self.download_path.mkdir(exist_ok=True)

        # Initialize session state
        if 'video_info' not in st.session_state:
            st.session_state.video_info = None
        if 'formats' not in st.session_state:
            st.session_state.formats = []
        if 'download_status' not in st.session_state:
            st.session_state.download_status = None

    def parse_time(self, time_str):
        """Parse time string (HH:MM:SS, MM:SS, or SS) to seconds"""
        if not time_str.strip():
            return None

        time_str = time_str.strip()

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
        if not seconds:
            return "Unknown"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

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
            st.error(f"Error getting video info: {str(e)}")
            return None

    def get_available_formats(self, info):
        """Extract available video formats and resolutions"""
        formats = []
        seen_resolutions = set()

        if 'formats' in info:
            for f in info['formats']:
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
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

    def create_download_options(self, formats):
        """Create download options for selectbox"""
        options = []

        # Add highest quality option first
        if formats:
            highest = formats[0]
            options.append(f"🎯 Highest Quality ({highest['resolution']}) - {highest['ext']}")

        # Add all format options
        for i, fmt in enumerate(formats):
            size_str = self.format_filesize(fmt['filesize'])
            fps_str = f"{fmt['fps']}fps" if fmt['fps'] != 'Unknown' else 'N/A'
            options.append(f"{fmt['resolution']} ({fmt['ext']}) - {size_str} - {fps_str}")

        # Add audio only option
        options.append("🎵 Audio Only (MP3)")

        return options

    def get_format_from_selection(self, selection, formats):
        """Get format_id from user selection"""
        if selection.startswith("🎯 Highest Quality"):
            return formats[0]['format_id'] if formats else None
        elif selection.startswith("🎵 Audio Only"):
            return 'audio'
        else:
            # Parse resolution from selection
            resolution = selection.split('(')[0].strip()
            for fmt in formats:
                if fmt['resolution'] == resolution:
                    return fmt['format_id']
        return None

    def download_video(self, url, format_choice, title, start_time=None, end_time=None, progress_callback=None):
        """Download video with selected format and optional trimming"""
        # Clean title for filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]

        # Add timestamp to filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = f"{safe_title}_{timestamp}"

        # Add trim info to filename if trimming
        if start_time is not None or end_time is not None:
            start_str = f"{start_time}s" if start_time else "0s"
            end_str = f"{end_time}s" if end_time else "end"
            safe_title += f"_trim_{start_str}-{end_str}"

        # Progress hook for Streamlit
        def progress_hook(d):
            if progress_callback and d['status'] == 'downloading':
                if 'total_bytes' in d:
                    progress = d['downloaded_bytes'] / d['total_bytes']
                    progress_callback(progress)
                elif 'total_bytes_estimate' in d:
                    progress = d['downloaded_bytes'] / d['total_bytes_estimate']
                    progress_callback(progress)

        if format_choice == 'audio':
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(self.download_path / f'{safe_title}.%(ext)s'),
                'progress_hooks': [progress_hook],
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
                'progress_hooks': [progress_hook],
            }

        # Add trimming options if specified
        if start_time is not None or end_time is not None:
            postprocessor_args = []

            if start_time is not None:
                postprocessor_args.extend(['-ss', str(start_time)])

            if end_time is not None:
                if start_time is not None:
                    duration = end_time - start_time
                    postprocessor_args.extend(['-t', str(duration)])
                else:
                    postprocessor_args.extend(['-to', str(end_time)])

            ydl_opts['postprocessor_args'] = {
                'ffmpeg': postprocessor_args
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find the downloaded file
            downloaded_files = list(self.download_path.glob(f"{safe_title}.*"))
            if downloaded_files:
                return downloaded_files[0]
            else:
                return None

        except Exception as e:
            st.error(f"Download failed: {str(e)}")
            return None

    def run_streamlit_app(self):
        """Main Streamlit application"""

        # Header
        st.title("🎥 YouTube Downloader Pro")
        st.markdown("---")

        # Sidebar for settings
        with st.sidebar:
            st.header("⚙️ Settings")

            # Check FFmpeg
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
                st.success("✅ FFmpeg installed - Trimming enabled")
                ffmpeg_available = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                st.warning("⚠️ FFmpeg not found - Trimming disabled")
                st.info("Install FFmpeg to enable video trimming")
                ffmpeg_available = False

            st.markdown("---")
            st.header("📊 Statistics")
            download_count = len(list(self.download_path.glob("*")))
            st.metric("Total Downloads", download_count)

        # Main content
        col1, col2 = st.columns([2, 1])

        with col1:
            st.header("📥 Download Video")

            # URL input
            url = st.text_input(
                "YouTube URL:",
                placeholder="https://www.youtube.com/watch?v=...",
                help="Enter a valid YouTube URL"
            )

            # Fetch video info button
            if st.button("🔍 Get Video Info", type="primary"):
                if url and ('youtube.com' in url or 'youtu.be' in url):
                    with st.spinner("Fetching video information..."):
                        info = self.get_video_info(url)
                        if info:
                            st.session_state.video_info = info
                            st.session_state.formats = self.get_available_formats(info)
                            st.success("✅ Video information loaded!")
                        else:
                            st.error("❌ Could not fetch video information")
                            st.session_state.video_info = None
                            st.session_state.formats = []
                else:
                    st.error("❌ Please enter a valid YouTube URL")

        with col2:
            if st.session_state.video_info:
                st.header("📹 Video Info")
                info = st.session_state.video_info

                # Display thumbnail
                thumbnail = info.get('thumbnail')
                if thumbnail:
                    st.image(thumbnail, width=300)

                # Video details
                st.write(f"**Title:** {info.get('title', 'Unknown')}")
                st.write(f"**Uploader:** {info.get('uploader', 'Unknown')}")
                st.write(f"**Duration:** {self.format_duration(info.get('duration', 0))}")
                st.write(f"**Views:** {info.get('view_count', 'Unknown'):,}" if info.get(
                    'view_count') else "**Views:** Unknown")

        # Download options (only show if video info is available)
        if st.session_state.video_info and st.session_state.formats:
            st.markdown("---")
            st.header("⚙️ Download Options")

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📺 Format Selection")

                # Create format options
                options = self.create_download_options(st.session_state.formats)
                selected_format = st.selectbox(
                    "Choose quality:",
                    options,
                    help="Select your preferred video quality or audio-only option"
                )

                # Show format details
                if selected_format.startswith("🎯 Highest Quality"):
                    fmt = st.session_state.formats[0]
                    st.info(f"📊 **{fmt['resolution']}** | {fmt['ext']} | {self.format_filesize(fmt['filesize'])}")
                elif not selected_format.startswith("🎵 Audio Only"):
                    resolution = selected_format.split('(')[0].strip()
                    for fmt in st.session_state.formats:
                        if fmt['resolution'] == resolution:
                            st.info(
                                f"📊 **{fmt['resolution']}** | {fmt['ext']} | {self.format_filesize(fmt['filesize'])}")
                            break
                else:
                    st.info("🎵 **Audio Only** | MP3 | ~3-5MB per minute")

            with col2:
                st.subheader("✂️ Trimming Options")

                enable_trim = st.checkbox("Enable trimming", disabled=not ffmpeg_available)

                if enable_trim and ffmpeg_available:
                    duration = st.session_state.video_info.get('duration', 0)

                    if duration:
                        st.write(f"**Video Duration:** {self.format_duration(duration)}")

                        # Time input columns
                        time_col1, time_col2 = st.columns(2)

                        with time_col1:
                            start_time_str = st.text_input(
                                "Start time:",
                                placeholder="0:30 or 30",
                                help="Format: MM:SS, HH:MM:SS, or seconds"
                            )

                        with time_col2:
                            end_time_str = st.text_input(
                                "End time:",
                                placeholder="2:30 or 150",
                                help="Format: MM:SS, HH:MM:SS, or seconds"
                            )

                        # Parse and validate times
                        start_time = self.parse_time(start_time_str) if start_time_str else None
                        end_time = self.parse_time(end_time_str) if end_time_str else None

                        # Show trim preview
                        if start_time is not None or end_time is not None:
                            start_display = self.format_duration(start_time) if start_time else "Beginning"
                            end_display = self.format_duration(end_time) if end_time else "End"
                            trim_duration = (end_time or duration) - (start_time or 0)

                            st.success(f"✂️ **Trim:** {start_display} → {end_display}")
                            st.info(f"📏 **Result Duration:** {self.format_duration(trim_duration)}")

                            # Validation
                            if start_time and start_time >= duration:
                                st.error("❌ Start time is beyond video duration")
                            elif end_time and end_time > duration:
                                st.error("❌ End time is beyond video duration")
                            elif start_time and end_time and end_time <= start_time:
                                st.error("❌ End time must be after start time")
                    else:
                        st.warning("⚠️ Video duration unknown - trimming may not work")
                        start_time, end_time = None, None
                else:
                    start_time, end_time = None, None

            # Download button
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 2, 1])

            with col2:
                if st.button("🚀 Download Video", type="primary", use_container_width=True):
                    format_id = self.get_format_from_selection(selected_format, st.session_state.formats)
                    title = st.session_state.video_info.get('title', 'Unknown')

                    # Validate trimming settings
                    trim_valid = True
                    if enable_trim and ffmpeg_available:
                        duration = st.session_state.video_info.get('duration', 0)
                        if start_time and start_time >= duration:
                            st.error("❌ Invalid start time")
                            trim_valid = False
                        elif end_time and end_time > duration:
                            st.error("❌ Invalid end time")
                            trim_valid = False
                        elif start_time and end_time and end_time <= start_time:
                            st.error("❌ Invalid time range")
                            trim_valid = False

                    if trim_valid:
                        # Create progress bar
                        progress_bar = st.progress(0)
                        status_text = st.empty()

                        def update_progress(progress):
                            progress_bar.progress(progress)
                            status_text.text(f"Downloading... {progress * 100:.1f}%")

                        status_text.text("Starting download...")

                        # Download the video
                        use_start_time = start_time if enable_trim and ffmpeg_available else None
                        use_end_time = end_time if enable_trim and ffmpeg_available else None

                        downloaded_file = self.download_video(
                            url, format_id, title,
                            use_start_time, use_end_time,
                            update_progress
                        )

                        if downloaded_file:
                            progress_bar.progress(1.0)
                            status_text.text("✅ Download completed!")

                            # Show download button
                            with open(downloaded_file, "rb") as file:
                                st.download_button(
                                    label="📥 Download File",
                                    data=file.read(),
                                    file_name=downloaded_file.name,
                                    mime="video/mp4" if format_id != 'audio' else "audio/mpeg",
                                    use_container_width=True
                                )

                            st.success(f"🎉 Successfully downloaded: {downloaded_file.name}")
                        else:
                            progress_bar.empty()
                            status_text.text("❌ Download failed")

        # Footer
        st.markdown("---")
        st.markdown(
            """
            <div style='text-align: center; color: #666;'>
                <p>🎥 YouTube Downloader Pro | Built with Streamlit & yt-dlp</p>
                <p><small>⚠️ Please respect copyright laws and YouTube's Terms of Service</small></p>
            </div>
            """,
            unsafe_allow_html=True
        )


def main():
    """Main function to run the Streamlit app"""
    try:
        downloader = StreamlitYouTubeDownloader()
        downloader.run_streamlit_app()
    except ImportError as e:
        st.error("❌ Required libraries not found")
        st.code("pip install streamlit yt-dlp", language="bash")
        st.stop()
    except Exception as e:
        st.error(f"Fatal error: {str(e)}")
        st.stop()


if __name__ == "__main__":
    main()
import os
import tempfile
import streamlit as st
import yt_dlp

st.set_page_config(page_title="MP4 Converter Engine", layout="centered")

st.title("MP4 Converter Engine")
st.write("Extract and convert media streams to MP4 using yt-dlp and ffmpeg.")

if "info" not in st.session_state:
    st.session_state.info = None
if "url" not in st.session_state:
    st.session_state.url = ""

url_input = st.text_input("Enter Media URL:", value=st.session_state.url, placeholder="https://...")

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.pornhub.com/",
}

if st.button("Fetch Media Info"):
    clean_url = url_input.strip()
    if not clean_url:
        st.error("Please enter a valid URL.")
    else:
        st.session_state.url = clean_url
        with st.spinner("Analyzing media stream..."):
            try:
                ydl_opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "extract_flat": False,
                    "nocheckcertificate": True,
                    "http_headers": BROWSER_HEADERS,
                    "impersonate": "chrome",
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(clean_url, download=False)
                    st.session_state.info = info
            except Exception as e:
                st.error(f"Failed to extract info: {str(e)}")
                st.session_state.info = None

if st.session_state.info:
    info = st.session_state.info
    st.divider()

    title = info.get("title", "Unknown Title")
    uploader = info.get("uploader", "Unknown Creator")
    duration = info.get("duration", 0)
    thumbnail = info.get("thumbnail", "")

    minutes = duration // 60
    seconds = duration % 60

    st.subheader(title)
    st.write(f"Uploader: {uploader} | Duration: {minutes}m {seconds}s")

    if thumbnail:
        st.image(thumbnail, use_container_width=True)

    raw_formats = info.get("formats", [])
    available_resolutions = []
    format_map = {}

    for f in reversed(raw_formats):
        height = f.get("height")
        fmt_id = f.get("format_id")
        ext = f.get("ext", "")
        if height and fmt_id and ext in ["mp4", "m3u8", "webm"]:
            res_label = f"{height}p"
            if res_label not in available_resolutions:
                available_resolutions.append(res_label)
                format_map[res_label] = fmt_id

    if not available_resolutions:
        available_resolutions = ["Best Available"]
        format_map["Best Available"] = "best"

    selected_res = st.selectbox("Select Quality:", available_resolutions)
    selected_fmt_id = format_map[selected_res]

    if st.button("Convert and Process MP4"):
        with st.spinner("Processing media with ffmpeg..."):
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    out_template = os.path.join(tmpdir, "%(title)s.%(ext)s")

                    if selected_fmt_id == "best":
                        fmt_spec = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                    else:
                        fmt_spec = f"{selected_fmt_id}+bestaudio/best"

                    ydl_opts_dl = {
                        "format": fmt_spec,
                        "outtmpl": out_template,
                        "merge_output_format": "mp4",
                        "quiet": True,
                        "no_warnings": True,
                        "nocheckcertificate": True,
                        "http_headers": BROWSER_HEADERS,
                        "impersonate": "chrome",
                    }

                    with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
                        dl_info = ydl.extract_info(st.session_state.url, download=True)
                        filename = ydl.prepare_filename(dl_info)

                        base, _ = os.path.splitext(filename)
                        mp4_filename = f"{base}.mp4"

                        target_file = mp4_filename if os.path.exists(mp4_filename) else filename

                        with open(target_file, "rb") as f:
                            file_bytes = f.read()

                        st.success("Conversion completed.")
                        st.download_button(
                            label="Download MP4 File",
                            data=file_bytes,
                            file_name=os.path.basename(target_file),
                            mime="video/mp4",
                        )
            except Exception as e:
                st.error(f"Error during processing: {str(e)}")

"""Client-side webcam widget: getUserMedia preview + optional periodic JPEG POST.

Runs entirely in the browser via an inline <script>, independent of Streamlit's rerun
cycle, so the capture loop keeps running between reruns instead of restarting each time.
"""
import json

import streamlit.components.v1 as components


def render_webcam(
    session_id: str | None = None,
    api_base: str | None = None,
    interval_ms: int = 2000,
    height: int = 300,
    video_height: int = 260,
    post_frames: bool = True,
):
    post_frames = post_frames and bool(session_id) and bool(api_base)

    capture_js = ""
    if post_frames:
        capture_js = f"""
          setInterval(function() {{
            if (video.videoWidth === 0) return;
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            canvas.toBlob(function(blob) {{
              if (!blob) return;
              var form = new FormData();
              form.append('frame', blob, 'frame.jpg');
              fetch({json.dumps(api_base)} + '/api/interview/' + {json.dumps(session_id)} + '/proctor/frame', {{
                method: 'POST',
                body: form,
              }}).catch(function() {{}});
            }}, 'image/jpeg', 0.7);
          }}, {interval_ms});
        """

    html = f"""
    <div style="width:100%;">
      <video id="cam" autoplay playsinline muted
             style="width:100%;height:{video_height}px;object-fit:cover;object-position:center;
                    border-radius:10px;background:#111;display:block;"></video>
      <canvas id="canvas" style="display:none;"></canvas>
      <div id="camStatus" style="font-size:12px;color:#888;margin-top:6px;">Requesting camera access…</div>
    </div>
    <script>
    (function() {{
      var video = document.getElementById('cam');
      var canvas = document.getElementById('canvas');
      var statusEl = document.getElementById('camStatus');

      navigator.mediaDevices.getUserMedia({{
        video: {{ width: {{ ideal: 640 }}, height: {{ ideal: 480 }} }},
        audio: false
      }})
        .then(function(stream) {{
          video.srcObject = stream;
          statusEl.textContent = 'Camera connected';
          statusEl.style.color = '#16a34a';
          {capture_js}
        }})
        .catch(function(err) {{
          statusEl.textContent = 'Camera not detected (' + err.message + ')';
          statusEl.style.color = '#dc2626';
        }});
    }})();
    </script>
    """
    components.html(html, height=height)

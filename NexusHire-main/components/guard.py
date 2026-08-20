"""Anti-cheat guard: fullscreen enforcement + tab-switch + copy detection.

Runs in its own small iframe (like webcam.py) and fires-and-forgets violation
reports straight to FastAPI via fetch, independent of Streamlit's rerun cycle.

Notes on browser mechanics:
- Tab-switch/minimize is detected via `visibilitychange` on the IFRAME's own
  document — per spec, a nested browsing context's visibility state mirrors its
  top-level context's, so this reliably reflects the actual tab, no cross-frame
  accesss needed.
- Fullscreen and copy-detection need the whole page (not just this small iframe)
  fullscreened / watched, so those reach into `window.parent.document`. That only
  works because Streamlit's component iframe is same-origin (srcdoc). It's wrapped
  in try/catch — if a browser blocks it, the button falls back to a text hint
  rather than failing silently.
"""
import json

import streamlit.components.v1 as components


def render_guard(session_id: str, api_base: str, height: int = 70):
    html = f"""
    <div style="text-align:center;">
      <button id="fsBtn" style="padding:10px 18px;border-radius:8px;border:none;
              background:#0f766e;color:white;font-weight:600;cursor:pointer;font-size:14px;">
        🖥️ Enter Fullscreen (required)
      </button>
      <div id="fsStatus" style="font-size:12px;color:#94a3b8;margin-top:6px;"></div>
    </div>
    <script>
    (function() {{
      var sessionId = {json.dumps(session_id)};
      var apiBase = {json.dumps(api_base)};
      var btn = document.getElementById('fsBtn');
      var statusEl = document.getElementById('fsStatus');
      var enteredOnce = false;

      function report(message) {{
        var form = new FormData();
        form.append('type', 'unfair_means');
        form.append('message', message);
        fetch(apiBase + '/api/interview/' + sessionId + '/violation', {{ method: 'POST', body: form }})
          .catch(function() {{}});
      }}

      btn.addEventListener('click', function() {{
        try {{
          var el = window.parent.document.documentElement;
          var req = el.requestFullscreen || el.webkitRequestFullscreen;
          Promise.resolve(req.call(el)).then(function() {{
            enteredOnce = true;
            btn.style.display = 'none';
            statusEl.textContent = 'Fullscreen mode active';
            statusEl.style.color = '#16a34a';
          }}).catch(function() {{
            statusEl.textContent = "Couldn't enter fullscreen automatically — press F11.";
            statusEl.style.color = '#b45309';
          }});
        }} catch (e) {{
          statusEl.textContent = "Couldn't enter fullscreen automatically — press F11.";
          statusEl.style.color = '#b45309';
        }}
      }});

      try {{
        window.parent.document.addEventListener('fullscreenchange', function() {{
          if (enteredOnce && !window.parent.document.fullscreenElement) {{
            statusEl.textContent = 'Warning: exited fullscreen';
            statusEl.style.color = '#dc2626';
            report('Candidate exited fullscreen mode');
          }}
        }});
      }} catch (e) {{}}

      document.addEventListener('visibilitychange', function() {{
        if (document.hidden) {{
          report('Candidate switched tabs or minimized the window');
        }}
      }});

      try {{
        window.parent.document.addEventListener('copy', function() {{
          report('Candidate attempted to copy interview content');
        }});
      }} catch (e) {{}}
    }})();
    </script>
    """
    components.html(html, height=height)

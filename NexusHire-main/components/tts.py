"""Speaks text via the browser's built-in SpeechSynthesis API.

Relies on Streamlit only reloading a components.html iframe when its HTML string
actually changes: as long as `text` is unchanged across reruns (e.g. during the
live screen's ~2s polling loop), the same iframe is reused and the <script> does
not re-execute, so the same question isn't spoken repeatedly.
"""
import json

import streamlit.components.v1 as components


def speak(text: str, rate: float = 1.0):
    if not text:
        return
    html = f"""
    <script>
    (function() {{
      if (!window.speechSynthesis) return;
      window.speechSynthesis.cancel();
      var utter = new SpeechSynthesisUtterance({json.dumps(text)});
      utter.rate = {rate};
      window.speechSynthesis.speak(utter);
    }})();
    </script>
    """
    components.html(html, height=0)

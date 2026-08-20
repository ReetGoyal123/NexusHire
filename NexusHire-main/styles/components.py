# styles/components.py
# Reusable HTML component builders for the NexusHire candidate flow.
#
# Trimmed down from the original draft: dropped the recruiter-dashboard-only
# pieces (sidebar_nav_recruiter, decorative SVG charts with hardcoded sample
# data) since there's no recruiter dashboard yet and the report screen uses
# real Plotly charts bound to real data instead. Add those back when the
# recruiter dashboard is actually built.


def _flatten(html: str) -> str:
    """Strips per-line indentation from a multi-line HTML template.

    Streamlit's markdown renderer treats a line indented >=4 spaces relative
    to its block's baseline as a CommonMark indented code block, so it prints
    the raw tags instead of rendering them. Templates built by nesting one
    f-string inside another (e.g. sidebar_brand's profile_html) end up with
    inconsistent indentation levels that trip this — flattening every line to
    the left margin makes the whole function immune to it regardless of how
    the Python source happens to be indented.
    """
    return "\n".join(line.strip() for line in html.strip("\n").splitlines())


def light_stat_card(icon: str, label: str, value: str, sub: str, sub_class: str = "", icon_bg: str = "rgba(15,118,110,0.08)") -> str:
    """Stat card used on the report screen (speech stats, warnings, etc.)."""
    sub_color = {
        "up":   "#16a34a",
        "down": "#dc2626",
        "warn": "#b45309",
    }.get(sub_class, "#64748b")
    return _flatten(f"""
    <div style="
        background:#ffffff; border:1.5px solid #e5e8eb;
        border-radius:16px; padding:20px 22px;
        box-shadow:0 2px 12px rgba(0,0,0,0.04);
        transition:box-shadow 0.2s, transform 0.2s;
        height:100%;
    ">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px;">
        <span style="font-size:11px; color:#94a3b8; font-weight:600; text-transform:uppercase; letter-spacing:0.6px;">{label}</span>
        <span style="width:36px;height:36px;border-radius:10px;background:{icon_bg};
                     display:inline-flex;align-items:center;justify-content:center;font-size:16px;">{icon}</span>
      </div>
      <div style="font-family:'Space Grotesk',sans-serif;font-size:30px;font-weight:700;
                  letter-spacing:-0.5px;color:#1a1f2b;margin-bottom:6px;line-height:1;">{value}</div>
      <div style="font-size:12px; color:{sub_color}; font-weight:500;">{sub}</div>
    </div>
    """)


def section_header(title: str, badge: str = "", badge_color: str = "#0f766e") -> str:
    badge_html = f'<span style="font-size:11px;font-weight:700;background:rgba(15,118,110,0.10);color:{badge_color};padding:3px 10px;border-radius:20px;">{badge}</span>' if badge else ""
    return _flatten(f"""
    <div class="nx-section-header">
      <div class="nx-section-title">{title}</div>
      {badge_html}
    </div>
    """)


def card_with_header(title: str, badge: str, body: str, badge_accent: str = "#0f766e") -> str:
    return _flatten(f"""
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;overflow:hidden;">
      <div style="padding:16px 22px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;">
        <span style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:15px;">{title}</span>
        <span style="font-size:11px;font-weight:700;background:rgba(15,118,110,0.1);color:{badge_accent};padding:3px 10px;border-radius:20px;">{badge}</span>
      </div>
      <div style="padding:18px 22px;">{body}</div>
    </div>
    """)


def pill(text: str, status: str) -> str:
    classes = {"selected": "pill-green", "rejected": "pill-red", "pending": "pill-amber", "live": "pill-teal"}
    cls = classes.get(status.lower(), "pill-teal")
    return f'<span class="pill {cls}">{text}</span>'


def sidebar_brand(step_label: str = "", name: str = "", email: str = "") -> str:
    """Persistent left-rail branding + current-step indicator shown across the
    candidate flow (details → setup → interview → report)."""
    initials = name[0].upper() if name else "•"
    profile_html = ""
    if name:
        # Normal document flow, not position:absolute — an absolutely
        # positioned "pin to bottom" only works reliably against a container
        # whose height is already the full sidebar; here it's just whatever
        # this page's content adds up to, which varies (short on the live
        # interview step), so "bottom:0" was landing right under the logo
        # instead of at the actual bottom.
        profile_html = f"""
        <div style="margin-top:24px;padding:16px 0 0;
                    border-top:1px solid rgba(255,255,255,0.07);">
          <div style="display:flex;align-items:center;gap:10px;padding:8px 12px;">
            <div style="width:36px;height:36px;border-radius:50%;
                        background:linear-gradient(135deg,#0f766e,#14b8a6);
                        display:flex;align-items:center;justify-content:center;
                        font-size:13px;font-weight:700;color:#fff;flex-shrink:0;">{initials}</div>
            <div style="min-width:0;">
              <div style="font-size:13px;font-weight:600;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>
              <div style="font-size:11px;color:rgba(255,255,255,0.4);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{email}</div>
            </div>
          </div>
        </div>
        """
    return _flatten(f"""
    <div style="padding:24px 0 0; font-family:'Inter',sans-serif;">
      <div style="padding:0 20px 20px; border-bottom:1px solid rgba(255,255,255,0.07);
                  display:flex; align-items:center; gap:10px; margin-bottom:20px;">
        <div style="width:36px;height:36px;background:linear-gradient(135deg,#0f766e,#14b8a6);
                    border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:17px;">🧠</div>
        <span style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:17px;color:#fff;">
          Nexus<span style="color:#5eead4;">Hire</span>
        </span>
      </div>
      <div style="padding:0 20px;">
        <div style="font-size:10px;letter-spacing:1.4px;color:rgba(255,255,255,0.3);
                    text-transform:uppercase;padding:0 4px 8px;font-weight:700;">Current step</div>
        <div style="font-size:14px;font-weight:600;color:#fff;padding:0 4px;">{step_label}</div>
      </div>
    </div>
    {profile_html}
    """)

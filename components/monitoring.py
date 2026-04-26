"""components/monitoring.py — Tab 2: Gantt + deadline check + alerts. Manager only."""
import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
import plotly.graph_objects as go
from datetime import date, timedelta
from auth.guards import require_role
from db import log_alert
from utils.alerts import compute_urgency, get_bottleneck, fire_mock_alerts
from utils.constants import TODAY

def render(milestones_df):
    if not require_role("Manager"): return
    st.markdown('''<div style="background:#E9EFF8;border:1px solid #003366;border-radius:8px;padding:10px 16px;margin-bottom:1rem;display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
      <span style="color:#003366;font-family:'IBM Plex Mono',monospace;font-size:0.8rem;">[Monitor] MONITORING ENGINE</span>
      <span style="color:#CDD4D9;font-size:0.75rem;">Simulated date: <strong style="color:#000000;">March 10, 2026</strong> &nbsp;·&nbsp; [OK] >7d &nbsp;[WARN] 3–7d &nbsp;[CRIT] <3d / overdue</span>
    </div>''', unsafe_allow_html=True)
    cb, _ = st.columns([1, 3])
    with cb: run_check = st.button("Run Deadline Check", type="primary", use_container_width=True)
    if milestones_df.empty: st.info("No milestones to monitor."); return
    milestones = []
    for _, r in milestones_df.iterrows():
        m = r.to_dict()
        if isinstance(m["target_date"], str): m["target_date"] = date.fromisoformat(m["target_date"])
        milestones.append(m)
    st.markdown('<div class="section-title">Gantt Timeline</div>', unsafe_allow_html=True)
    try: st.plotly_chart(_gantt(milestones), use_container_width=True)
    except Exception as e: st.warning(f"Gantt unavailable: {e}")
    st.markdown("---")
    st.markdown('<div class="section-title">Deadline Status</div>', unsafe_allow_html=True)
    to_alert, bottlenecks = [], []
    for m in milestones:
        info = compute_urgency(m["target_date"], m["status"])
        bn = get_bottleneck(m["name"], info["days"], m["status"])
        if bn: bottlenecks.append((m["name"], bn))
        bn_html = f'<div style="margin-top:8px;padding:6px 10px;background:#FFF8E1;border-left:3px solid #C8950C;border-radius:4px;font-size:0.75rem;color:#C8950C;">[Gear] <strong>Bottleneck:</strong> Possible cause: {bn}</div>' if bn else ""
        notes_html = f'<div style="font-size:0.73rem;color:#CDD4D9;margin-top:4px;">[Notes] {m["notes"]}</div>' if m.get("notes") else ""
        st.markdown(f"""
        <div style="background:#E9EFF8;border:1px solid {info['color']};border-left:4px solid {info['color']};border-radius:8px;padding:12px 16px;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
            <span style="font-weight:600;color:#000000;">{info['emoji']} {m['name']}</span>
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
              <span style="background:{info['color']}22;color:{info['color']};border:1px solid {info['color']};border-radius:20px;padding:2px 12px;font-size:0.75rem;font-family:'IBM Plex Mono',monospace;">{info['label']}</span>
              <span style="font-size:0.75rem;color:#CDD4D9;font-family:'IBM Plex Mono',monospace;">{m['target_date'].strftime('%d %b %Y')}</span>
            </div>
          </div>{notes_html}{bn_html}
        </div>""", unsafe_allow_html=True)
        if info["level"] in ("yellow","red") and m["status"] != "complete": to_alert.append(m)
    if run_check:
        st.markdown("---")
        st.markdown('<div class="section-title">Alert Dispatch Log</div>', unsafe_allow_html=True)
        if not to_alert:
            st.success("All milestones on track. No alerts triggered.")
        else:
            all_fired = []
            for m in to_alert:
                info = compute_urgency(m["target_date"], m["status"])
                fired = fire_mock_alerts(m["id"], m["name"], info["days"])
                for item in fired:
                    try: log_alert(m["id"], item["channel"], item["message"])
                    except: pass
                all_fired.extend(fired)
                ch_colors = {"WhatsApp":"#25d366","SMS":"#7dd3fc","Email":"#C8950C"}
            for item in all_fired:
                cc = ch_colors.get(item["channel"],"#CDD4D9")
                st.markdown(
                             f"<div style='background:#FFFFFF;border:1px solid #D6DADC;border-left:3px solid {cc};border-radius:6px;padding:8px 12px;margin-bottom:5px;font-family:\"IBM Plex Mono\",monospace;font-size:0.73rem;color:#000000;'><span style='color:{cc};font-weight:600;'>[{item['channel']}]</span>&nbsp;{item['message']}</div>",
                             unsafe_allow_html=True)
            st.info(f"📬 {len(all_fired)} mock alerts dispatched across {len(to_alert)} milestone(s). Replace fire_mock_alerts() with Twilio in production.")
        st.session_state.last_alert_run = TODAY.isoformat()
    if st.session_state.get("last_alert_run"): st.caption(f"Last check: {st.session_state.last_alert_run}")
    if bottlenecks:
        st.markdown("---")
        st.markdown('<div class="section-title">Bottleneck Summary</div>', unsafe_allow_html=True)
        for name, reason in bottlenecks: st.warning(f"**{name}** — Possible cause: {reason}")

def _gantt(milestones):
    proj_start = TODAY - timedelta(days=180)
    tasks, color_map = [], {"green":"#003366","yellow":"#C8950C","red":"#BF382A","complete":"#003366"}
    for m in milestones:
        td = m["target_date"]
        start_dt = proj_start + timedelta(days=max(m.get("offset_days",30)-30,0))
        info = compute_urgency(td, m["status"])
        tasks.append(dict(Task=m["name"],Start=start_dt.strftime("%Y-%m-%d"),Finish=td.strftime("%Y-%m-%d"),Resource=info["level"]))
    try:
        fig = ff.create_gantt(tasks,colors=color_map,index_col="Resource",show_colorbar=True,group_tasks=True,showgrid_x=True,showgrid_y=True,title="")
    except Exception as e:
        fig = go.Figure(); fig.add_annotation(text=f"Chart unavailable: {e}",x=0.5,y=0.5,xref="paper",yref="paper",showarrow=False,font=dict(color="#BF382A"))
    today_str = TODAY.strftime("%Y-%m-%d")
    fig.add_shape(type="line",x0=today_str,x1=today_str,y0=0,y1=1,xref="x",yref="paper",line=dict(color="#C8950C",width=2,dash="dash"))
    fig.add_annotation(x=today_str,y=1.02,xref="x",yref="paper",text=f"TODAY ({TODAY.strftime('%d %b %Y')})",showarrow=False,font=dict(color="#C8950C",size=11),xanchor="left")
    fig.update_layout(paper_bgcolor="#FFFFFF",plot_bgcolor="#E9EFF8",font=dict(color="#000000",family="IBM Plex Mono"),margin=dict(l=10,r=10,t=30,b=10),height=320,xaxis=dict(gridcolor="#D6DADC",color="#CDD4D9"),yaxis=dict(gridcolor="#D6DADC",color="#000000"),legend=dict(bgcolor="#E9EFF8",bordercolor="#D6DADC",borderwidth=1))
    return fig
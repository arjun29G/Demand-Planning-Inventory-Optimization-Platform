import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

POWERBI_COLORS = {
    "primary": "#118DFF",
    "secondary": "#12239E",
    "accent_orange": "#E66C37",
    "accent_purple": "#6B007B",
    "accent_yellow": "#F2C80F",
    "success": "#107C41",
    "warning": "#FFC83B",
    "danger": "#D83B01",
    "dark_bg": "#1F2421",
    "card_bg": "#2A3038",
    "light_card": "#FFFFFF",
    "text_dark": "#252423",
    "text_light": "#F3F2F1"
}

def apply_powerbi_theme():
    """
    Applies Power BI-style visual styling to Streamlit components.
    This is a Streamlit/Plotly theme — not a native Power BI (.pbix) dashboard.
    """
    st.markdown(
        """
        <style>
        /* Modern Font & Container */
        @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
        }

        /* Power BI Header Ribbon */
        .pbi-header {
            background: linear-gradient(90deg, #118DFF 0%, #12239E 100%);
            color: #FFFFFF;
            padding: 16px 24px;
            border-radius: 8px;
            margin-bottom: 24px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .pbi-header h1 {
            font-size: 24px;
            font-weight: 700;
            margin: 0;
            line-height: 1.3;
            color: #FFFFFF !important;
        }
        .pbi-header p {
            font-size: 13px;
            margin: 6px 0 0 0;
            opacity: 0.9;
            line-height: 1.4;
            color: #E1F0FF !important;
        }

        /* KPI Card Styling */
        .pbi-kpi-card {
            background: #FFFFFF;
            border: 1px solid #E1DFDD;
            border-top: 4px solid #118DFF;
            border-radius: 6px;
            padding: 14px 18px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
            margin-bottom: 12px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .pbi-kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        .pbi-kpi-title {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #605E5C;
            margin-bottom: 6px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .pbi-kpi-val {
            font-size: 24px;
            font-weight: 700;
            color: #201F1E;
            margin-bottom: 4px;
            line-height: 1.2;
        }
        .pbi-kpi-sub {
            font-size: 12px;
            font-weight: 600;
            line-height: 1.3;
        }
        .pbi-sub-positive { color: #107C41; }
        .pbi-sub-negative { color: #D83B01; }
        .pbi-sub-neutral { color: #605E5C; }

        /* Power BI Table & Dataframes */
        .stDataFrame {
            border: 1px solid #EDEBE9;
            border-radius: 6px;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #F8F9FA;
            border-right: 1px solid #E1DFDD;
        }
        
        /* Metric Badges */
        .badge-critical {
            background-color: #FDE8E8;
            color: #D83B01;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11px;
        }
        .badge-warning {
            background-color: #FFF8E1;
            color: #B78103;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11px;
        }
        .badge-success {
            background-color: #DEF7EC;
            color: #03543F;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def pbi_header(title: str, subtitle: str):
    apply_powerbi_theme()
    st.markdown(
        f"""
        <div class="pbi-header">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_kpi_card(title: str, value: str, subtitle: str = "", status: str = "neutral"):
    status_class = f"pbi-sub-{status}"
    st.markdown(
        f"""
        <div class="pbi-kpi-card">
            <div class="pbi-kpi-title" title="{title}">{title}</div>
            <div class="pbi-kpi-val">{value}</div>
            <div class="pbi-kpi-sub {status_class}">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def apply_plotly_pbi_theme(fig):
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Segoe UI, sans-serif", size=12, color="#201F1E"),
        title=dict(
            font=dict(size=14, color="#201F1E", family="Segoe UI, sans-serif"),
            x=0.0,
            xanchor="left",
            y=0.98,
            yanchor="top"
        ),
        margin=dict(l=40, r=40, t=90, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,249,250,0.5)"
    )
    return fig


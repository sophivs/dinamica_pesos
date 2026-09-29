import streamlit as st

def apply_styles():
    st.markdown(
        """
        <style>
        :root {
            --border: #e2e8f0;
            --text: #102a43;
            --muted: #64748b;
            --bg-card: #ffffff;
        }
    
        .stApp {
            background: #f5f8fc;
        }
    
        .block-container {
            max-width: 1800px;
            padding-top: 1.15rem;
            padding-bottom: 2rem;
        }
    
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid #dfe7f1;
        }
    
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
        }
    
        h1, h2, h3, h4 {
            color: #102a43;
        }
    
        .dashboard-header {
            background: linear-gradient(90deg, #073b74 0%, #0b5cad 55%, #168aad 100%);
            border-radius: 12px;
            padding: 1.15rem 1.4rem;
            margin-bottom: 1rem;
            color: white;
            box-shadow: 0 2px 8px rgba(15, 23, 42, .08);
        }
    
        .dashboard-header h1 {
            color: white;
            font-size: 1.75rem;
            margin: 0;
            font-weight: 700;
        }
    
        .dashboard-header p {
            color: rgba(255,255,255,.88);
            margin: .35rem 0 0 0;
            font-size: .95rem;
        }
    
        .section-label {
            font-size: 1.05rem;
            font-weight: 700;
            color: #102a43;
            margin: .8rem 0 .55rem;
        }
    
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: .9rem 1rem;
            min-height: 105px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, .04);
        }
    
        div[data-testid="stMetricLabel"] {
            color: #52677e;
            font-weight: 600;
        }
    
        div[data-testid="stMetricValue"] {
            color: #0b5cad;
            font-weight: 700;
        }
    
        [data-testid="stPlotlyChart"] {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: .35rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, .04);
        }
    
        div[data-testid="stDataFrame"] {
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            overflow: hidden;
        }
    
        .weight-total-ok {
            padding: .65rem .8rem;
            background: #ecfdf3;
            border: 1px solid #a7e8c4;
            border-radius: 8px;
            color: #087443;
            font-weight: 700;
        }
    
        .weight-total-bad {
            padding: .65rem .8rem;
            background: #fff1f2;
            border: 1px solid #fecdd3;
            border-radius: 8px;
            color: #b42318;
            font-weight: 700;
        }
    
        .sidebar-title {
            font-size: 1.15rem;
            font-weight: 800;
            color: #102a43;
            margin-bottom: .2rem;
        }
    
        .sidebar-subtitle {
            color: #64748b;
            font-size: .82rem;
            margin-bottom: 1rem;
        }
    
        .stTabs [data-baseweb="tab-list"] {
            gap: .4rem;
        }
    
        .stTabs [data-baseweb="tab"] {
            background: #eef4fb;
            border-radius: 7px 7px 0 0;
            padding-left: 1.3rem;
            padding-right: 1.3rem;
        }
    
        .stTabs [aria-selected="true"] {
            background: #0b5cad !important;
            color: white !important;
        }
    
        div.stButton > button,
        div.stDownloadButton > button {
            border-radius: 7px;
        }
    
        .info-strip {
            padding: .65rem .9rem;
            border: 1px solid #cbdff5;
            border-left: 4px solid #0b5cad;
            border-radius: 7px;
            background: #f0f7ff;
            color: #31516f;
            margin-bottom: .9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

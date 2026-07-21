"""
Streamlit Dashboard for AICF

Basic dashboard for managing content profiles and projects.
"""

import streamlit as st
import requests
from typing import Optional
import json

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"


def make_request(method: str, endpoint: str, data: Optional[dict] = None) -> dict:
    """Make HTTP request to the API."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return {}


st.set_page_config(
    page_title="AICF Dashboard",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 AICF - AI Content Factory")
st.markdown("---")

# Sidebar navigation
menu = st.sidebar.selectbox(
    "Navigation",
    ["Dashboard", "Content Profiles", "Projects", "Workflow Status", "Settings"]
)

# ============== Dashboard Home ==============
if menu == "Dashboard":
    st.header("Overview")
    
    # Quick stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        profiles = make_request("GET", "/profiles")
        st.metric("Active Profiles", len(profiles))
    
    with col2:
        projects = make_request("GET", "/projects")
        st.metric("Total Projects", len(projects))
    
    with col3:
        # Count in-progress projects
        in_progress = sum(1 for p in projects if p.get("status") == "in_progress")
        st.metric("In Progress", in_progress)
    
    st.markdown("---")
    st.info("Welcome to AICF! Use the sidebar to manage your content profiles and projects.")

# ============== Content Profiles ==============
elif menu == "Content Profiles":
    st.header("Content Profiles")
    
    tab1, tab2 = st.tabs(["View Profiles", "Create Profile"])
    
    with tab1:
        st.subheader("Existing Profiles")
        profiles = make_request("GET", "/profiles")
        
        if profiles:
            for profile in profiles:
                with st.expander(f"📺 {profile['name']}"):
                    st.write(f"**Niche:** {profile.get('niche', 'Not specified')}")
                    st.write(f"**Target Audience:** {profile.get('target_audience', 'Not specified')}")
                    st.write(f"**Visual Style:** {profile.get('visual_style', 'Not specified')}")
                    st.write(f"**Aspect Ratio:** {profile.get('aspect_ratio', '16:9')}")
                    st.write(f"**Language:** {profile.get('language', 'English')}")
                    
                    if profile.get('hashtags'):
                        st.write(f"**Hashtags:** {', '.join(profile['hashtags'])}")
                    
                    if profile.get('forbidden_elements'):
                        st.write(f"**Forbidden:** {', '.join(profile['forbidden_elements'])}")
                    
                    st.caption(f"Created: {profile.get('created_at', 'Unknown')}")
        else:
            st.warning("No profiles found. Create one in the 'Create Profile' tab.")
    
    with tab2:
        st.subheader("Create New Profile")
        
        with st.form("create_profile_form"):
            name = st.text_input("Channel Name *", max_chars=255)
            description = st.text_area("Description")
            niche = st.text_input("Niche")
            target_audience = st.text_area("Target Audience")
            
            col1, col2 = st.columns(2)
            with col1:
                visual_style = st.text_input("Visual Style")
                aspect_ratio = st.selectbox("Aspect Ratio", ["16:9", "9:16", "1:1", "4:5"])
                language = st.text_input("Language", value="English")
            
            with col2:
                music_style = st.text_input("Music Style")
                video_duration = st.text_input("Video Duration (e.g., '10 minutes')")
                hashtags_str = st.text_input("Hashtags (comma-separated)")
            
            forbidden_str = st.text_input("Forbidden Elements (comma-separated)")
            storytelling_rules = st.text_area("Storytelling Rules")
            
            submitted = st.form_submit_button("Create Profile")
            
            if submitted:
                if not name:
                    st.error("Channel name is required")
                else:
                    profile_data = {
                        "name": name,
                        "description": description,
                        "niche": niche,
                        "target_audience": target_audience,
                        "visual_style": visual_style,
                        "aspect_ratio": aspect_ratio,
                        "language": language,
                        "music_style": music_style,
                        "video_duration": video_duration,
                        "hashtags": [h.strip() for h in hashtags_str.split(",")] if hashtags_str else [],
                        "forbidden_elements": [f.strip() for f in forbidden_str.split(",")] if forbidden_str else [],
                        "storytelling_rules": storytelling_rules
                    }
                    
                    result = make_request("POST", "/profiles", profile_data)
                    
                    if result:
                        st.success(f"Profile '{name}' created successfully!")
                        st.rerun()

# ============== Projects ==============
elif menu == "Projects":
    st.header("Projects")
    
    tab1, tab2 = st.tabs(["View Projects", "Create Project"])
    
    with tab1:
        st.subheader("Existing Projects")
        
        # Get profiles for selection
        profiles = make_request("GET", "/profiles")
        profile_filter = st.selectbox(
            "Filter by Profile",
            ["All"] + [p["name"] for p in profiles]
        )
        
        # Get projects
        projects = make_request("GET", "/projects")
        
        if projects:
            # Filter if needed
            if profile_filter != "All":
                profile_id_map = {p["name"]: p["id"] for p in profiles}
                filter_id = profile_id_map.get(profile_filter)
                projects = [p for p in projects if p.get("profile_id") == filter_id]
            
            for project in projects:
                status_emoji = {
                    "pending": "⏳",
                    "in_progress": "🔄",
                    "completed": "✅",
                    "failed": "❌",
                    "cancelled": "🚫"
                }.get(project.get("status"), "📄")
                
                with st.expander(f"{status_emoji} {project['title']}"):
                    st.write(f"**Status:** {project.get('status', 'unknown')}")
                    st.write(f"**Current Stage:** {project.get('current_stage', 'idea')}")
                    st.write(f"**Profile ID:** {project.get('profile_id')}")
                    
                    if project.get('idea'):
                        st.write("**Idea:**")
                        st.write(project['idea'])
                    
                    if project.get('script'):
                        st.write("**Script:**")
                        st.write(project['script'][:500] + "..." if len(project['script']) > 500 else project['script'])
                    
                    st.caption(f"Created: {project.get('created_at', 'Unknown')}")
        else:
            st.warning("No projects found. Create one in the 'Create Project' tab.")
    
    with tab2:
        st.subheader("Create New Project")
        
        profiles = make_request("GET", "/profiles")
        
        if not profiles:
            st.error("No content profiles found. Please create a profile first.")
        else:
            with st.form("create_project_form"):
                title = st.text_input("Project Title *", max_chars=500)
                description = st.text_area("Description")
                
                profile_options = {p["name"]: p["id"] for p in profiles}
                selected_profile = st.selectbox("Content Profile *", list(profile_options.keys()))
                
                submitted = st.form_submit_button("Create Project")
                
                if submitted:
                    if not title:
                        st.error("Project title is required")
                    else:
                        project_data = {
                            "title": title,
                            "description": description,
                            "profile_id": profile_options[selected_profile]
                        }
                        
                        result = make_request("POST", "/projects", project_data)
                        
                        if result:
                            st.success(f"Project '{title}' created successfully!")
                            st.rerun()

# ============== Workflow Status ==============
elif menu == "Workflow Status":
    st.header("Workflow Status")
    
    projects = make_request("GET", "/projects")
    
    if not projects:
        st.warning("No projects found.")
    else:
        selected_project = st.selectbox(
            "Select Project",
            [f"{p['id']}: {p['title']}" for p in projects]
        )
        
        if selected_project:
            project_id = int(selected_project.split(":")[0])
            
            workflow = make_request("GET", f"/projects/{project_id}/workflow")
            
            if workflow:
                st.subheader(f"Workflow: {workflow.get('project_title')}")
                
                # Overall status
                status_col, stage_col = st.columns(2)
                with status_col:
                    st.metric("Overall Status", workflow.get('overall_status'))
                with stage_col:
                    st.metric("Current Stage", workflow.get('current_stage'))
                
                st.markdown("---")
                st.subheader("Stage Details")
                
                stages = workflow.get('stages', [])
                for stage in stages:
                    status_emoji = {
                        "pending": "⏳",
                        "in_progress": "🔄",
                        "completed": "✅",
                        "failed": "❌",
                        "cancelled": "🚫"
                    }.get(stage.get('status'), "📄")
                    
                    with st.expander(f"{status_emoji} {stage.get('stage_type')}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Agent:** {stage.get('agent_name', 'Not assigned')}")
                            st.write(f"**Status:** {stage.get('status')}")
                        with col2:
                            if stage.get('duration_seconds'):
                                st.write(f"**Duration:** {stage['duration_seconds']:.2f}s")
                            if stage.get('started_at'):
                                st.write(f"**Started:** {stage['started_at']}")
                        
                        if stage.get('error_message'):
                            st.error(f"Error: {stage['error_message']}")

# ============== Settings ==============
elif menu == "Settings":
    st.header("Settings")
    
    st.info("Configuration settings will be available here.")
    
    # Health check
    st.subheader("System Status")
    health = make_request("GET", "/health")
    
    if health:
        st.success(f"✅ {health.get('message', 'API is running')}")
    else:
        st.error("❌ Cannot connect to API. Make sure the backend is running.")

# Footer
st.markdown("---")
st.caption("AICF v0.1.0 | AI Content Factory")

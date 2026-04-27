import streamlit as st
import streamlit.components.v1 as components
import os

def render_sidebar_nav() -> None:
    try:
        with st.sidebar:
            st.page_link("app.py", label="🏠 Home")
            st.page_link("pages/0_🔐_Auth.py", label="🔐 Auth")
            st.page_link("pages/3_⭐_Recommender.py", label="⭐ Recommender")
    except Exception:
        pass

def render_heartbeat(user_id: int, movie_id: int = None) -> None:
    """
    Injects a small JavaScript snippet that sends a 'heartbeat' activity to the backend
    every 30 seconds to track dwell time.
    """
    if not user_id:
        return

    api_base = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    m_id = int(movie_id) if movie_id else "null"
    
    # We use a unique key for the component based on the movie_id to ensure it resets when the page changes
    component_key = f"heartbeat_{user_id}_{m_id}"
    
    js_code = f"""
    <script>
    (function() {{
        const userId = {user_id};
        const movieId = {m_id};
        const apiBase = "{api_base}";
        const interval = 30000; // 30 seconds
        
        console.log("Heartbeat started for user " + userId + " on movie " + movieId);
        
        const sendHeartbeat = () => {{
            fetch(`${{apiBase}}/users/${{userId}}/activities`, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    activity_type: 'heartbeat',
                    movie_id: movieId,
                    details: 'staying_on_page'
                }})
            }}).catch(err => console.error("Heartbeat failed", err));
        }};

        // Send initial heartbeat
        sendHeartbeat();
        
        // Setup interval
        setInterval(sendHeartbeat, interval);
    }})();
    </script>
    """
    
    # Render the JS in a hidden 0x0 iframe
    components.html(js_code, height=0, width=0)

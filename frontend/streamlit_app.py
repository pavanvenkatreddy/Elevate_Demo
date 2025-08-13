"""
Main Streamlit application for Elevate Charter AI.
"""

import os
import streamlit as st
from components import StatusIndicator, QuoteForm, QuoteDisplay, ChatInterface


def main():
    """Main application entry point."""
    # Configuration
    st.set_page_config(page_title="Elevate Charter AI", page_icon="✈️")
    
    # Environment setup
    BACKEND_URL = os.environ.get("BACKEND_URL", "https://pavanvenkat.pythonanywhere.com")
    
    # Header
    st.title("Elevate Charter AI ✈️")
    st.caption("Two‑mode demo: manual form & chat agent")
    
    # Status indicator
    status = StatusIndicator.render(BACKEND_URL)
    st.info(f"**Status**: {status}")
    
    # Mode selection
    mode = st.toggle("Chat mode (agent)")
    
    if not mode:
        # Manual quote mode
        form_data = QuoteForm.render()
        
        if form_data:
            # Process quote request
            try:
                import requests
                r = requests.post(f"{BACKEND_URL}/api/quote/", json=form_data, timeout=10)
                
                if r.status_code == 200:
                    data = r.json()
                    
                    # Display quote results
                    QuoteDisplay.render_trip_summary(data)
                    QuoteDisplay.render_recommended_aircraft(data)
                    st.divider()
                    QuoteDisplay.render_aircraft_options(data)
                    QuoteDisplay.render_comparison_table(data)
                    
                else:
                    st.error(f"Backend error {r.status_code}: {r.text}")
                    
            except Exception as e:
                st.error(f"Failed to reach backend: {e}")
    
    else:
        # Chat mode
        ChatInterface.render(BACKEND_URL)


if __name__ == "__main__":
    main()

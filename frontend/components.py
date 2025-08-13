"""
Frontend UI components for the Elevate Charter application.
"""

import streamlit as st
from typing import Dict, Any, List
from datetime import date


class StatusIndicator:
    """Component for displaying system status."""
    
    @staticmethod
    def render(backend_url: str) -> str:
        """Render the status indicator and return status."""
        try:
            import requests
            status_response = requests.get(f"{backend_url}/api/status/", timeout=5)
            if status_response.status_code == 200:
                return "🟢 OpenAI Enabled"
            else:
                return "🔴 OpenAI Disabled"
        except:
            return "🔴 Backend Unreachable"


class QuoteForm:
    """Component for the manual quote form."""
    
    @staticmethod
    def render() -> Dict[str, Any]:
        """Render the quote form and return form data."""
        st.subheader("Mode 1 — Manual Quote")
        
        with st.form("quote_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                origin = st.text_input("Origin (city or IATA)", value="New York")
                dep = st.date_input("Departure date", value=date.today())
                pax = st.number_input("Passengers", min_value=1, max_value=16, value=4)
            
            with col2:
                destination = st.text_input("Destination (city or IATA)", value="Miami")
                ret_enabled = st.checkbox("Return trip")
                ret = st.date_input("Return date", value=date.today(), disabled=not ret_enabled)
            
            submitted = st.form_submit_button("Get Quote")
            
            if submitted:
                form_data = {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": dep.isoformat(),
                    "passengers": int(pax),
                }
                
                if ret_enabled:
                    form_data["return_date"] = ret.isoformat()
                
                return form_data
        
        return None


class QuoteDisplay:
    """Component for displaying quote results."""
    
    @staticmethod
    def render_trip_summary(data: Dict[str, Any]):
        """Render the trip summary section."""
        st.success(f"**Trip Summary**: {data['itinerary']['origin']} → {data['itinerary']['destination']}")
        st.info(f"**Distance**: {data['itinerary']['distance_nm']} nm | **Passengers**: {data['itinerary']['passengers']}")
    
    @staticmethod
    def render_recommended_aircraft(data: Dict[str, Any]):
        """Render the recommended aircraft section."""
        recommended = data['recommended_aircraft']
        st.subheader("🏆 Recommended Aircraft")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Aircraft Type", recommended['type'])
        with col2:
            st.metric("Capacity", f"{recommended['capacity']} pax")
        with col3:
            st.metric("Total Price", f"${recommended['total_price_usd']:,.0f}")
        with col4:
            if data['itinerary'].get('return_date'):
                st.metric("Trip Type", "Round Trip")
            else:
                st.metric("Trip Type", "One Way")
    
    @staticmethod
    def render_aircraft_options(data: Dict[str, Any]):
        """Render all aircraft options."""
        st.subheader("🛩️ All Aircraft Options")
        
        for i, aircraft in enumerate(data['aircraft_options']):
            QuoteDisplay._render_aircraft_option(aircraft, data, i)
            st.divider()
    
    @staticmethod
    def _render_aircraft_option(aircraft: Dict[str, Any], data: Dict[str, Any], index: int):
        """Render a single aircraft option."""
        # Create columns for aircraft comparison
        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 2])
        
        with col1:
            # Aircraft type with recommendation badge
            if aircraft['recommended']:
                st.markdown(f"**{aircraft['aircraft_type']}** 🏆 *Recommended*")
            else:
                st.markdown(f"**{aircraft['aircraft_type']}**")
            st.caption(f"Capacity: {aircraft['capacity']} pax")
            st.caption(f"Range: {aircraft['range_nm']} nm | Speed: {aircraft['cruise_speed']} kts")
            st.caption(f"Amenities: {aircraft['amenities']}")
        
        with col2:
            st.metric("Total Price", f"${aircraft['total_price_usd']:,.0f}")
        
        with col3:
            st.metric("Base Rate", f"${aircraft['base_nm_rate']}/nm")
        
        with col4:
            # Show price difference from recommended
            if aircraft['recommended']:
                st.metric("Price Diff", "—")
            else:
                recommended_price = data['recommended_aircraft']['total_price_usd']
                diff = aircraft['total_price_usd'] - recommended_price
                st.metric("Price Diff", f"{diff:+,.0f}")
        
        with col5:
            # Flight time estimate
            distance = data['itinerary']['distance_nm']
            speed = aircraft['cruise_speed']
            flight_time = distance / speed * 1.15  # Include climb/descent time
            st.metric("Flight Time", f"{flight_time:.1f} hrs")
        
        # Expandable details
        QuoteDisplay._render_aircraft_details(aircraft, data, index)
    
    @staticmethod
    def _render_aircraft_details(aircraft: Dict[str, Any], data: Dict[str, Any], index: int):
        """Render expandable aircraft details."""
        with st.expander(f"📋 {aircraft['aircraft_type']} Details"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Aircraft Specifications**")
                st.write(f"**Type**: {aircraft['aircraft_type']}")
                st.write(f"**Capacity**: {aircraft['capacity']} passengers")
                st.write(f"**Range**: {aircraft['range_nm']} nautical miles")
                st.write(f"**Cruise Speed**: {aircraft['cruise_speed']} knots")
                st.write(f"**Amenities**: {aircraft['amenities']}")
                st.write(f"**Base Rate**: ${aircraft['base_nm_rate']}/nm")
            
            with col2:
                st.write("**Route Information**")
                st.write(f"**Origin**: {data['itinerary']['origin']}")
                st.write(f"**Destination**: {data['itinerary']['destination']}")
                st.write(f"**Distance**: {data['itinerary']['distance_nm']} nm")
                st.write(f"**Passengers**: {data['itinerary']['passengers']}")
                if data['itinerary'].get('return_date'):
                    st.write(f"**Return Date**: {data['itinerary']['return_date']}")
                    st.write("**Trip Type**: Round Trip")
                else:
                    st.write("**Trip Type**: One Way")
            
            st.divider()
            
            # Pricing breakdown
            QuoteDisplay._render_pricing_breakdown(aircraft)
            
            # Aircraft selection button
            if st.button(f"Select {aircraft['aircraft_type']}", key=f"select_{index}"):
                st.success(f"✅ {aircraft['aircraft_type']} selected for your charter!")
    
    @staticmethod
    def _render_pricing_breakdown(aircraft: Dict[str, Any]):
        """Render pricing breakdown for an aircraft."""
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Outbound Leg**")
            leg = aircraft['outbound_leg']
            st.write(f"Route: {leg['from']} → {leg['to']}")
            st.write(f"Distance: {leg['distance_nm']} nm")
            pricing = leg['pricing']
            st.write(f"Base Cost: ${pricing['base_cost']:,.0f}")
            st.write(f"Fees: ${pricing['fees']['landing_fee'] + pricing['fees']['segment_fee']:,.0f}")
            st.write(f"Multipliers: Lead {pricing['multipliers']['lead_time']} × Weekend {pricing['multipliers']['weekend']}")
            st.write(f"Taxes: ${pricing['taxes']:,.0f}")
            st.write(f"**Leg Total: ${pricing['total_usd']:,.0f}**")
        
        if aircraft['return_leg']:
            with col2:
                st.write("**Return Leg**")
                leg = aircraft['return_leg']
                st.write(f"Route: {leg['from']} → {leg['to']}")
                st.write(f"Distance: {leg['distance_nm']} nm")
                pricing = leg['pricing']
                st.write(f"Base Cost: ${pricing['base_cost']:,.0f}")
                st.write(f"Fees: ${pricing['fees']['landing_fee'] + pricing['fees']['segment_fee']:,.0f}")
                st.write(f"Multipliers: Lead {pricing['multipliers']['lead_time']} × Weekend {pricing['multipliers']['weekend']}")
                st.write(f"Taxes: ${pricing['taxes']:,.0f}")
                st.write(f"**Leg Total: ${pricing['total_usd']:,.0f}**")
        
        # Total summary
        st.divider()
        st.success(f"**Total Charter Price: ${aircraft['total_price_usd']:,.0f} USD**")
    
    @staticmethod
    def render_comparison_table(data: Dict[str, Any]):
        """Render the quick comparison table."""
        st.subheader("📊 Quick Comparison")
        
        comparison_data = []
        for ac in data['aircraft_options']:
            comparison_data.append({
                "Aircraft": ac['aircraft_type'],
                "Capacity": ac['capacity'],
                "Range (nm)": ac['range_nm'],
                "Speed (kts)": ac['cruise_speed'],
                "Total Price": f"${ac['total_price_usd']:,.0f}",
                "Base Rate": f"${ac['base_nm_rate']}/nm",
                "Recommended": "🏆 Yes" if ac['recommended'] else "No"
            })
        
        st.dataframe(comparison_data, use_container_width=True)


class ChatInterface:
    """Component for the chat-based quote interface."""
    
    @staticmethod
    def render(backend_url: str):
        """Render the chat interface."""
        st.subheader("Mode 2 — Chat Agent")
        
        if "chat" not in st.session_state:
            st.session_state.chat = []
        
        # Display chat history
        for role, msg in st.session_state.chat:
            with st.chat_message(role):
                st.markdown(msg)
        
        # Chat input
        prompt = st.chat_input("Describe your trip… e.g. 'Need a jet from New York to Miami on Friday for 6, return Monday'")
        if prompt:
            ChatInterface._process_chat_message(prompt, backend_url)
        
        # Chat controls
        if st.session_state.chat:
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🗑️ Clear Chat"):
                    st.session_state.chat = []
                    st.rerun()
            with col2:
                st.caption("💡 **Tip**: Try natural language like 'I need a jet for 4 people from LA to Vegas next weekend'")
    
    @staticmethod
    def _process_chat_message(prompt: str, backend_url: str):
        """Process a chat message and update the interface."""
        # Add user message to chat
        st.session_state.chat.append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Prepare conversation history for backend
        conversation_history = []
        for role, msg in st.session_state.chat[:-1]:  # Exclude current message
            conversation_history.append({"role": role, "content": msg})
        
        # Show assistant is typing
        with st.chat_message("assistant"):
            with st.spinner("Getting your quote..."):
                try:
                    import requests
                    r = requests.post(
                        f"{backend_url}/api/chat/", 
                        json={
                            "message": prompt, 
                            "conversation_history": conversation_history
                        }, 
                        timeout=15
                    )
                    
                    if r.status_code == 200:
                        data = r.json()
                        reply = data.get("reply", "(no reply)")
                        st.markdown(reply)
                        
                        # Show structured details if available
                        if 'itinerary' in data:
                            ChatInterface._render_quote_details(data)
                        
                        # Add assistant response to chat history
                        st.session_state.chat.append(("assistant", reply))
                        
                    else:
                        err = f"Backend error {r.status_code}: {r.text}"
                        st.error(err)
                        st.session_state.chat.append(("assistant", err))
                        
                except Exception as e:
                    msg = f"Failed to reach backend: {e}"
                    st.error(msg)
                    st.session_state.chat.append(("assistant", msg))
    
    @staticmethod
    def _render_quote_details(data: Dict[str, Any]):
        """Render quote details in an expandable section."""
        with st.expander("📋 Quote Details"):
            # Debug: Show what data we have
            st.write("**Debug Info:**")
            st.write(f"Data keys: {list(data.keys())}")
            if 'recommended_aircraft' in data:
                st.write(f"Recommended aircraft keys: {list(data['recommended_aircraft'].keys())}")
                st.write(f"Recommended aircraft type: {data['recommended_aircraft'].get('type', 'NOT FOUND')}")
            else:
                st.write("No recommended_aircraft in data")
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Origin**: {data['itinerary']['origin']}")
                st.write(f"**Destination**: {data['itinerary']['destination']}")
                st.write(f"**Date**: {data['itinerary']['departure_date']}")
            with col2:
                st.write(f"**Return**: {data['itinerary']['return_date'] or 'One-way'}")
                st.write(f"**Passengers**: {data['itinerary']['passengers']}")
                if 'recommended_aircraft' in data and 'type' in data['recommended_aircraft']:
                    st.write(f"**Aircraft**: {data['recommended_aircraft']['type']}")
                else:
                    st.write("**Aircraft**: Not specified")
            
            if 'total_price_usd' in data:
                st.success(f"**Total Price**: ${data['total_price_usd']:,.0f} USD")

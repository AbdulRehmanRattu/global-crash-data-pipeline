import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# Page configuration
st.set_page_config(
    page_title="USA Traffic Accident Analysis",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling with dark theme
st.markdown("""
<style>
    /* DARK THEME STYLES */
    .stApp {
        background-color: #121212;
        color: #f0f0f0;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #1e88e5 !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #424242;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 20px;
        height: 50px;
        color: white !important;
        font-weight: 600;
        font-size: 16px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1e88e5 !important;
        color: white !important;
    }
    
    /* Card style for metrics */
    .metric-card {
        background-color: #2c2c2c;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        margin-bottom: 16px;
    }
    
    /* Risk level colors */
    .risk-high {
        color: #f44336;
        font-weight: bold;
    }
    
    .risk-medium {
        color: #ff9800;
        font-weight: bold;
    }
    
    .risk-low {
        color: #4caf50;
        font-weight: bold;
    }
    
    /* Override Streamlit's default padding */
    .main .block-container {
        padding-top: 2rem;
        max-width: 95%;
    }
    
    /* Better markdown text */
    p, li {
        font-size: 16px;
        line-height: 1.6;
    }
    
    /* Button styles */
    .stButton button {
        background-color: #1e88e5;
        color: white;
        border: none;
        font-weight: 600;
    }
    
    /* Alert/info styles */
    .stAlert {
        background-color: #2c2c2c;
        border-left-color: #1e88e5;
    }
    
    /* Fix white boxes */
    div[data-testid="stVerticalBlock"] {
        background-color: transparent !important;
    }
    
    div.element-container {
        background-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# Function to load data with explicit type handling
def load_data():
    try:
        # Explicitly set dtypes to avoid conversion issues
        weather_dtypes = {
            'weathername': str,
            'Total_Accidents': int,
            'Total_Fatalities': int
        }
        
        lighting_dtypes = {
            'lgt_condname': str,
            'Total_Accidents': int,
            'Total_Fatalities': int
        }
        
        time_dtypes = {
            'hour': int,
            'Total_Accidents': int,
            'Total_Fatalities': int
        }
        
        day_dtypes = {
            'day_weekname': str,
            'Total_Accidents': int,
            'Total_Fatalities': int
        }
        
        # Load data with explicit dtypes
        weather_summary = pd.read_csv("weather_summary.csv", dtype=weather_dtypes)
        lighting_summary = pd.read_csv("lighting_summary.csv", dtype=lighting_dtypes)
        time_summary = pd.read_csv("time_summary.csv", dtype=time_dtypes)
        day_summary = pd.read_csv("day_summary.csv", dtype=day_dtypes)
        grid_summary = pd.read_csv("grid_summary.csv")
        
        # Ensure numeric columns in grid_summary
        for col in ['Total_Accidents', 'Total_Fatalities']:
            grid_summary[col] = pd.to_numeric(grid_summary[col], errors='coerce')
        
        # Ensure string columns in grid_summary
        for col in ['Sample_State', 'Sample_City', 'Sample_County']:
            if col in grid_summary.columns:
                grid_summary[col] = grid_summary[col].astype(str)
        
        # Format hour display safely
        time_summary['hour_display'] = time_summary['hour'].apply(
            lambda x: f"{int(x)}:00 - {int(x)+1}:00"
        )
        
        # Calculate fatality rates
        weather_summary['Fatality_Rate'] = weather_summary['Total_Fatalities'] / weather_summary['Total_Accidents']
        lighting_summary['Fatality_Rate'] = lighting_summary['Total_Fatalities'] / lighting_summary['Total_Accidents']
        time_summary['Fatality_Rate'] = time_summary['Total_Fatalities'] / time_summary['Total_Accidents']
        day_summary['Fatality_Rate'] = day_summary['Total_Fatalities'] / day_summary['Total_Accidents']
        grid_summary['Fatality_Rate'] = grid_summary['Total_Fatalities'] / grid_summary['Total_Accidents']
        
        return {
            'weather': weather_summary,
            'lighting': lighting_summary,
            'time': time_summary,
            'day': day_summary,
            'grid': grid_summary
        }
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

# Dashboard Header
st.title("🚨 USA Traffic Accident Analysis Dashboard")
st.markdown("### Interactive dashboard for accident patterns and risk assessment")

try:
    # Load data
    data = load_data()
    
    if data is None:
        st.error("Failed to load data. Please check the error message above.")
    else:
        # Create tabs with clear text
        tab1, tab2, tab3 = st.tabs([
            "📊 Overview & Patterns", 
            "🗺️ Geographic Hotspots", 
            "⚠️ Risk Factors"
        ])
        
        # ========================= TAB 1: OVERVIEW & PATTERNS =========================
        with tab1:
            # Calculate totals for metrics
            total_accidents = sum(data['weather']['Total_Accidents'])
            total_fatalities = sum(data['weather']['Total_Fatalities'])
            overall_rate = (total_fatalities / total_accidents) * 100
            
            # Key metrics in the first row
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(
                    f"""<div class="metric-card">
                    <h3>Total Accidents</h3>
                    <p style="font-size:28px; font-weight:bold; color:#1e88e5;">{total_accidents:,}</p>
                    </div>""", 
                    unsafe_allow_html=True
                )
                
            with col2:
                st.markdown(
                    f"""<div class="metric-card">
                    <h3>Total Fatalities</h3>
                    <p style="font-size:28px; font-weight:bold; color:#f44336;">{total_fatalities:,}</p>
                    </div>""", 
                    unsafe_allow_html=True
                )
                
            with col3:
                st.markdown(
                    f"""<div class="metric-card">
                    <h3>Overall Fatality Rate</h3>
                    <p style="font-size:28px; font-weight:bold; color:#ff9800;">{overall_rate:.2f}%</p>
                    </div>""", 
                    unsafe_allow_html=True
                )
                
            st.markdown("---")
            
            # Time patterns - Two column layout
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Accidents by Hour of Day")
                
                # Create a bar chart for hour of day
                fig_time = px.bar(
                    data['time'], 
                    x='hour_display', y='Total_Accidents',
                    color='Total_Fatalities',
                    color_continuous_scale='Blues',
                    labels={
                        'Total_Accidents': 'Accident Count', 
                        'hour_display': 'Hour', 
                        'Total_Fatalities': 'Fatalities'
                    }
                )
                
                # Update layout for dark theme
                fig_time.update_layout(
                    plot_bgcolor='rgba(30, 30, 30, 1)',
                    paper_bgcolor='rgba(30, 30, 30, 1)',
                    font=dict(color='white'),
                    margin=dict(l=40, r=40, t=40, b=40),
                    height=400
                )
                
                # Update axes for better readability
                fig_time.update_xaxes(
                    gridcolor='rgba(80, 80, 80, 0.3)',
                    tickfont=dict(size=12)
                )
                
                fig_time.update_yaxes(
                    gridcolor='rgba(80, 80, 80, 0.3)',
                    tickfont=dict(size=12)
                )
                
                st.plotly_chart(fig_time, use_container_width=True)
                
            with col2:
                st.subheader("Accidents by Day of Week")
                
                # Define custom order for days
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                # Create a categorical type with the custom order
                day_summary_sorted = data['day'].copy()
                day_summary_sorted['day_weekname'] = pd.Categorical(
                    day_summary_sorted['day_weekname'], 
                    categories=day_order,
                    ordered=True
                )
                day_summary_sorted = day_summary_sorted.sort_values('day_weekname')
                
                # Create bar chart for day of week
                fig_day = px.bar(
                    day_summary_sorted, 
                    x='day_weekname', y='Total_Accidents',
                    color='Total_Fatalities',
                    color_continuous_scale='Blues',
                    labels={
                        'Total_Accidents': 'Accident Count', 
                        'day_weekname': 'Day of Week', 
                        'Total_Fatalities': 'Fatalities'
                    }
                )
                
                # Update layout for dark theme
                fig_day.update_layout(
                    plot_bgcolor='rgba(30, 30, 30, 1)',
                    paper_bgcolor='rgba(30, 30, 30, 1)',
                    font=dict(color='white'),
                    margin=dict(l=40, r=40, t=40, b=40),
                    height=400
                )
                
                # Update axes for better readability
                fig_day.update_xaxes(
                    gridcolor='rgba(80, 80, 80, 0.3)',
                    tickfont=dict(size=12)
                )
                
                fig_day.update_yaxes(
                    gridcolor='rgba(80, 80, 80, 0.3)',
                    tickfont=dict(size=12)
                )
                
                st.plotly_chart(fig_day, use_container_width=True)
            
            st.markdown("---")
            
            # Environmental conditions - Two column layout
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Accidents by Weather Condition")
                
                # Sort by accident count
                weather_sorted = data['weather'].sort_values('Total_Accidents', ascending=False)
                
                # Create bar chart for weather conditions
                fig_weather = px.bar(
                    weather_sorted,
                    x='weathername', y='Total_Accidents',
                    color='Fatality_Rate',
                    color_continuous_scale='RdBu_r',  # Red for high fatality rate, blue for low
                    labels={
                        'Total_Accidents': 'Accident Count', 
                        'weathername': 'Weather Condition', 
                        'Fatality_Rate': 'Fatality Rate'
                    },
                    text=weather_sorted['Total_Accidents'].apply(lambda x: f"{x:,}")
                )
                
                # Update layout for dark theme
                fig_weather.update_layout(
                    plot_bgcolor='rgba(30, 30, 30, 1)',
                    paper_bgcolor='rgba(30, 30, 30, 1)',
                    font=dict(color='white'),
                    margin=dict(l=40, r=40, t=40, b=40),
                    height=500
                )
                
                # Update axes for better readability
                fig_weather.update_xaxes(
                    tickangle=45,
                    gridcolor='rgba(80, 80, 80, 0.3)',
                    tickfont=dict(size=12)
                )
                
                fig_weather.update_yaxes(
                    gridcolor='rgba(80, 80, 80, 0.3)',
                    tickfont=dict(size=12)
                )
                
                fig_weather.update_traces(textposition='outside')
                
                st.plotly_chart(fig_weather, use_container_width=True)
                
            with col2:
                st.subheader("Accidents by Lighting Condition")
                
                # Sort by accident count
                lighting_sorted = data['lighting'].sort_values('Total_Accidents', ascending=False)
                
                # Create bar chart for lighting conditions
                fig_lighting = px.bar(
                    lighting_sorted,
                    x='lgt_condname', y='Total_Accidents',
                    color='Fatality_Rate',
                    color_continuous_scale='RdBu_r',  # Red for high fatality rate, blue for low
                    labels={
                        'Total_Accidents': 'Accident Count', 
                        'lgt_condname': 'Lighting Condition', 
                        'Fatality_Rate': 'Fatality Rate'
                    },
                    text=lighting_sorted['Total_Accidents'].apply(lambda x: f"{x:,}")
                )
                
                # Update layout for dark theme
                fig_lighting.update_layout(
                    plot_bgcolor='rgba(30, 30, 30, 1)',
                    paper_bgcolor='rgba(30, 30, 30, 1)',
                    font=dict(color='white'),
                    margin=dict(l=40, r=40, t=40, b=40),
                    height=500
                )
                
                # Update axes for better readability
                fig_lighting.update_xaxes(
                    tickangle=45,
                    gridcolor='rgba(80, 80, 80, 0.3)',
                    tickfont=dict(size=12)
                )
                
                fig_lighting.update_yaxes(
                    gridcolor='rgba(80, 80, 80, 0.3)',
                    tickfont=dict(size=12)
                )
                
                fig_lighting.update_traces(textposition='outside')
                
                st.plotly_chart(fig_lighting, use_container_width=True)
        
        # ========================= TAB 2: GEOGRAPHIC HOTSPOTS =========================
        with tab2:
            st.header("Accident Hotspots Map")
            
            # Create two columns for map controls and info
            map_col1, map_col2 = st.columns([3, 1])
            
            with map_col2:
                st.subheader("Map Controls")
                
                # Filter by minimum accidents
                min_accidents = st.slider(
                    "Minimum Accidents",
                    min_value=10,
                    max_value=int(data['grid']['Total_Accidents'].max()),
                    value=100
                )
                
                # Option to show high fatality areas
                highlight_fatalities = st.checkbox(
                    "Highlight High Fatality Areas",
                    value=True
                )
                
                # Show top hotspots data
                st.subheader("Top 5 Hotspots")
                
                # Get top 5 accident locations
                top_locations = data['grid'].sort_values('Total_Accidents', ascending=False).head(5)
                
                # Display top locations with styling
                for i, (_, row) in enumerate(top_locations.iterrows()):
                    st.markdown(
                        f"""<div class="metric-card" style="padding: 10px; margin-bottom: 10px;">
                        <h4 style="margin: 0; color: #1e88e5;">#{i+1}: {row['Sample_City']}, {row['Sample_State']}</h4>
                        <p style="margin: 5px 0 0 0;">Accidents: <span style="color: #ff9800; font-weight: bold;">{row['Total_Accidents']:,}</span></p>
                        <p style="margin: 0;">Fatalities: <span style="color: #f44336; font-weight: bold;">{row['Total_Fatalities']:,}</span></p>
                        </div>""",
                        unsafe_allow_html=True
                    )
            
            with map_col1:
                # Prepare filtered data
                grid_filtered = data['grid'][data['grid']['Total_Accidents'] >= min_accidents].copy()
                
                # Using Plotly instead of Folium for the map to avoid the error
                # Create a scatter map of accident locations
                
                # Determine colors and sizes for points
                grid_filtered['color'] = 'blue'
                
                # Highlight high fatality areas if selected
                if highlight_fatalities:
                    high_fatality_threshold = grid_filtered['Fatality_Rate'].quantile(0.75)
                    grid_filtered.loc[grid_filtered['Fatality_Rate'] > high_fatality_threshold, 'color'] = 'red'
                
                # Create scatter mapbox
                fig = px.scatter_mapbox(
                    grid_filtered,
                    lat='lat_grid',
                    lon='lon_grid',
                    size='Total_Accidents',
                    color='color',
                    color_discrete_map={'blue': '#1e88e5', 'red': '#f44336'},
                    size_max=15,
                    opacity=0.7,
                    zoom=3,
                    center={"lat": 39.8, "lon": -98.5},
                    height=700,
                    hover_data={
                        'lat_grid': False,
                        'lon_grid': False,
                        'color': False,
                        'Sample_City': True,
                        'Sample_State': True,
                        'Sample_County': True,
                        'Total_Accidents': True,
                        'Total_Fatalities': True,
                        'Fatality_Rate': True
                    },
                    custom_data=['Sample_City', 'Sample_State', 'Sample_County', 'Total_Accidents', 'Total_Fatalities', 'Fatality_Rate']
                )
                
                # Update traces to format the hover template
                fig.update_traces(
                    hovertemplate=(
                        "<b>%{customdata[0]}, %{customdata[1]}</b><br>" +
                        "County: %{customdata[2]}<br>" +
                        "Accidents: %{customdata[3]:,}<br>" +
                        "Fatalities: %{customdata[4]:,}<br>" +
                        "Fatality Rate: %{customdata[5]:.2%}<br>" +
                        "<extra></extra>"
                    )
                )
                
                # Use a dark theme map style
                fig.update_layout(
                    mapbox_style="carto-darkmatter",
                    margin={"r": 0, "t": 0, "l": 0, "b": 0},
                    legend_title_text="Accident Locations",
                    paper_bgcolor='rgba(30, 30, 30, 1)',
                )
                
                # Add a legend title
                if highlight_fatalities:
                    fig.update_layout(
                        legend=dict(
                            title="<b>Accident Locations</b>",
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1,
                            font=dict(color="white")
                        )
                    )
                
                # Display the map
                st.plotly_chart(fig, use_container_width=True)
            
            # Add some explanatory text under the map
            st.markdown("""
            ### Geographic Insights
            
            The map above shows the distribution of traffic accidents across the United States:
            
            - **Red points** indicate locations with high fatality rates
            - **Larger circles** represent areas with more accidents
            - **Hotspots** typically correlate with population density and major highways
            
            Use this geographic data to target your alert system to high-risk areas.
            """)
        
        # ========================= TAB 3: RISK FACTORS =========================
        with tab3:
            st.header("Risk Factor Analysis")
            
            # Create a 2-column layout
            risk_col1, risk_col2 = st.columns([1, 1])
            
            with risk_col1:
                # Condition selection for analysis
                factor_type = st.selectbox(
                    "Analyze Risk By:",
                    ["Weather", "Lighting", "Time of Day", "Day of Week"]
                )
                
                # Prepare data based on selection
                if factor_type == "Weather":
                    # Sort by fatality rate
                    df = data['weather'].sort_values('Fatality_Rate', ascending=False)
                    x_col = 'weathername'
                    x_label = 'Weather Condition'
                
                elif factor_type == "Lighting":
                    # Sort by fatality rate
                    df = data['lighting'].sort_values('Fatality_Rate', ascending=False)
                    x_col = 'lgt_condname'
                    x_label = 'Lighting Condition'
                
                elif factor_type == "Time of Day":
                    df = data['time']
                    x_col = 'hour'
                    x_label = 'Hour of Day'
                
                else:  # Day of Week
                    # Define custom order for days
                    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    
                    # Create a categorical type with the custom order
                    df = data['day'].copy()
                    df['day_weekname'] = pd.Categorical(
                        df['day_weekname'], 
                        categories=day_order,
                        ordered=True
                    )
                    df = df.sort_values('day_weekname')
                    x_col = 'day_weekname'
                    x_label = 'Day of Week'
                
                # Create visualization
                fig = px.bar(
                    df,
                    x=x_col,
                    y='Fatality_Rate',
                    color='Total_Accidents',
                    color_continuous_scale='Blues',
                    labels={
                        x_col: x_label,
                        'Fatality_Rate': 'Fatality Rate',
                        'Total_Accidents': 'Accident Count'
                    },
                    text=df['Fatality_Rate'].apply(lambda x: f"{x:.2%}")
                )
                
                # Update layout for dark theme
                fig.update_layout(
                    plot_bgcolor='rgba(30, 30, 30, 1)',
                    paper_bgcolor='rgba(30, 30, 30, 1)',
                    font=dict(color='white'),
                    margin=dict(l=40, r=40, t=40, b=40),
                    height=500
                )
                
                # Update axes for better readability
                if factor_type in ["Weather", "Lighting"]:
                    fig.update_xaxes(
                        tickangle=45,
                        gridcolor='rgba(80, 80, 80, 0.3)',
                        tickfont=dict(size=12)
                    )
                else:
                    fig.update_xaxes(
                        gridcolor='rgba(80, 80, 80, 0.3)',
                        tickfont=dict(size=12)
                    )
                
                fig.update_yaxes(
                    gridcolor='rgba(80, 80, 80, 0.3)',
                    tickfont=dict(size=12)
                )
                
                fig.update_traces(textposition='outside')
                
                st.plotly_chart(fig, use_container_width=True)
            
            with risk_col2:
                st.subheader("Risk Assessment Tool")
                st.markdown("""
                Select conditions to assess accident risk based on historical data:
                """)
                
                # Create dropdowns for condition selection
                selected_weather = st.selectbox(
                    "Weather Condition",
                    options=sorted(data['weather']['weathername'].unique())
                )
                
                selected_lighting = st.selectbox(
                    "Lighting Condition",
                    options=sorted(data['lighting']['lgt_condname'].unique())
                )
                
                selected_hour = st.slider(
                    "Hour of Day",
                    min_value=0,
                    max_value=23,
                    value=12
                )
                
                selected_day = st.selectbox(
                    "Day of Week",
                    options=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                )
                
                # Create a risk calculation based on selections
                # This is simplified since we don't have the full combinations dataset
                
                # Get relevant fatality rates
                try:
                    weather_rate = float(data['weather'][data['weather']['weathername'] == selected_weather]['Fatality_Rate'].iloc[0])
                except:
                    weather_rate = 0.01
                    
                try:
                    lighting_rate = float(data['lighting'][data['lighting']['lgt_condname'] == selected_lighting]['Fatality_Rate'].iloc[0])
                except:
                    lighting_rate = 0.01
                    
                try:
                    hour_rate = float(data['time'][data['time']['hour'] == selected_hour]['Fatality_Rate'].iloc[0])
                except:
                    hour_rate = 0.01
                    
                try:
                    day_rate = float(data['day'][data['day']['day_weekname'] == selected_day]['Fatality_Rate'].iloc[0])
                except:
                    day_rate = 0.01
                
                # Calculate a weighted risk score - not perfect but gives a relative risk level
                # Normalize each factor by its maximum in the dataset
                max_weather_rate = float(data['weather']['Fatality_Rate'].max())
                max_lighting_rate = float(data['lighting']['Fatality_Rate'].max())
                max_hour_rate = float(data['time']['Fatality_Rate'].max())
                max_day_rate = float(data['day']['Fatality_Rate'].max())
                
                # Calculate normalized rates
                norm_weather = weather_rate / max_weather_rate if max_weather_rate > 0 else 0
                norm_lighting = lighting_rate / max_lighting_rate if max_lighting_rate > 0 else 0
                norm_hour = hour_rate / max_hour_rate if max_hour_rate > 0 else 0
                norm_day = day_rate / max_day_rate if max_day_rate > 0 else 0
                
                # Calculate final risk score (0-100)
                risk_score = (norm_weather * 0.3 + norm_lighting * 0.3 + norm_hour * 0.2 + norm_day * 0.2) * 100
                
                # Determine risk level
                if risk_score >= 70:
                    risk_level = "High"
                    risk_class = "risk-high"
                    risk_color = "#f44336"  # Red
                elif risk_score >= 40:
                    risk_level = "Medium"
                    risk_class = "risk-medium"
                    risk_color = "#ff9800"  # Orange
                else:
                    risk_level = "Low"
                    risk_class = "risk-low"
                    risk_color = "#4caf50"  # Green
                
                # Display risk assessment result
                st.markdown(f"""
                <div class="metric-card" style="margin-top: 20px;">
                <h3>Accident Risk Assessment</h3>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                <p style="font-size: 16px; margin-bottom: 5px;">Based on your selected conditions:</p>
                <p class="{risk_class}" style="font-size: 32px; margin: 0;">{risk_level} Risk</p>
                <p style="margin-top: 5px;">Risk Score: {risk_score:.1f}/100</p>
                </div>
                <div style="width: 120px; height: 120px; border-radius: 50%; background: conic-gradient({risk_color} {risk_score}%, #333 0); display: flex; align-items: center; justify-content: center;">
                <div style="width: 100px; height: 100px; background: #2c2c2c; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                <span style="font-size: 24px; font-weight: bold; color: {risk_color};">{risk_score:.0f}%</span>
                </div>
                </div>
                </div>
                </div>""", 
                unsafe_allow_html=True
                )
                
                # Add recommendations based on risk level
                st.markdown(f"""
                <div class="metric-card" style="margin-top: 20px;">
                <h3>Alert System Recommendations</h3>
                """, unsafe_allow_html=True)
                
                if risk_level == "High":
                    st.markdown("""
                    - ⚠️ **Implement active alert system** for these specific conditions
                    - 🚨 Broadcast warnings when these conditions are present
                    - 🚦 Suggest alternative routes or delayed travel
                    - 👁️ Increase visibility measures (additional lighting, signage)
                    - 🚔 Consider requesting increased enforcement presence
                    """)
                elif risk_level == "Medium":
                    st.markdown("""
                    - 📱 Issue cautionary notifications to drivers
                    - 🚧 Prioritize road maintenance during these conditions
                    - 🔔 Implement passive alert systems
                    - 📊 Monitor these conditions for changes in risk patterns
                    """)
                else:
                    st.markdown("""
                    - ✅ Standard safety measures are sufficient
                    - 📝 Include in general safety education
                    - 📈 Continue monitoring accident patterns
                    """)
                
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Add overall risk insights section
            st.markdown("---")
            st.subheader("Key Insights for Alert System Development")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                #### Highest Risk Factors
                
                1. **Time Factors:**
                   - Late night/early morning hours (1AM-4AM)
                   - Weekend nights (Friday/Saturday)
                
                2. **Environmental Factors:**
                   - Dark conditions with no lighting
                   - Adverse weather (snow, fog, rain)
                """)
            
            with col2:
                st.markdown("""
                #### Alert System Design Recommendations
                
                1. **Multiple Factor Analysis:**
                   - Combine weather, lighting, time, and location data
                   - Weight risk factors based on fatality rates
                
                2. **Targeting Strategy:**
                   - Geographic targeting based on hotspot map
                   - Temporal targeting during high-risk hours
                   - Condition-based alerts for weather and lighting
                """)
    
    # Add footer with credits
    st.markdown("---")
    st.markdown(
        """<div style="text-align: center; color: #aaaaaa; font-size: 12px;">
        USA Traffic Accident Analysis Dashboard | Data from 2015-2023
        </div>""",
        unsafe_allow_html=True
    )

except Exception as e:
    st.error(f"Error loading dashboard: {str(e)}")
    
    # Add debug information in case of errors
    with st.expander("Debug Information"):
        st.write("### Error Details:")
        st.code(str(e))
        
        import os
        st.write("### Files in current directory:")
        files = os.listdir()
        st.write(files)
        
        st.write("### Troubleshooting:")
        st.markdown("""
        1. CSV files needed:
           - weather_summary.csv
           - lighting_summary.csv
           - time_summary.csv
           - day_summary.csv
           - grid_summary.csv
        
        2. Make sure you have installed all required packages:
           ```
           pip install streamlit pandas plotly numpy
           ```
        
        3. Make sure Python version is 3.7+
        """)
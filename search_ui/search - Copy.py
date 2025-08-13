# Enhanced Streamlit UI for Field-Specific Multi-Method Search
import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import os
import json
from dotenv import load_dotenv
from typing import Dict, Any, List

# Load environment variables
load_dotenv()

# Configuration
SEARCH_API_HOST = os.getenv("SEARCH_API_HOST", "localhost")
SEARCH_API_PORT = os.getenv("SEARCH_API_PORT", "8000")
DEBUG_UI = os.getenv("DEBUG_UI", "false").lower() in ("true", "1", "t", "yes")

# Set page config
st.set_page_config(
    page_title="Multi-Method Vector Search - Enhanced",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS - simplified for better Streamlit compatibility
st.markdown("""
<style>
    .main { padding-top: 1rem; }
    
    /* Score badges */
    .score-excellent { background-color: #22c55e; }
    .score-very-good { background-color: #10b981; }
    .score-good { background-color: #3b82f6; }
    .score-fair { background-color: #8b5cf6; }
    .score-poor { background-color: #f59e0b; }
    .score-very-poor { background-color: #f97316; }
    .score-no-match { background-color: #ef4444; }
    
    /* Method colors */
    .method-dense { color: #3b82f6; }
    .method-bm25 { color: #10b981; }
    .method-minicoil { color: #8b5cf6; }
    .method-hybrid-bm25 { color: #f59e0b; }
    .method-hybrid-minicoil { color: #ef4444; }
    
    /* Streamlit-specific adjustments */
    .stImage { margin: 0 auto; }
    div[data-testid="column"] { 
        padding: 0.5rem; 
    }
    
    /* Ensure consistent column spacing for cards */
    .element-container {
        height: 100%;
    }
    
    /* Card container adjustments */
    div[data-testid="stHorizontalBlock"] > div {
        height: 100%;
    }
</style>
""", unsafe_allow_html=True)

# API configuration
API_BASE_URL = f"http://{SEARCH_API_HOST}:{SEARCH_API_PORT}"

# Configure retry strategy
retry_strategy = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
session = requests.Session()
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Search method configurations (Dense + BM25 only)
SEARCH_METHODS = {
    "dense": {
        "name": "🎯 Dense Search",
        "description": "Semantic vector search on product descriptions only",
        "fields": "shortDescription_airgas_text",
        "color": "#3b82f6",
        "endpoint": "/api/dense"
    },
    "sparse": {
        "name": "🔍 BM25 Sparse Search", 
        "description": "Traditional BM25 keyword search (Qdrant native)",
        "fields": "shortDescription + partNumber + manufacturerPartNumber",
        "color": "#10b981",
        "endpoint": "/api/sparse"
    },
    "hybrid": {
        "name": "⚡ Hybrid Search",
        "description": "Dense + BM25 fusion using Qdrant native RRF", 
        "fields": "Dense (shortDescription) + BM25 (shortDescription + part numbers)",
        "color": "#f59e0b",
        "endpoint": "/api/hybrid"
    },
    "query": {
        "name": "🔄 Flexible Query",
        "description": "Flexible search with mode selection (dense, sparse, hybrid)",
        "fields": "Configurable by mode parameter", 
        "color": "#6366f1",
        "endpoint": "/api/query"
    }
}

def get_score_color(score):
    """Get color based on score"""
    if score >= 0.8: return "#22c55e"
    if score >= 0.7: return "#10b981" 
    if score >= 0.6: return "#3b82f6"
    if score >= 0.5: return "#8b5cf6"
    if score >= 0.4: return "#f59e0b"
    if score >= 0.3: return "#f97316"
    return "#ef4444"

def get_score_label(score):
    """Get descriptive label for score"""
    if score >= 0.8: return "Excellent"
    if score >= 0.7: return "Very Good"
    if score >= 0.6: return "Good" 
    if score >= 0.5: return "Fair"
    if score >= 0.4: return "Poor"
    if score >= 0.3: return "Very Poor"
    return "No Match"

def make_search_request(method_key: str, query: str, limit: int = 10, mode: str = "hybrid"):
    """Make search request using enhanced search methods"""
    try:
        method_config = SEARCH_METHODS[method_key]
        endpoint_url = f"{API_BASE_URL}{method_config['endpoint']}"
        
        # Handle different parameter names for different endpoints
        if method_key == "query":
            params = {"q": query, "count": limit, "mode": mode}
        elif method_key in ["dense", "sparse", "hybrid"]:
            params = {"query": query, "limit": limit}
        else:
            # Legacy endpoints if any exist
            params = {"query": query, "limit": limit}
        
        response = session.get(endpoint_url, params=params, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API returned status {response.status_code}"}
            
    except requests.exceptions.ConnectionError:
        return {"error": "Connection failed - ensure the search service is running"}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

def render_product_card_native(result: Dict[str, Any], method_key: str):
    """Render product card using native Streamlit components with consistent height"""
    # Extract data from result
    if 'payload' in result:
        data = result['payload']
    else:
        data = result
    
    score = result.get('score', 0)
    part_num = data.get('partNumber_airgas_text', 'N/A')
    description = data.get('shortDescription_airgas_text', 'N/A') 
    mfg_part = data.get('manufacturerPartNumber_text', 'N/A')
    price = data.get('onlinePrice_string', 'N/A')
    image_url = data.get('img_270Wx270H_string', '')
    
    # Build image URL
    if image_url and not image_url.startswith('http'):
        if image_url.startswith('/'):
            image_url = f"http://www.airgas.com{image_url}"
        else:
            image_url = f"http://www.airgas.com/{image_url}"
    
    # Get labels
    score_label = get_score_label(score)
    method_name = SEARCH_METHODS[method_key]['name']
    method_color = SEARCH_METHODS[method_key]['color']
    score_color = get_score_color(score)
    
    # Truncate text to ensure consistent height
    # Part number - max 20 chars
    if len(part_num) > 20:
        part_num_display = part_num[:17] + "..."
    else:
        part_num_display = part_num
    
    # Description - exactly 3 lines worth (~120 chars)
    if len(description) > 120:
        desc_display = description[:117] + "..."
    else:
        desc_display = description
    
    # MFG part - max 15 chars
    if len(mfg_part) > 15:
        mfg_display = mfg_part[:12] + "..."
    else:
        mfg_display = mfg_part
    
    # No image placeholder SVG
    no_image_svg = """
    <svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <rect width="100" height="100" fill="#f3f4f6"/>
        <path d="M37 30 L63 30 L63 55 L37 55 Z" fill="none" stroke="#9ca3af" stroke-width="2"/>
        <circle cx="45" cy="40" r="3" fill="#9ca3af"/>
        <path d="M37 55 L47 45 L53 51 L63 41" fill="none" stroke="#9ca3af" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <text x="50" y="70" font-family="Arial, sans-serif" font-size="10" fill="#6b7280" text-anchor="middle">No Image</text>
    </svg>
    """
    
    # Create a container with CSS border (compatible with older Streamlit versions)
    with st.container():
        # Add CSS border styling
        st.markdown("""
        <style>
        .product-card {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
            background-color: #ffffff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Start product card container
        st.markdown('<div class="product-card">', unsafe_allow_html=True)
        # Row 1: Method badge
        st.markdown(
            f"<div style='text-align: center; background-color: {method_color}; color: white; "
            f"padding: 6px; border-radius: 8px; margin-bottom: 8px; font-weight: bold; font-size: 0.9em;'>"
            f"{method_name}</div>", 
            unsafe_allow_html=True
        )
        
        # Row 2: Score badge
        st.markdown(
            f"<div style='text-align: center; background-color: {score_color}; color: white; "
            f"padding: 6px; border-radius: 8px; margin-bottom: 10px; font-weight: bold; font-size: 0.9em;'>"
            f"{score_label}: {score:.3f}</div>", 
            unsafe_allow_html=True
        )
        
        # Row 3: Image with fixed height container
        if image_url:
            # Try to load the actual image
            image_html = f"""
            <img src='{image_url}' 
                 style='max-height: 110px; max-width: 100%; object-fit: contain;' 
                 onerror="this.onerror=null; this.style.display='none'; this.nextElementSibling.style.display='block';"
                 alt='Product' />
            <div style='display:none;'>{no_image_svg}</div>
            """
        else:
            # Use the no image placeholder
            image_html = no_image_svg
        
        st.markdown(
            f"<div style='height: 120px; display: flex; align-items: center; justify-content: center; "
            f"background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; margin-bottom: 10px;'>"
            f"{image_html}</div>",
            unsafe_allow_html=True
        )
        
        # Row 4: Part number (fixed height)
        st.markdown(
            f"<div style='height: 25px; margin-bottom: 8px;'>"
            f"<strong>Part:</strong> <code style='background: #f3f4f6; padding: 2px 4px; border-radius: 3px;'>"
            f"{part_num_display}</code></div>",
            unsafe_allow_html=True
        )
        
        # Row 5: Description (fixed 3 lines = ~60px)
        st.markdown(
            f"<div style='height: 80px; overflow: hidden; margin-bottom: 8px;'>"
            f"<strong>Description:</strong><br>"
            f"<span style='font-size: 0.9em; color: #4b5563; line-height: 1.4;'>{desc_display}</span></div>",
            unsafe_allow_html=True
        )
        
        # Row 6: Divider
        st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #e5e7eb;'>", unsafe_allow_html=True)
        
        # Row 7: MFG and Price (fixed height)
        st.markdown(
            f"<div style='height: 25px; display: flex; justify-content: space-between; align-items: center;'>"
            f"<span><strong>MFG:</strong> <code style='background: #f3f4f6; padding: 1px 3px; border-radius: 2px; font-size: 0.85em;'>"
            f"{mfg_display}</code></span>"
            f"<span style='color: #10b981; font-weight: bold;'>${price}</span></div>",
            unsafe_allow_html=True
        )
        
        # Close product card container
        st.markdown('</div>', unsafe_allow_html=True)

def render_simple_product_info(result: Dict[str, Any], method_key: str):
    """Render simple product info using native Streamlit components"""
    # Extract data
    if 'payload' in result:
        data = result['payload']
    else:
        data = result
    
    score = result.get('score', 0)
    part_num = data.get('partNumber_airgas_text', 'N/A')
    description = data.get('shortDescription_airgas_text', 'N/A')
    mfg_part = data.get('manufacturerPartNumber_text', 'N/A')
    price = data.get('onlinePrice_string', 'N/A')
    
    score_label = get_score_label(score)
    method_name = SEARCH_METHODS[method_key]['name']
    
    # Create metrics row
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.metric(label=method_name, value=f"{score_label}", delta=f"Score: {score:.3f}")
    with col2:
        st.metric(label="Part", value=part_num)
    with col3:
        st.metric(label="Price", value=f"${price}")
    
    # Description
    st.write(f"**Description:** {description[:150]}{'...' if len(description) > 150 else ''}")
    st.write(f"**MFG Part:** {mfg_part}")
    st.divider()

def render_comparison_view(all_results: Dict[str, Any], query: str):
    """Render comparison view using native Streamlit components"""
    st.subheader(f"🔬 Method Comparison for: *{query}*")
    
    # Performance metrics
    st.markdown("#### ⚡ Performance Metrics")
    
    perf_cols = st.columns(len(SEARCH_METHODS))
    for i, (method_key, result) in enumerate(all_results.items()):
        with perf_cols[i]:
            if result.get('error'):
                st.error(f"{SEARCH_METHODS[method_key]['name']}\n{result['error']}")
            else:
                search_time = result.get('search_time_ms', 0)
                result_count = len(result.get('results', []))
                
                st.metric(
                    label=SEARCH_METHODS[method_key]['name'],
                    value=f"{result_count} results",
                    delta=f"{search_time:.1f}ms"
                )
    
    # Field mapping info
    with st.expander("🔍 Search Field Mapping", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Dense Search:**")
            st.write("• shortDescription_airgas_text only")
            st.write("• Semantic understanding")
        
        with col2:
            st.markdown("**Sparse Search (BM25/MiniCOIL):**")
            st.write("• shortDescription_airgas_text")
            st.write("• partNumber_airgas_text")
            st.write("• manufacturerPartNumber_text")
        
        with col3:
            st.markdown("**Hybrid Search:**")
            st.write("• Combines dense + sparse")
            st.write("• Weighted fusion scoring")
    
    # Top results comparison
    st.markdown("#### 📋 Top 3 Results per Method")
    
    for method_key, result in all_results.items():
        if not result.get('error'):
            with st.expander(f"{SEARCH_METHODS[method_key]['name']} - Top Results", expanded=True):
                results = result.get('results', [])[:3]
                
                if results:
                    for i, res in enumerate(results, 1):
                        score = res.get('score', 0)
                        data = res.get('payload', res)
                        part_num = data.get('partNumber_airgas_text', 'N/A')
                        description = data.get('shortDescription_airgas_text', 'N/A')
                        price = data.get('onlinePrice_string', 'N/A')
                        
                        col1, col2, col3, col4 = st.columns([1, 2, 3, 1])
                        with col1:
                            st.write(f"**#{i}**")
                        with col2:
                            st.write(f"Score: **{score:.3f}**")
                        with col3:
                            st.write(f"Part: `{part_num}`")
                        with col4:
                            st.write(f"${price}")
                        
                        st.write(f"{description[:100]}...")
                        if i < len(results):
                            st.divider()
                else:
                    st.info("No results found")

# App Header
st.title("🚀 Airgas - Vector Search Application")
st.markdown("Dense + BM25 Sparse + Hybrid (Qdrant Native RRF)")

# Sidebar configuration
with st.sidebar:
    st.header("🔧 Search Configuration")
    
    # Search method selection
    selected_method = st.selectbox(
        "Select Search Method:",
        options=list(SEARCH_METHODS.keys()),
        format_func=lambda x: SEARCH_METHODS[x]["name"],
        index=0
    )
    
    # Show method details
    method_config = SEARCH_METHODS[selected_method]
    st.info(f"**Description:** {method_config['description']}\n\n"
            f"**Search Fields:** {method_config['fields']}")
    
    # Mode selector for query endpoint
    query_mode = "hybrid"  # default
    if selected_method == "query":
        query_mode = st.selectbox(
            "Query Mode:",
            options=["dense", "sparse", "hybrid"],
            index=2,  # hybrid as default
            help="Select the search mode for the flexible query endpoint"
        )
    
    st.divider()
    
    # Options
    result_limit = st.slider("Results per method", 1, 60, 20)
    display_mode = st.radio("Display Mode", ["Cards", "Simple List"], index=0)
    show_debug = st.checkbox("Show debug info", value=DEBUG_UI)
    
    st.divider()
    st.markdown("### Available Methods")
    for key, config in SEARCH_METHODS.items():
        st.write(f"• {config['name']}")

# Main search interface
st.markdown("### 🔍 Search Interface")

# Search input with form for Enter key support
with st.form(key="search_form", clear_on_submit=False):
    query = st.text_input(
        "Enter your search query:",
        placeholder="e.g., 'gas torch', 'HYP220479', 'welding equipment'",
        help="Try product descriptions, part numbers, or manufacturer codes (Press Enter to search)"
    )
    
    # Search buttons inside form
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        individual_search = st.form_submit_button(
            f"Search with {SEARCH_METHODS[selected_method]['name']}", 
            type="primary",
            use_container_width=True
        )
    
    with col2:
        compare_all = st.form_submit_button(
            "🔬 Compare All Methods", 
            type="secondary",
            use_container_width=True
        )

# Auto-trigger individual search on Enter (when no specific button is clicked)
if query and not individual_search and not compare_all:
    # Check if this is a new search by comparing with session state
    if 'last_query' not in st.session_state or st.session_state.last_query != query:
        individual_search = True  # Auto-trigger individual search
        st.session_state.last_query = query

# Process searches
if query and (individual_search or compare_all):
    
    if individual_search:
        # Single method search
        st.subheader(f"Results from {SEARCH_METHODS[selected_method]['name']}")
        
        with st.spinner(f"Searching with {SEARCH_METHODS[selected_method]['name']}..."):
            result = make_search_request(selected_method, query, result_limit, query_mode)
            
            if result.get('error'):
                st.error(f"❌ {result['error']}")
            else:
                results = result.get('results', [])
                search_time = result.get('search_time_ms', 0)
                
                # Performance metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Search Time", f"{search_time:.1f}ms")
                with col2:
                    st.metric("Results Found", len(results))
                with col3:
                    st.metric("Fields Searched", len(SEARCH_METHODS[selected_method]['fields'].split('+')))
                
                st.info(f"**Fields searched:** {SEARCH_METHODS[selected_method]['fields']}")
                
                if results:
                    st.divider()
                    
                    if display_mode == "Cards":
                        # Display as cards in columns
                        num_cols = min(4, len(results))
                        cols = st.columns(num_cols)
                        
                        for i, res in enumerate(results):
                            with cols[i % num_cols]:
                                render_product_card_native(res, selected_method)
                    else:
                        # Simple list display
                        for res in results:
                            render_simple_product_info(res, selected_method)
                else:
                    st.warning("No results found. Try a different query.")
    
    elif compare_all:
        # Multi-method comparison
        st.subheader("🔬 Running All Search Methods...")
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_results = {}
        
        # Run all search methods
        for i, method_key in enumerate(SEARCH_METHODS.keys()):
            status_text.text(f"Running {SEARCH_METHODS[method_key]['name']}...")
            progress_bar.progress((i + 1) / len(SEARCH_METHODS))
            
            result = make_search_request(method_key, query, result_limit, query_mode)
            all_results[method_key] = result
            
            time.sleep(0.1)  # Small delay for visual effect
        
        progress_bar.empty()
        status_text.empty()
        
        # Create tabs for results
        tab_names = ["🔬 Comparison"] + [config['name'] for config in SEARCH_METHODS.values()]
        tabs = st.tabs(tab_names)
        
        # Comparison tab
        with tabs[0]:
            render_comparison_view(all_results, query)
        
        # Individual method tabs
        for i, method_key in enumerate(SEARCH_METHODS.keys()):
            with tabs[i + 1]:
                result = all_results[method_key]
                method_config = SEARCH_METHODS[method_key]
                
                if result.get('error'):
                    st.error(f"❌ {result['error']}")
                else:
                    results = result.get('results', [])
                    search_time = result.get('search_time_ms', 0)
                    
                    # Method info box
                    with st.container():
                        st.info(f"**Method:** {method_config['name']}\n\n"
                               f"**Description:** {method_config['description']}\n\n"
                               f"**Fields Searched:** {method_config['fields']}")
                    
                    # Performance metrics
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Search Time", f"{search_time:.1f}ms")
                    with col2:
                        st.metric("Results Found", len(results))
                    
                    if results:
                        st.divider()
                        
                        if display_mode == "Cards":
                            # Display as cards
                            num_cols = min(4, len(results))
                            cols = st.columns(num_cols)
                            
                            for idx, res in enumerate(results):
                                with cols[idx % num_cols]:
                                    render_product_card_native(res, method_key)
                        else:
                            # Simple list
                            for res in results:
                                render_simple_product_info(res, method_key)
                    else:
                        st.warning("No results found with this method.")

# Debug information
if show_debug and query:
    with st.expander("🐛 Debug Information", expanded=False):
        debug_info = {
            "query": query,
            "api_base_url": API_BASE_URL,
            "selected_method": selected_method,
            "result_limit": result_limit,
            "display_mode": display_mode,
            "available_methods": list(SEARCH_METHODS.keys())
        }
        st.json(debug_info)

# Footer
st.divider()
st.caption(f"🔧 **Configuration:** API: `{API_BASE_URL}` | Debug: `{'ON' if show_debug else 'OFF'}`")
st.caption("🎯 **Field-Specific Search:** Dense (descriptions) vs Sparse (descriptions + part numbers) vs Hybrid (fusion)")
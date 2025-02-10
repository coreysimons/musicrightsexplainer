#!/usr/bin/env python3
import streamlit as st
import json
import networkx as nx
import matplotlib.pyplot as plt
import textwrap  # For wrapping long labels
import pandas as pd  # For creating tables in the text section

# -----------------------------------
# 1) Load JSON Data from File
# -----------------------------------
@st.cache_data
def load_json():
    try:
        with open("royalties.json", "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                st.error("Invalid JSON structure: Expected a dictionary at the root.")
                return {}
            return data
    except FileNotFoundError:
        st.error("Error: royalties.json file not found. Ensure it's in the correct directory.")
        return {}
    except json.JSONDecodeError:
        st.error("Error: royalties.json contains invalid JSON formatting.")
        return {}

ROYALTY_DATA = load_json()

# -----------------------------------
# 2) Utility function to wrap labels
# -----------------------------------
def wrap_label(label, width=15):
    """Wraps text into multiple lines for better readability."""
    return "\n".join(textwrap.wrap(label, width))

# -----------------------------------
# 2.1) Helper to convert keys to friendly text.
# -----------------------------------
def friendly_text(key):
    mapping = {
        "interactive_dsp": "Interactive DSP",
        "traditional_digital": "Traditional Digital",
        "non_interactive_services": "Non-Interactive Services",
        "digital_downloads": "Digital Downloads",
        "ugc": "User-Generated Content",
        "non_digital": "Non-Digital",
        "artist_label": "Artist/Label",
        "writer_publisher": "Writer/Publisher",
        "us": "US",
        "international": "International",
        "recording_revenues": "Recording Revenues",
        "neighboring_rights": "Neighboring Rights",
        "performance": "Performance Rights",
        "mechanical": "Mechanical Rights",
        "sync_fees": "Sync Fees",
        "broadcast_radio_tv": "Broadcast Radio & TV",
        "restaurants_bars_venues": "Restaurants, Bars & Venues",
        "live_performances": "Live Performances",
        "physical_sales": "Physical Sales",
        "organic": "Organic",
        "official_library": "Official Library",
        "youtube": "YouTube",
        "meta": "Meta",
        "tiktok": "TikTok",
        "snapchat": "Snapchat",
        "twitch": "Twitch"
    }
    return mapping.get(key.lower(), key)

# -----------------------------------
# 3) Function to Generate and Display Flowcharts
# -----------------------------------
def generate_flowchart(source, region, role, rights):
    if not isinstance(rights, dict) or not rights:
        st.error(f"Unexpected or missing rights data for {friendly_text(role)} in {friendly_text(region)} for {friendly_text(source)}. Skipping flowchart.")
        return

    G = nx.DiGraph()
    node_positions = {}
    node_colors = {}

    # Layout parameters
    x_offset = 2  # Horizontal spacing
    y_offset = 2  # Vertical spacing
    num_rights = len(rights)
    mid_y = -((num_rights - 1) * y_offset) / 2  # center vertically

    # Add the source node (using the subcategory name)
    G.add_node(source)
    source_color = "lightblue"
    node_colors[source] = source_color
    node_positions[source] = (0, mid_y)

    # Loop over each right (e.g., "recording_revenues", "neighboring_rights")
    for i, (right, details) in enumerate(rights.items()):
        if not isinstance(details, dict):
            continue

        collected_by = details.get("collected_by", "").strip()
        payee = details.get("payee", "").strip()
        is_not_applicable = "fully_not_applicable" in details

        if not payee:
            payee = role

        right_x = x_offset
        right_y = -i * y_offset
        G.add_node(right)
        G.add_edge(source, right)
        node_colors[right] = "red" if is_not_applicable else source_color
        node_positions[right] = (right_x, right_y)

        if is_not_applicable:
            continue

        collected_by_x = right_x + x_offset
        payee_x = collected_by_x + x_offset

        if collected_by:
            G.add_node(collected_by)
            G.add_edge(right, collected_by)
            node_colors[collected_by] = source_color
            node_positions[collected_by] = (collected_by_x, right_y)

        if payee:
            G.add_node(payee)
            if collected_by:
                G.add_edge(collected_by, payee)
            else:
                G.add_edge(right, payee)
            node_colors[payee] = source_color
            node_positions[payee] = (payee_x, mid_y)

    wrapped_labels = {node: wrap_label(friendly_text(node), width=20) for node in G.nodes()}
    fig, ax = plt.subplots(figsize=(12, 6))
    nx.draw(
        G,
        pos=node_positions,
        labels=wrapped_labels,
        with_labels=True,
        node_color=[node_colors[n] for n in G.nodes()],
        edge_color="gray",
        node_size=2500,
        font_size=11,
        font_color="black",
        verticalalignment="center",
        arrowsize=20
    )
    plt.title(f"{friendly_text(source)} ({friendly_text(region)} - {friendly_text(role)})", fontsize=14)
    st.pyplot(fig)

# -----------------------------------
# 4) Helpers for Rights Details in Text
# -----------------------------------
def get_rights_data(area: str, usage_type: str, location: str, platform: str = None):
    # For UGC, our JSON structure now is at:
    # ROYALTY_DATA["ugc"][usage_type][platform][location]
    if area.lower() == "ugc":
        if not platform:
            return [], []
        data_node = ROYALTY_DATA[area][usage_type].get(platform, {}).get(location, {})
    else:
        data_node = ROYALTY_DATA.get(area, {}).get(usage_type, {}).get(location, {})

    master_list = []
    publishing_list = []
    if not isinstance(data_node, dict):
        return master_list, publishing_list

    for role_key, role_data in data_node.items():
        if not isinstance(role_data, dict):
            continue
        for right_key, right_info in role_data.items():
            if not isinstance(right_info, dict):
                continue
            entry = {
                "Right": right_key,
                "fully_not_applicable": right_info.get("fully_not_applicable", None),
                "Collected By": right_info.get("collected_by", ""),
                "How Received": right_info.get("how_it_is_received", ""),
                "Est. Rate": right_info.get("estimated_rate", 0.0),
                "How it's Calculated": right_info.get("how_it_is_calculated", "")
            }
            if role_key == "artist_label":
                master_list.append(entry)
            elif role_key == "writer_publisher":
                publishing_list.append(entry)
    return master_list, publishing_list

def create_rights_table(data_list, rights_of_interest):
    rights_status = {r: "❌" for r in rights_of_interest}
    right_mapping = {
        "recording_revenues": friendly_text("recording_revenues"),
        "neighboring_rights": friendly_text("neighboring_rights"),
        "performance": friendly_text("performance"),
        "mechanical": friendly_text("mechanical"),
        "sync_fees": friendly_text("sync_fees")
    }
    for entry in data_list:
        raw_key = entry["Right"].lower().replace(" ", "_")
        display_key = right_mapping.get(raw_key, friendly_text(raw_key))
        if entry["fully_not_applicable"]:
            continue
        if entry["Collected By"] and not entry["Collected By"].startswith("❌"):
            rights_status[display_key] = "✅"
    df = pd.DataFrame({
        "Rights": rights_of_interest,
        "Applicable": [rights_status[r] for r in rights_of_interest]
    })
    return df

def display_rights_details(data_list):
    if not data_list:
        st.write("No rights data available for this section.")
        return

    for entry in data_list:
        display_right = friendly_text(entry["Right"])
        if entry["fully_not_applicable"]:
            st.markdown(
                f"<strong><p style='margin:0;'>{display_right}</p></strong>"
                f"<ul style='margin:0; padding-left:20px; list-style-type: disc;'>"
                f"<p><li>{entry['fully_not_applicable']}</li></p>"
                f"</ul>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"<strong><p style='margin:0;'>{display_right}</p></strong>", unsafe_allow_html=True)
            st.markdown(f"""
<ul style="margin:0; padding-left:20px; list-style-type: disc;">
  <li><strong>How it's collected:</strong> {entry['Collected By']}</li>
  <li><strong>How it's paid:</strong> {entry['How Received']}</li>
  <li><strong>Estimated rate:</strong> {entry['Est. Rate']}</li>
  <li><strong>How it's calculated:</strong> {entry["How it's Calculated"]}</li>
</ul>
""", unsafe_allow_html=True)

# -----------------------------------
# 5) Streamlit UI with Dropdowns, Flowchart, and Rights Details
# -----------------------------------

st.sidebar.header("Select usage type")
category = st.sidebar.selectbox("Category", list(ROYALTY_DATA.keys()), format_func=friendly_text)
subcategory = st.sidebar.selectbox("Source", list(ROYALTY_DATA[category].keys()), format_func=friendly_text)

if category.lower() == "ugc":
    # For UGC, the structure is:
    # ROYALTY_DATA["ugc"][subcategory][platform][region][role]
    platform_options = [key for key, value in ROYALTY_DATA[category][subcategory].items() if isinstance(value, dict)]
    platform = st.sidebar.selectbox("Platform", platform_options, format_func=friendly_text)
    region_options = [key for key, value in ROYALTY_DATA[category][subcategory][platform].items() if isinstance(value, dict)]
    region = st.sidebar.selectbox("Region", region_options, format_func=friendly_text)
    # Use radio buttons here (instead of selectbox) to match the other options.
    role = st.sidebar.radio("Role", options=list(ROYALTY_DATA[category][subcategory][platform][region].keys()), format_func=friendly_text)
else:
    region_options = [key for key, value in ROYALTY_DATA[category][subcategory].items() if isinstance(value, dict)]
    region = st.sidebar.selectbox("Region", region_options, format_func=friendly_text)
    role = st.sidebar.radio(
        "Role",
        options=["artist_label", "writer_publisher"],
        format_func=friendly_text,
        index=0  # Default to "Artist/Label"
    )

# Display the current selection chain.
if category.lower() == "ugc":
    st.markdown(f"### {friendly_text(subcategory)} → {friendly_text(platform)} → {friendly_text(region)} → {friendly_text(role)}")
else:
    st.markdown(f"### {friendly_text(subcategory)} → {friendly_text(region)} → {friendly_text(role)}")

# Retrieve the rights dictionary and generate the flowchart.
if category.lower() == "ugc":
    rights = ROYALTY_DATA[category][subcategory][platform][region].get(role, {})
    generate_flowchart(subcategory, region, role, rights)
else:
    rights = ROYALTY_DATA[category][subcategory][region][role]
    generate_flowchart(subcategory, region, role, rights)

# -----------------------------------
# Updated Usage Explainer Section
# -----------------------------------
# Always build a region-specific key – no fallback to generic keys.
if region.lower() == "us":
    usage_key = f"us_usage_explainer_{role}"
elif region.lower() == "international":
    usage_key = f"int_usage_explainer_{role}"
else:
    usage_key = f"{region.lower()}_usage_explainer_{role}"

if category.lower() == "ugc":
    # For UGC, the usage explainer is now at the platform level (inside ROYALTY_DATA[ugc][subcategory][platform])
    usage_text = ROYALTY_DATA[category][subcategory][platform].get(usage_key, "No usage explainer available.")
else:
    usage_text = ROYALTY_DATA[category][subcategory].get(usage_key, "No usage explainer available.")

st.markdown(usage_text)

# Retrieve rights details for display.
if category.lower() == "ugc":
    master_list, publishing_list = get_rights_data(category, subcategory, region, platform=platform)
else:
    master_list, publishing_list = get_rights_data(category, subcategory, region)

if role == "artist_label":
    display_rights_details(master_list)
elif role == "writer_publisher":
    display_rights_details(publishing_list)

import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time

# Page config
st.set_page_config(
    page_title="Vietnam Airlines Image Database Editor",
    page_icon="",
    layout='wide'
)

# Supabase configuration
SUPABASE_URL = "https://iyxcvqvhmqhjjfieszga.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5eGN2cXZobXFoampmaWVzemdhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTg2ODkyMTYsImV4cCI6MjA3NDI2NTIxNn0.DQ3o-ug6XbhU3hGgzazJzPksbgL7InM1RvVDF175tkk"

@st.cache_resource
def get_supabase_client():
    """Create and cache Supabase client"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_total_count():
    """Get total number of records"""
    try:
        supabase = get_supabase_client()
        response = supabase.table("images").select("id", count="exact").execute()
        return response.count, None
    except Exception as e:
        return 0, str(e)

@st.cache_data(ttl=60)  # Cache for 1 minute
def load_data_paginated(page=0, page_size=100, status_filter=None, search_term=None):
    """Load paginated data from Supabase with filtering"""
    try:
        supabase = get_supabase_client()

        # Start building query
        query = supabase.table("images").select("*")

        # Apply filters
        if status_filter == "Valid Images":
            query = query.eq("image_status", True)
        elif status_filter == "Invalid Images":
            query = query.eq("image_status", False)

        if search_term:
            query = query.or_(f"image_title.ilike.%{search_term}%,image_alt.ilike.%{search_term}%")

        # Apply pagination
        start_idx = page * page_size
        end_idx = start_idx + page_size - 1

        response = query.range(start_idx, end_idx).execute()

        if response.data:
            df = pd.DataFrame(response.data)
            return df, None
        else:
            return pd.DataFrame(), "No data found"
    except Exception as e:
        return pd.DataFrame(), str(e)

@st.cache_data(ttl=300)  # Cache for 5 minutes since this is expensive
def load_all_data(status_filter=None):
    """Load all data from Supabase without pagination limits"""
    try:
        supabase = get_supabase_client()
        all_data = []
        page_size = 1000  # Use smaller chunks to avoid timeouts
        page = 0

        # Create a progress container if we're in Streamlit context
        progress_placeholder = None
        try:
            progress_placeholder = st.empty()
        except:
            pass  # Not in Streamlit context

        while True:
            # Start building query
            query = supabase.table("images").select("*")

            # Apply filters
            if status_filter == "Valid Images":
                query = query.eq("image_status", True)
            elif status_filter == "Invalid Images":
                query = query.eq("image_status", False)

            # Apply pagination
            start_idx = page * page_size
            end_idx = start_idx + page_size - 1

            response = query.range(start_idx, end_idx).execute()

            if not response.data or len(response.data) == 0:
                break

            all_data.extend(response.data)

            # Update progress
            if progress_placeholder:
                progress_placeholder.info(f"Loading data... {len(all_data)} records loaded so far")

            # If we got less than page_size records, we've reached the end
            if len(response.data) < page_size:
                break

            page += 1

        # Clear progress indicator
        if progress_placeholder:
            progress_placeholder.empty()

        if all_data:
            df = pd.DataFrame(all_data)
            return df, None
        else:
            return pd.DataFrame(), "No data found"

    except Exception as e:
        return pd.DataFrame(), str(e)

@st.cache_data(ttl=60)
def get_filtered_count(status_filter=None, search_term=None):
    """Get count of filtered records"""
    try:
        supabase = get_supabase_client()
        query = supabase.table("images").select("id", count="exact")

        if status_filter == "Valid Images":
            query = query.eq("image_status", True)
        elif status_filter == "Invalid Images":
            query = query.eq("image_status", False)

        if search_term:
            query = query.or_(f"image_title.ilike.%{search_term}%,image_alt.ilike.%{search_term}%")

        response = query.execute()
        return response.count, None
    except Exception as e:
        return 0, str(e)

def update_record(supabase_client, record_id, updates):
    """Update a single record in Supabase"""
    try:
        response = supabase_client.table("images").update(updates).eq("id", record_id).execute()

        # Check if the update was successful
        if response.data and len(response.data) > 0:
            return True, None
        else:
            return False, f"No record found with id {record_id} or update failed"

    except Exception as e:
        return False, f"Database error: {str(e)}"

def log_change(record_id, field, old_value, new_value):
    """Log a field change for debugging and tracking"""
    # Handle None/NaN values for display
    old_display = "NULL" if pd.isna(old_value) else str(old_value)
    new_display = "NULL" if pd.isna(new_value) else str(new_value)

    return {
        'record_id': record_id,
        'field': field,
        'old_value': old_display,
        'new_value': new_display
    }

def values_are_equal(val1, val2):
    """Compare two values accounting for NaN, None, and type differences"""
    # Handle NaN values
    if pd.isna(val1) and pd.isna(val2):
        return True
    if pd.isna(val1) or pd.isna(val2):
        return False

    # Handle None values
    if val1 is None and val2 is None:
        return True
    if val1 is None or val2 is None:
        return False

    # Convert to strings and strip whitespace for comparison
    str_val1 = str(val1).strip()
    str_val2 = str(val2).strip()

    return str_val1 == str_val2

def get_overall_progress():
    """Get overall progress statistics"""
    try:
        supabase = get_supabase_client()

        # Get total count
        total = supabase.table("images").select("id", count="exact").execute()

        # Get completed count (has prompt filled)
        completed = supabase.table("images").select("id", count="exact").not_.is_("prompt", None).neq("prompt", "").execute()

        # Get valid/invalid counts
        valid = supabase.table("images").select("id", count="exact").eq("image_status", True).execute()
        invalid = supabase.table("images").select("id", count="exact").eq("image_status", False).execute()

        # Calculate progress
        remaining = total.count - completed.count
        completion_rate = (completed.count / total.count * 100) if total.count > 0 else 0

        return {
            "total": total.count,
            "completed": completed.count,
            "remaining": remaining,
            "completion_rate": completion_rate,
            "valid": valid.count,
            "invalid": invalid.count
        }
    except Exception as e:
        st.error(f"Error loading progress: {str(e)}")
        return None

def progress_dashboard():
    """Overall progress dashboard"""
    st.header("Progress Dashboard")

    # Get progress data
    progress = get_overall_progress()

    if progress:
        # Main progress metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Images", f"{progress['total']:,}")
        with col2:
            st.metric("Completed", f"{progress['completed']:,}")
        with col3:
            st.metric("Remaining", f"{progress['remaining']:,}")
        with col4:
            st.metric("Progress", f"{progress['completion_rate']:.1f}%")

        # Progress bar
        st.progress(progress['completion_rate'] / 100)

        # Additional metrics
        st.markdown("---")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Valid Images", f"{progress['valid']:,}")
        with col2:
            st.metric("Invalid Images", f"{progress['invalid']:,}")
        with col3:
            not_reviewed = progress['total'] - progress['valid'] - progress['invalid']
            st.metric("Not Reviewed", f"{not_reviewed:,}")

        # Source-level progress
        st.markdown("---")
        st.subheader("Progress by Source")

        try:
            # Get source-level statistics
            supabase = get_supabase_client()

            # Get all sources with their progress
            sources_query = """
                SELECT
                    source_url,
                    COUNT(*) as total_images,
                    COUNT(CASE WHEN prompt IS NOT NULL AND prompt != '' THEN 1 END) as completed_images,
                    COUNT(CASE WHEN image_status = true THEN 1 END) as valid_images,
                    COUNT(CASE WHEN image_status = false THEN 1 END) as invalid_images
                FROM images
                GROUP BY source_url
                ORDER BY total_images DESC
            """

            # Note: This is a simplified approach. In a real deployment, you'd use Supabase's RPC function
            # For now, let's get basic source stats
            all_data = supabase.table("images").select("source_url, prompt, image_status").execute()

            if all_data.data:
                df = pd.DataFrame(all_data.data)

                # Calculate source-level stats
                source_stats = []
                for source_url in df['source_url'].unique():
                    source_df = df[df['source_url'] == source_url]
                    total = len(source_df)
                    completed = len(source_df[source_df['prompt'].notna() & (source_df['prompt'] != '')])
                    valid = len(source_df[source_df['image_status'] == True])
                    invalid = len(source_df[source_df['image_status'] == False])

                    completion_pct = (completed / total * 100) if total > 0 else 0

                    source_stats.append({
                        "Source URL": source_url,
                        "Total": total,
                        "Completed": completed,
                        "Valid": valid,
                        "Invalid": invalid,
                        "Progress %": f"{completion_pct:.1f}%"
                    })

                # Sort by total images descending
                source_stats = sorted(source_stats, key=lambda x: x['Total'], reverse=True)

                # Show top sources
                if source_stats:
                    st.dataframe(
                        pd.DataFrame(source_stats[:20]),  # Show top 20 sources
                        use_container_width=True,
                        column_config={
                            "Source URL": st.column_config.LinkColumn("Source URL", width="large")
                        }
                    )

                    if len(source_stats) > 20:
                        st.info(f"Showing top 20 sources out of {len(source_stats)} total")

        except Exception as e:
            st.error(f"Error loading source statistics: {str(e)}")
    else:
        st.error("Unable to load progress data")

def main():
    st.title("Vietnam Airlines Image Database Editor")

    # Add navigation
    page = st.selectbox(
        "Select Mode",
        ["Progress Dashboard", "Review Images", "Browse Data"],
        index=0
    )

    st.markdown("---")

    if page == "Progress Dashboard":
        progress_dashboard()
        return

    # Initialize session state for pagination
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0
    if 'page_size' not in st.session_state:
        st.session_state.page_size = 100

    # Initialize session state for image review workflow
    if 'review_mode' not in st.session_state:
        st.session_state.review_mode = False
    if 'current_source_index' not in st.session_state:
        st.session_state.current_source_index = 0
    if 'current_image_index' not in st.session_state:
        st.session_state.current_image_index = 0
    if 'pending_changes' not in st.session_state:
        st.session_state.pending_changes = {}

    # Set review mode based on page selection
    st.session_state.review_mode = (page == "Review Images")

    # Get total count
    with st.spinner("Loading database info..."):
        total_count, count_error = get_total_count()

    if count_error:
        st.error(f"Error loading database info: {count_error}")
        return

    # Display database overview
    st.subheader("Database Overview")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Records", f"{total_count:,}")

    # Calculate other metrics from current view (approximation)
    with col2:
        st.metric("Pages Available", f"{(total_count + st.session_state.page_size - 1) // st.session_state.page_size:,}")

    # Only show filters for Browse Data mode
    if page == "Browse Data":
        with col1:
            status_filter = st.selectbox(
                "Filter by Image Status",
                ["All", "Valid Images", "Invalid Images"]
            )

        with col2:
            group_by_source = st.checkbox("Group by Source URL", value=False)
    else:
        status_filter = "All"
        group_by_source = False

    with col3:
        page_size = st.selectbox(
            "Records per page",
            [50, 100, 200, 500],
            index=1  # Default to 100
        )
        st.session_state.page_size = page_size

    with col4:
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    # Get filtered count
    filtered_count, filtered_error = get_filtered_count(
        status_filter if status_filter != "All" else None
    )

    if filtered_error:
        st.error(f"Error getting filtered count: {filtered_error}")
        return

    max_pages = (filtered_count + page_size - 1) // page_size if filtered_count > 0 else 1

    # Pagination controls
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 1, 2])

    with col1:
        if st.button("First", disabled=(st.session_state.current_page == 0)):
            st.session_state.current_page = 0
            st.rerun()

    with col2:
        if st.button("Previous", disabled=(st.session_state.current_page == 0)):
            st.session_state.current_page -= 1
            st.rerun()

    with col3:
        st.write(f"**Page {st.session_state.current_page + 1} of {max_pages}** ({filtered_count:,} records)")

    with col4:
        if st.button("Next", disabled=(st.session_state.current_page >= max_pages - 1)):
            st.session_state.current_page += 1
            st.rerun()

    with col5:
        if st.button("Last", disabled=(st.session_state.current_page >= max_pages - 1)):
            st.session_state.current_page = max_pages - 1
            st.rerun()

    # Load data based on mode
    if st.session_state.review_mode:
        # Load all data for review mode
        with st.spinner("Loading all data for review..."):
            all_df, error = load_all_data(status_filter=None)

        if error:
            st.error(f"Error loading data: {error}")
            return

        if all_df.empty:
            st.warning("No data available")
            return

        st.info(f"Loaded {len(all_df)} total records for review")

        # Group by source_url for review workflow
        if 'source_url' in all_df.columns:
            sources = all_df['source_url'].unique()
            st.info(f"Found {len(sources)} unique sources")

            # Implement review workflow
            st.markdown("---")
            st.header("Image Review Workflow")

            if len(sources) == 0:
                st.warning("No sources found")
                return

            # Ensure indices are valid
            if st.session_state.current_source_index >= len(sources):
                st.session_state.current_source_index = 0

            current_source = sources[st.session_state.current_source_index]
            source_images = all_df[all_df['source_url'] == current_source].reset_index(drop=True)

            if st.session_state.current_image_index >= len(source_images):
                st.session_state.current_image_index = 0

            if len(source_images) == 0:
                st.warning(f"No images found for source: {current_source}")
                return

            current_image = source_images.iloc[st.session_state.current_image_index]

            # Progress indicators - larger spacing
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns([2, 3, 2, 3])
            with col1:
                st.markdown(f"### Source: {st.session_state.current_source_index + 1}/{len(sources)}")
            with col2:
                source_name = current_source.split('/')[-1] if '/' in current_source else current_source
                st.markdown(f"### Current: {source_name}")
            with col3:
                st.markdown(f"### Image: {st.session_state.current_image_index + 1}/{len(source_images)}")
            with col4:
                total_images = len(all_df)
                current_position = sum(len(all_df[all_df['source_url'] == s]) for s in sources[:st.session_state.current_source_index]) + st.session_state.current_image_index + 1
                st.markdown(f"### Overall: {current_position}/{total_images}")

            st.markdown("---")

            # Large image display and editing form - bigger layout
            col1, col2 = st.columns([1.2, 1])

            with col1:
                st.subheader("Image Preview")
                st.markdown("<br>", unsafe_allow_html=True)
                if pd.notna(current_image.get('image_url')):
                    st.image(current_image['image_url'], use_container_width=True)
                else:
                    st.warning("No image URL available")

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f"**Image Title:** {current_image.get('image_title', 'N/A')}")
                st.markdown(f"**Alt Text:** {current_image.get('image_alt', 'N/A')}")
                st.markdown(f"**Source URL:** {current_source}")

            with col2:
                st.subheader("Edit Fields")

                # Get current values (with pending changes override)
                record_id = current_image['id']
                current_values = st.session_state.pending_changes.get(record_id, {})

                # Edit form - larger inputs
                st.markdown("<br>", unsafe_allow_html=True)
                with st.form(f"edit_form_{record_id}"):
                    prompt = st.text_area(
                        "Prompt",
                        value=current_values.get('prompt', current_image.get('prompt', '')),
                        height=200,
                        help="Describe what this image represents"
                    )

                    st.markdown("<br>", unsafe_allow_html=True)
                    image_status = st.checkbox(
                        "Valid Image",
                        value=current_values.get('image_status', current_image.get('image_status', False)),
                        help="Check if this image is valid and should be kept"
                    )

                    st.markdown("<br>", unsafe_allow_html=True)
                    notes = st.text_area(
                        "Notes",
                        value=current_values.get('notes', current_image.get('notes', '')),
                        height=150,
                        help="Internal notes about this image"
                    )

                    st.markdown("<br>", unsafe_allow_html=True)
                    ref_image_url = st.text_input(
                        "Reference Image URL",
                        value=current_values.get('ref_image_url', current_image.get('ref_image_url', '')),
                        help="URL to a reference image if applicable"
                    )

                    st.markdown("<br>", unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        save_changes = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
                    with col2:
                        save_and_next = st.form_submit_button("Save & Next", use_container_width=True)

                # Handle form submission
                if save_changes or save_and_next:
                    changes = {}
                    if prompt != current_image.get('prompt', ''):
                        changes['prompt'] = prompt
                    if image_status != current_image.get('image_status', False):
                        changes['image_status'] = image_status
                    if notes != current_image.get('notes', ''):
                        changes['notes'] = notes
                    if ref_image_url != current_image.get('ref_image_url', ''):
                        changes['ref_image_url'] = ref_image_url

                    if changes:
                        st.session_state.pending_changes[record_id] = {
                            **current_values,
                            **changes
                        }
                        st.success("Changes saved locally")

                    if save_and_next:
                        # Move to next image
                        if st.session_state.current_image_index < len(source_images) - 1:
                            st.session_state.current_image_index += 1
                        else:
                            # Move to next source
                            if st.session_state.current_source_index < len(sources) - 1:
                                st.session_state.current_source_index += 1
                                st.session_state.current_image_index = 0
                            else:
                                st.success("All images reviewed!")
                        st.rerun()

            # Navigation controls - larger spacing and buttons
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("<br>", unsafe_allow_html=True)

            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])

            with col1:
                if st.button("First Image", use_container_width=True):
                    st.session_state.current_source_index = 0
                    st.session_state.current_image_index = 0
                    st.rerun()

            with col2:
                if st.button("Previous", use_container_width=True):
                    if st.session_state.current_image_index > 0:
                        st.session_state.current_image_index -= 1
                    elif st.session_state.current_source_index > 0:
                        st.session_state.current_source_index -= 1
                        prev_source = sources[st.session_state.current_source_index]
                        prev_source_images = all_df[all_df['source_url'] == prev_source]
                        st.session_state.current_image_index = len(prev_source_images) - 1
                    st.rerun()

            with col3:
                if st.button("Save All to Database", type="secondary", use_container_width=True):
                    if st.session_state.pending_changes:
                        # Implement save logic here
                        supabase_client = get_supabase_client()
                        success_count = 0
                        error_count = 0

                        with st.spinner("Saving all changes..."):
                            for record_id, changes in st.session_state.pending_changes.items():
                                success, error = update_record(supabase_client, record_id, changes)
                                if success:
                                    success_count += 1
                                else:
                                    error_count += 1

                        if success_count > 0:
                            st.success(f"Saved {success_count} records to database!")
                            st.session_state.pending_changes = {}
                            st.rerun()
                        if error_count > 0:
                            st.error(f"Failed to save {error_count} records")
                    else:
                        st.info("No changes to save")

            with col4:
                if st.button("Next", use_container_width=True):
                    if st.session_state.current_image_index < len(source_images) - 1:
                        st.session_state.current_image_index += 1
                    elif st.session_state.current_source_index < len(sources) - 1:
                        st.session_state.current_source_index += 1
                        st.session_state.current_image_index = 0
                    st.rerun()

            with col5:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### Navigation")

            # Show pending changes count
            if st.session_state.pending_changes:
                st.markdown("<br>", unsafe_allow_html=True)
                st.info(f"{len(st.session_state.pending_changes)} records have unsaved changes")
        else:
            st.error("No source_url column found")
        return

    # Load current page data for browse mode
    with st.spinner(f"Loading page {st.session_state.current_page + 1}..."):
        df, error = load_data_paginated(
            page=st.session_state.current_page,
            page_size=page_size,
            status_filter=status_filter if status_filter != "All" else None
        )

    if error:
        st.error(f"Error loading data: {error}")
        return

    if df.empty:
        st.warning("No data available for current filters and page")
        return

    # Reorder columns for better visibility - put most important columns first
    desired_order = ['image_url', 'image_status', 'prompt', 'source_url', 'image_title', 'image_alt', 'id']
    available_cols = [col for col in desired_order if col in df.columns]
    remaining_cols = [col for col in df.columns if col not in desired_order]
    df = df[available_cols + remaining_cols]

    st.markdown("---")

    # Configure column types with image rendering
    column_config = {
        "id": st.column_config.TextColumn("ID", disabled=True, width="small"),
        "image_url": st.column_config.ImageColumn("Image Preview", width=300, help="Click to view larger image"),
        "image_title": st.column_config.TextColumn("Image Title", width="medium"),
        "image_alt": st.column_config.TextColumn("Image Alt", width="medium"),
        "source_url": st.column_config.LinkColumn("Source URL", width="medium"),
        "image_status": st.column_config.CheckboxColumn("Valid", width="small"),
        "prompt": st.column_config.TextColumn("Prompt", width="large"),
        "notes": st.column_config.TextColumn("Notes", width="medium"),
        "ref_image_url": st.column_config.LinkColumn("Ref Image URL", width="medium")
    }

    if group_by_source and 'source_url' in df.columns:
        # Group by source_url and show overview
        grouped = df.groupby('source_url')
        source_counts = grouped.size().reset_index(name='image_count')
        source_counts = source_counts.sort_values('image_count', ascending=False)

        st.subheader(f"Source Overview ({len(source_counts)} sources, {len(df)} total images)")

        # Show source summary table
        st.dataframe(
            source_counts,
            column_config={
                "source_url": st.column_config.LinkColumn("Source URL", width="large"),
                "image_count": st.column_config.NumberColumn("Images", width="small")
            },
            hide_index=True,
            use_container_width=True
        )

        st.markdown("---")
        st.subheader("Edit Images by Source")

        # Create optimized column config for editing workflow
        edit_column_config = {
            "image_url": st.column_config.ImageColumn("Preview", width=200),
            "prompt": st.column_config.TextColumn("Prompt", width="large"),
            "image_status": st.column_config.CheckboxColumn("Valid", width="small"),
            "image_title": st.column_config.TextColumn("Title", width="medium"),
            "image_alt": st.column_config.TextColumn("Alt Text", width="medium"),
            "id": st.column_config.TextColumn("ID", disabled=True, width="small")
        }

        # Display each source group in expandable sections
        edited_dfs = {}
        for source_url, group_df in grouped:
            # Get source page name for cleaner display
            source_name = source_url.split('/')[-1] if '/' in source_url else source_url
            if not source_name:
                source_name = source_url.split('/')[-2] if len(source_url.split('/')) > 2 else "Unknown"

            # Count valid/invalid images in this group
            valid_count = group_df['image_status'].sum() if 'image_status' in group_df.columns else 0
            invalid_count = len(group_df) - valid_count

            with st.expander(f"{source_name} ({len(group_df)} images: {valid_count} valid, {invalid_count} invalid)", expanded=False):
                st.write(f"**Full URL:** {source_url}")

                # Reorder columns for editing workflow
                edit_order = ['image_url', 'prompt', 'image_status', 'image_title', 'image_alt', 'id']
                available_cols = [col for col in edit_order if col in group_df.columns]
                remaining_cols = [col for col in group_df.columns if col not in edit_order]
                group_df_ordered = group_df[available_cols + remaining_cols].reset_index(drop=True)

                edited_group = st.data_editor(
                    group_df_ordered,
                    column_config=edit_column_config,
                    hide_index=True,
                    num_rows="fixed",
                    use_container_width=True,
                    key=f"editor_{hash(source_url)}_{st.session_state.current_page}"
                )
                edited_dfs[source_url] = edited_group

        # Combine all edited groups back into a single dataframe
        if edited_dfs:
            edited_df = pd.concat(edited_dfs.values(), ignore_index=True)
            # Restore original order for comparison
            if 'id' in edited_df.columns and 'id' in df.columns:
                original_id_order = df['id'].tolist()
                edited_df = edited_df.set_index('id').loc[original_id_order].reset_index()
        else:
            edited_df = df.copy()

    else:
        st.subheader(f"Editable Data ({len(df)} records on this page)")

        # Display editable dataframe normally
        edited_df = st.data_editor(
            df,
            column_config=column_config,
            hide_index=True,
            num_rows="fixed",
            use_container_width=True,
            key=f"data_editor_page_{st.session_state.current_page}"
        )

    # Debug section - show if any changes detected
    if not df.equals(edited_df):
        st.info("Changes detected in the data editor")

        # Show a sample of changes for debugging
        with st.expander("View Changes"):
            editable_fields = ['image_title', 'image_alt', 'image_status', 'prompt', 'notes', 'ref_image_url']
            changes_found = []

            for idx in range(min(5, len(df))):  # Show first 5 changes
                for field in editable_fields:
                    if field in df.columns and field in edited_df.columns:
                        original_val = df.iloc[idx][field]
                        edited_val = edited_df.iloc[idx][field]

                        if not values_are_equal(original_val, edited_val):
                            changes_found.append({
                                'Row': idx,
                                'Field': field,
                                'Original': str(original_val)[:50] if not pd.isna(original_val) else "NULL",
                                'Edited': str(edited_val)[:50] if not pd.isna(edited_val) else "NULL"
                            })

            if changes_found:
                st.write("Sample changes:")
                st.dataframe(pd.DataFrame(changes_found))

    # Handle updates
    if st.button("Save Changes to Database", type="primary"):
        supabase_client = get_supabase_client()

        # Find changes by comparing DataFrames directly
        changes_made = False
        success_count = 0
        error_count = 0
        errors = []
        change_log = []  # Track all changes made

        # Reset index to ensure proper comparison
        df_original = df.reset_index(drop=True)
        df_edited = edited_df.reset_index(drop=True)

        # Check if DataFrames have the same shape
        if len(df_original) != len(df_edited):
            st.error("Row count mismatch between original and edited data. Please refresh and try again.")
            return

        with st.spinner("Saving changes..."):
            progress_bar = st.progress(0)

            # Compare row by row
            editable_fields = ['image_title', 'image_alt', 'image_status', 'prompt', 'notes', 'ref_image_url']

            for idx in range(len(df_original)):
                try:
                    updates = {}
                    row_id = df_original.loc[idx, 'id']

                    # Compare each editable field
                    for field in editable_fields:
                        if field in df_original.columns and field in df_edited.columns:
                            original_val = df_original.loc[idx, field]
                            edited_val = df_edited.loc[idx, field]

                            # Use improved comparison function
                            if not values_are_equal(original_val, edited_val):
                                # Log the change
                                change_info = log_change(row_id, field, original_val, edited_val)
                                change_log.append(change_info)

                                # Prepare update value
                                if pd.isna(edited_val):
                                    updates[field] = None
                                else:
                                    updates[field] = edited_val

                    # Apply updates if any changes found
                    if updates:
                        success, error = update_record(supabase_client, row_id, updates)
                        if success:
                            success_count += 1
                            changes_made = True
                        else:
                            error_count += 1
                            errors.append(f"Record {row_id}: {error}")

                    progress_bar.progress((idx + 1) / len(df_original))

                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {idx}: {str(e)}")

            progress_bar.empty()

        # Show results
        if changes_made:
            st.success(f"Successfully updated {success_count} records with {len(change_log)} field changes!")

            # Display detailed change log
            if change_log:
                with st.expander(f"View {len(change_log)} Changes Made"):
                    change_df = pd.DataFrame(change_log)
                    st.dataframe(
                        change_df,
                        column_config={
                            "record_id": st.column_config.TextColumn("Record ID"),
                            "field": st.column_config.TextColumn("Field"),
                            "old_value": st.column_config.TextColumn("Old Value"),
                            "new_value": st.column_config.TextColumn("New Value")
                        },
                        hide_index=True,
                        use_container_width=True
                    )

            if error_count > 0:
                st.warning(f"Failed to update {error_count} records")
                with st.expander("View Errors"):
                    for error in errors:
                        st.error(error)

            # Clear cache to reload fresh data
            st.cache_data.clear()
            time.sleep(1)
            st.rerun()
        else:
            if change_log:
                st.warning(f"{len(change_log)} changes were detected but failed to save to database")
                with st.expander("View Detected Changes"):
                    change_df = pd.DataFrame(change_log)
                    st.dataframe(change_df, hide_index=True, use_container_width=True)
            else:
                st.info("No changes detected")

        if error_count > 0 and success_count == 0:
            st.error("All updates failed")
            with st.expander("View All Errors"):
                for error in errors:
                    st.error(error)

if __name__ == "__main__":
    main()
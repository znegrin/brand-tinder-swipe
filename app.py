"""
Brand Tinder Swipe - A brand workshop voting app

Example images.csv format:
---
id,url,label
img_001,https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800,Abstract gradient
img_002,https://images.unsplash.com/photo-1557683316-973673baf926?w=800,Vibrant colors
img_003,images/local_image.png,Local brand concept
---

Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import uuid
import os
import base64
from datetime import datetime
from pathlib import Path

# Configuration
IMAGES_CSV = "images.csv"
VOTES_CSV = "votes.csv"
IMAGES_FOLDER = "images"

# Page config - must be first Streamlit command
st.set_page_config(
    page_title="Brand Tinder Swipe",
    page_icon="🎨",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for cleaner UI
st.markdown("""
<style>
    .stApp {
        max-width: 900px;
        margin: 0 auto;
    }
    .main-title {
        text-align: center;
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .progress-text {
        text-align: center;
        font-size: 1rem;
        color: #888;
        margin-bottom: 1rem;
    }
    .image-label {
        text-align: center;
        font-style: italic;
        color: #555;
        margin-top: 0.5rem;
    }
    .keyboard-hint {
        text-align: center;
        font-size: 0.85rem;
        color: #aaa;
        margin-top: 1rem;
    }
    .vote-button {
        font-size: 1.5rem;
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 1rem;
        justify-content: center;
    }
    .stat-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
        margin: 0.5rem 0;
    }
    .stat-number {
        font-size: 2.5rem;
        font-weight: 700;
        color: #333;
    }
    .stat-label {
        color: #666;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "user_name" not in st.session_state:
        st.session_state.user_name = None
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0
    if "finished" not in st.session_state:
        st.session_state.finished = False
    if "started" not in st.session_state:
        st.session_state.started = False


def load_images():
    """Load images from CSV file."""
    if not os.path.exists(IMAGES_CSV):
        return None, "images.csv not found. Please create it with columns: id, url, label"
    
    try:
        df = pd.read_csv(IMAGES_CSV)
        required_cols = ["id", "url"]
        if not all(col in df.columns for col in required_cols):
            return None, "images.csv must have 'id' and 'url' columns"
        
        if len(df) == 0:
            return None, "images.csv is empty. Please add some images to vote on."
        
        # Ensure label column exists
        if "label" not in df.columns:
            df["label"] = ""
            
        # Ensure columns are strings and fill NaNs
        df["url"] = df["url"].fillna("").astype(str).str.strip()
        df["id"] = df["id"].fillna("").astype(str).str.strip()
        
        return df, None
    except Exception as e:
        return None, f"Error loading images.csv: {str(e)}"


def get_image_path(url: str) -> str:
    """Get the proper image path/URL."""
    if pd.isna(url) or not isinstance(url, str):
        return ""
    
    if url.startswith(("http://", "https://")):
        return url
    # Local file - check in images folder
    return os.path.join(IMAGES_FOLDER, url) if not url.startswith(IMAGES_FOLDER) else url


def load_votes():
    """Load existing votes from CSV."""
    if not os.path.exists(VOTES_CSV):
        return pd.DataFrame(columns=["session_id", "user_name", "image_id", "vote", "timestamp"])
    
    try:
        df = pd.read_csv(VOTES_CSV)
        # Ensure image_id is string to match images_df
        if "image_id" in df.columns:
            df["image_id"] = df["image_id"].astype(str).str.strip()
        return df
    except Exception:
        return pd.DataFrame(columns=["session_id", "user_name", "image_id", "vote", "timestamp"])


def save_vote(session_id: str, user_name: str, image_id: str, vote: str):
    """Save or update a vote."""
    timestamp = datetime.now().isoformat()
    votes_df = load_votes()
    
    # Check for existing vote from this session for this image
    mask = (votes_df["session_id"] == session_id) & (votes_df["image_id"] == image_id)
    
    if mask.any():
        # Update existing vote
        votes_df.loc[mask, "vote"] = vote
        votes_df.loc[mask, "timestamp"] = timestamp
    else:
        # Add new vote
        new_vote = pd.DataFrame([{
            "session_id": session_id,
            "user_name": user_name,
            "image_id": image_id,
            "vote": vote,
            "timestamp": timestamp
        }])
        votes_df = pd.concat([votes_df, new_vote], ignore_index=True)
    
    # Save to CSV
    votes_df.to_csv(VOTES_CSV, index=False)


def get_user_vote_summary(session_id: str):
    """Get vote summary for current user."""
    votes_df = load_votes()
    user_votes = votes_df[votes_df["session_id"] == session_id]
    
    summary = {
        "total": len(user_votes),
        "yes": len(user_votes[user_votes["vote"] == "yes"]),
        "no": len(user_votes[user_votes["vote"] == "no"]),
        "maybe": len(user_votes[user_votes["vote"] == "maybe"])
    }
    return summary


def get_aggregate_stats():
    """Get aggregate statistics across all users."""
    votes_df = load_votes()
    
    if len(votes_df) == 0:
        return None
    
    # Calculate yes percentage for each image
    stats = votes_df.groupby("image_id").agg(
        total_votes=("vote", "count"),
        yes_votes=("vote", lambda x: (x == "yes").sum()),
        no_votes=("vote", lambda x: (x == "no").sum()),
        maybe_votes=("vote", lambda x: (x == "maybe").sum())
    ).reset_index()
    
    stats["yes_percentage"] = (stats["yes_votes"] / stats["total_votes"] * 100).round(1)
    # Weighted score: yes_percentage * log(total_votes + 1) to balance approval rate with sample size
    import numpy as np
    stats["weighted_score"] = stats["yes_percentage"] * np.log1p(stats["total_votes"])
    stats = stats.sort_values(["weighted_score", "yes_percentage"], ascending=[False, False])
    
    return stats


def reset_session():
    """Reset session for a new user."""
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.user_name = None
    st.session_state.current_index = 0
    st.session_state.finished = False
    st.session_state.started = False


def show_intro_screen():
    """Display the intro/welcome screen."""
    st.markdown('<h1 class="main-title">🎨 Brand Tinder Swipe</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Quickly react to visual inspirations for the future ZenML brand</p>',
        unsafe_allow_html=True
    )
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### How it works")
        st.markdown("""
        1. You'll see a series of brand inspiration images
        2. For each image, vote with your gut reaction:
           - 👍 **Yes** — Feels like future ZenML
           - 👎 **No** — Not our vibe  
           - 🤔 **Maybe** — Worth discussing
        3. Go fast! Trust your instincts.
        """)
        
        st.markdown("---")
        
        user_name = st.text_input(
            "Your name or alias",
            placeholder="e.g., Alex, Designer_1, etc.",
            key="name_input"
        )
        
        st.markdown("")
        
        if st.button("🚀 Start Swiping", use_container_width=True, type="primary"):
            if user_name.strip():
                st.session_state.user_name = user_name.strip()
                st.session_state.started = True
                st.rerun()
            else:
                st.error("Please enter your name or alias to continue.")


def render_media_content(file_path: str):
    """Helper to render image or video content."""
    is_video = file_path.lower().endswith(('.mp4', '.mov', '.webm'))
    
    try:
        if is_video:
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    video_bytes = f.read()
                    video_b64 = base64.b64encode(video_bytes).decode()
                    
                video_html = f"""
                    <video width="100%" autoplay loop muted playsinline style="border-radius: 5px;">
                        <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                """
                st.markdown(video_html, unsafe_allow_html=True)
                return True
            else:
                 st.error(f"Video file not found: {file_path}")
                 return False
        else:
            st.image(file_path, use_container_width=True)
            return True
    except Exception as e:
        st.error(f"Could not load content: {str(e)}")
        return False


def show_voting_screen(images_df: pd.DataFrame):
    """Display the main voting screen."""
    current_idx = st.session_state.current_index
    total_images = len(images_df)
    
    # Check if we're done
    if current_idx >= total_images:
        st.session_state.finished = True
        st.rerun()
        return
    
    current_image = images_df.iloc[current_idx]
    
    # Progress indicator
    progress = (current_idx) / total_images
    st.progress(progress)
    st.markdown(
        f'<p class="progress-text">Image {current_idx + 1} of {total_images}</p>',
        unsafe_allow_html=True
    )
    
    # Display image or video
    file_path = get_image_path(current_image["url"])
    content_loaded = render_media_content(file_path)
    
    # Show label if present
    label = current_image.get("label", "")
    if pd.notna(label) and str(label).strip():
        st.markdown(f'<p class="image-label">{label}</p>', unsafe_allow_html=True)
    
    st.markdown("")
    
    # Voting buttons
    col1, col2, col3 = st.columns(3)
    
    def handle_vote(vote_value):
        save_vote(
            st.session_state.session_id,
            st.session_state.user_name,
            current_image["id"],
            vote_value
        )
        st.session_state.current_index += 1
        st.rerun()
    
    with col1:
        if st.button("👎 No (N)", use_container_width=True, key="btn_no"):
            handle_vote("no")

    with col2:
        if st.button("🤔 Maybe (H)", use_container_width=True, key="btn_maybe"):
            handle_vote("maybe")

    with col3:
        if st.button("👍 Yes (Y)", use_container_width=True, type="primary", key="btn_yes"):
            handle_vote("yes")
    
    # Skip button for broken content
    if not content_loaded:
        st.markdown("")
        if st.button("⏭️ Skip this item", use_container_width=True):
            st.session_state.current_index += 1
            st.rerun()
    
    # Keyboard shortcut handler using components.html for JS execution
    import streamlit.components.v1 as components
    components.html("""
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        // Ignore if user is typing in an input field
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        const key = e.key.toLowerCase();
        const buttons = doc.querySelectorAll('button[kind="secondary"], button[kind="primary"]');

        if (key === 'n') {
            buttons.forEach(b => { if (b.innerText.includes('No')) b.click(); });
        } else if (key === 'h') {
            buttons.forEach(b => { if (b.innerText.includes('Maybe')) b.click(); });
        } else if (key === 'y') {
            buttons.forEach(b => { if (b.innerText.includes('Yes')) b.click(); });
        }
    });
    </script>
    """, height=0)

    # Keyboard hints
    st.markdown(
        '<p class="keyboard-hint">💡 Tip: Use keyboard shortcuts N / H / Y to vote quickly!</p>',
        unsafe_allow_html=True
    )


def show_end_screen(images_df: pd.DataFrame):
    """Display the end/summary screen."""
    st.markdown('<h1 class="main-title">🎉 All Done!</h1>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="subtitle">Thanks for voting, {st.session_state.user_name}!</p>',
        unsafe_allow_html=True
    )
    
    st.markdown("---")
    
    # User's vote summary
    summary = get_user_vote_summary(st.session_state.session_id)
    
    st.markdown("### Your Votes")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{summary['total']}</div>
            <div class="stat-label">Total</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number" style="color: #28a745;">{summary['yes']}</div>
            <div class="stat-label">👍 Yes</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number" style="color: #dc3545;">{summary['no']}</div>
            <div class="stat-label">👎 No</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number" style="color: #ffc107;">{summary['maybe']}</div>
            <div class="stat-label">🤔 Maybe</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Bar chart of user's votes
    if summary['total'] > 0:
        st.markdown("")
        vote_data = pd.DataFrame({
            "Vote": ["👍 Yes", "👎 No", "🤔 Maybe"],
            "Count": [summary['yes'], summary['no'], summary['maybe']]
        })
        st.bar_chart(vote_data.set_index("Vote"), color="#7C3AED")
    
    st.markdown("---")
    
    # Aggregate stats
    st.markdown("### 📊 Team Results (All Voters)")
    
    agg_stats = get_aggregate_stats()
    
    if agg_stats is not None and len(agg_stats) > 0:
        # Merge with image labels
        # Use inner join to exclude votes for images that no longer exist in the deck
        agg_stats = agg_stats.merge(
            images_df[["id", "url", "label"]], 
            left_on="image_id", 
            right_on="id", 
            how="inner"
        )
        
        # Top images by yes percentage
        st.markdown("**Top Images by Approval Rate**")
        
        top_images = agg_stats.head(10).copy()
        
        # Display top results as an interactive list
        for rank, (_, row) in enumerate(top_images.iterrows(), start=1):
            label_text = row['label'] if pd.notna(row['label']) and str(row['label']).strip() else row['image_id']
            score = f"{row['yes_percentage']}% Yes ({row['total_votes']} votes)"

            with st.expander(f"#{rank} {label_text} — {score}"):
                file_path = get_image_path(row['url'])
                render_media_content(file_path)
                st.caption(f"Votes: {int(row['yes_votes'])} Yes, {int(row['no_votes'])} No, {int(row['maybe_votes'])} Maybe")
        
        # Total stats
        total_votes = agg_stats["total_votes"].sum()
        
        # Get unique voters only for the valid votes
        valid_image_ids = set(agg_stats["id"])
        all_votes = load_votes()
        valid_votes = all_votes[all_votes["image_id"].isin(valid_image_ids)]
        unique_voters = valid_votes["session_id"].nunique()
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Votes Cast", total_votes)
        with col2:
            st.metric("Unique Voters", unique_voters)
    else:
        st.info("No aggregate data available yet.")
    
    st.markdown("---")
    
    # Restart button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Restart with another name", use_container_width=True, type="primary"):
            reset_session()
            st.rerun()


def main():
    """Main application entry point."""
    # Initialize session state
    init_session_state()
    
    # Load images
    images_df, error = load_images()
    
    if error:
        st.error(f"❌ {error}")
        st.markdown("""
        ### Setup Instructions
        
        Create an `images.csv` file in the same folder as `app.py` with this format:
        
        ```csv
        id,url,label
        img_001,https://example.com/image1.jpg,Abstract gradient
        img_002,images/local_image.png,Local brand concept
        ```
        """)
        return
    
    # Route to appropriate screen
    if not st.session_state.started or not st.session_state.user_name:
        show_intro_screen()
    elif st.session_state.finished:
        show_end_screen(images_df)
    else:
        show_voting_screen(images_df)
    
    # Admin Section in Sidebar
    with st.sidebar:
        st.markdown("---")
        with st.expander("🔐 Admin Area"):
            admin_password = st.text_input("Admin Password", type="password")
            if admin_password == "zenml-brand":  # Simple hardcoded password
                st.success("Access Granted")

                if st.button("📊 View Results"):
                    st.session_state.user_name = "Admin"
                    st.session_state.started = True
                    st.session_state.finished = True
                    st.rerun()

                if st.button("🗑️ Clear All Votes", type="primary"):
                    if os.path.exists(VOTES_CSV):
                        try:
                            os.remove(VOTES_CSV)
                            st.toast("Votes database deleted!", icon="🗑️")
                            # Force reload
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.info("No votes found to delete.")
                
                st.markdown("---")
                st.caption(f"Current Votes: {len(load_votes())}")


if __name__ == "__main__":
    main()

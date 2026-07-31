"""
app.py
GitHub Developer Activity Dashboard — Streamlit entry point.

Enter any public GitHub username and get:
  - Profile summary
  - Language breakdown across repos
  - Most active/starred repos
  - Weekly commit activity across recent repos

Run locally:
    streamlit run app.py
"""

import streamlit as st
import plotly.express as px
from dotenv import load_dotenv

from github_data import (
    fetch_user_profile,
    fetch_repos,
    repos_to_dataframe,
    language_breakdown,
    commit_activity_to_dataframe,
    GitHubAPIError,
)

load_dotenv()

st.set_page_config(page_title="GitHub Dev Activity Dashboard", page_icon="📊", layout="wide")


# Cache API calls for 10 minutes so repeated views (or the same username twice)
# don't burn through the rate limit or slow the app down.
@st.cache_data(ttl=600, show_spinner=False)
def get_profile(username: str):
    return fetch_user_profile(username)


@st.cache_data(ttl=600, show_spinner=False)
def get_repos(username: str):
    return fetch_repos(username)


@st.cache_data(ttl=600, show_spinner=False)
def get_commit_df(username: str, repo_names: tuple):
    return commit_activity_to_dataframe(username, list(repo_names), max_repos=5)


st.title("📊 GitHub Developer Activity Dashboard")
st.caption("Enter any public GitHub username to generate a live activity dashboard.")

username = st.text_input("GitHub username", placeholder="e.g. torvalds")
go = st.button("Generate Dashboard", type="primary")

if go and username.strip():
    username = username.strip()

    try:
        with st.spinner(f"Fetching profile for {username}..."):
            profile = get_profile(username)
    except GitHubAPIError as e:
        st.error(str(e))
        st.stop()
    except Exception as e:
        st.error(f"Something went wrong talking to GitHub: {e}")
        st.stop()

    # --- Profile header ---
    col1, col2 = st.columns([1, 4])
    with col1:
        if profile.get("avatar_url"):
            st.image(profile["avatar_url"], width=120)
    with col2:
        st.subheader(profile.get("name") or username)
        if profile.get("bio"):
            st.write(profile["bio"])
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Public repos", profile.get("public_repos", 0))
        m2.metric("Followers", profile.get("followers", 0))
        m3.metric("Following", profile.get("following", 0))
        m4.metric("Account created", str(profile.get("created_at", ""))[:10])

    st.divider()

    # --- Repos ---
    try:
        with st.spinner("Fetching repositories..."):
            repos = get_repos(username)
            repo_df = repos_to_dataframe(repos)
    except GitHubAPIError as e:
        st.error(str(e))
        st.stop()

    if repo_df.empty:
        st.warning("This user has no public repositories.")
        st.stop()

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Languages Used")
        lang_df = language_breakdown(repo_df)
        if not lang_df.empty:
            fig = px.pie(lang_df, names="language", values="repo_count", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No language data available (repos may all be forks).")

    with col_b:
        st.subheader("Top Repos by Stars")
        top_repos = repo_df.sort_values("stars", ascending=False).head(8)
        fig2 = px.bar(top_repos, x="stars", y="name", orientation="h")
        fig2.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # --- Commit activity ---
    st.subheader("Weekly Commit Activity (recent repos)")
    st.caption("GitHub computes this in the background — if a repo shows 0, try refreshing in a moment.")
    active_repo_names = repo_df[~repo_df["is_fork"]]["name"].tolist()

    with st.spinner("Fetching commit history — this can take a few seconds..."):
        commit_df = get_commit_df(username, tuple(active_repo_names))

    if not commit_df.empty:
        fig3 = px.line(commit_df, x="week", y="commits", markers=True)
        st.plotly_chart(fig3, use_container_width=True)

        # --- Contribution heatmap (GitHub-style calendar, week x weekday) ---
        st.subheader("Contribution Heatmap")
        heat_df = commit_df.copy()
        heat_df["week_label"] = heat_df["week"].astype(str)
        fig4 = px.density_heatmap(
            heat_df,
            x="week_label",
            y=[""] * len(heat_df),  # single row, GitHub-calendar style strip
            z="commits",
            color_continuous_scale="Greens",
            nbinsx=len(heat_df),
        )
        fig4.update_layout(
            yaxis_visible=False,
            xaxis_title="Week",
            height=180,
            margin=dict(l=10, r=10, t=10, b=40),
        )
        fig4.update_xaxes(tickangle=90, tickfont=dict(size=8))
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No commit activity data available yet for this user's recent repos.")

    st.divider()

    # --- Raw data table ---
    with st.expander("View raw repo data"):
        st.dataframe(
            repo_df[["name", "language", "stars", "forks", "pushed_at", "is_fork"]],
            use_container_width=True,
        )

elif go:
    st.warning("Please enter a GitHub username first.")
else:
    st.info("👆 Enter a GitHub username above and click Generate Dashboard to get started.")

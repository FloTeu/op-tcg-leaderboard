import os
import streamlit as st

def main_bug_report():
    st.header("Bug Report")
    st.markdown(f"""
Spot a Bug? Share Your Thoughts!

Hey there! We want OPTCG Leaderboard to be as fun and smooth as possible. 
If you find any bugs or have some rad suggestions, don’t keep them to yourself! 
Fill out the feedback form and help us make things better. 
Thanks for being part of our journey!
""")
    google_forms_url = os.environ.get("GOOGLE_FORMS_FEEDBACK_URL", "")
    st.link_button("Send Feedback", google_forms_url, icon="📫")

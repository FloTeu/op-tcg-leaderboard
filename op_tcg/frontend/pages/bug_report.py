import os
from fasthtml import ft

def bug_report_page():
    # Get the Google Forms URL from environment variables
    google_forms_url = os.environ.get("GOOGLE_FORM_FEEDBACK_URL", "")
    
    return ft.Div(
        ft.H1("Bug Report", cls="text-3xl font-bold text-white mb-6"),
        
        ft.Div(
            ft.H2("Spot a Bug? Share Your Thoughts!", cls="text-xl font-semibold text-white mb-4"),
            
            ft.P(
                "Hey there! We want OPTCG Leaderboard to be as fun and smooth as possible.",
                cls="text-gray-300 mb-4"
            ),
            
            ft.P(
                "If you find any bugs or have some great suggestions, don't keep them to yourself!",
                cls="text-gray-300 mb-4"
            ),
            
            ft.P(
                "Fill out the feedback form and help us make things better.",
                cls="text-gray-300 mb-4"
            ),
            
            ft.P(
                "Thanks for being part of our journey!",
                cls="text-gray-300 mb-8"
            ),
            
            # Google Forms link button
            ft.A(
                ft.Div(
                    ft.Span("📫", cls="mr-2"),
                    "Send Feedback",
                    cls="inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200"
                ),
                href=google_forms_url,
                target="_blank",
                rel="noopener noreferrer",
                cls="inline-block"
            ) if google_forms_url else ft.P(
                "Feedback form is currently unavailable.",
                cls="text-gray-500 italic"
            ),
            
            cls="max-w-2xl"
        ),
        
        cls="min-h-screen px-4 py-8"
    ) 
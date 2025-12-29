from fasthtml import ft

def about_page():
    return ft.Div(
        ft.H1("About OP TCG Leaderboard", cls="text-3xl font-bold text-white mb-6"),
        ft.Div(
            ft.Div(
                ft.H2("Hey Nakama! 👋", cls="text-2xl font-bold text-white mb-4"),
                ft.P(
                    "I'm Florian. I'm a One Piece TCG player myself, and I've always had a passion for digging into data to find that extra edge.",
                    cls="text-gray-300 mb-4"
                ),
                ft.P(
                    "I created this leaderboard to help players of all experience levels get a better grasp of the meta. "
                    "Whether you're a pro analyzing matchups or a new player looking for an overview, I hope this data helps you see the bigger picture beyond just tournament results. "
                    "If you find value in these insights, then I've achieved my goal!",
                    cls="text-gray-300 mb-4"
                ),
                cls="mb-8"
            ),
            ft.Div(
                ft.H2("The Data & Shoutouts", cls="text-2xl font-bold text-white mb-4"),
                ft.P(
                    "The insights on this page are derived from tournament results and community data.",
                    cls="text-gray-300 mb-4"
                ),
                ft.P(
                    ft.Span("A massive shoutout to "),
                    ft.A("Limitless TCG", href="https://onepiece.limitlesstcg.com/", target="_blank", cls="text-blue-400 hover:text-blue-300 font-semibold"),
                    ft.Span(". Their API makes it possible to gather the match data needed to build these stats."),
                    cls="text-gray-300"
                ),
                cls="mb-8"
            ),
            ft.Div(
                ft.H2("Feedback", cls="text-2xl font-bold text-white mb-4"),
                ft.P(
                    "This is a passion project, and it's always a work in progress. If you spot a bug or have an idea for a new feature, feel free to use the Bug Report page!",
                    cls="text-gray-300"
                ),
            ),
            cls="bg-gray-800 rounded-lg p-8 shadow-lg"
        ),
        cls="container mx-auto px-4 py-8 max-w-4xl"
    )

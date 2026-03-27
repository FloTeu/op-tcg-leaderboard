from fasthtml import ft


def privacy_page():
    def section(title, *children):
        return ft.Div(
            ft.H2(title, cls="text-xl font-bold text-white mb-3"),
            *children,
            cls="mb-8"
        )

    def p(text):
        return ft.P(text, cls="text-gray-300 mb-3")

    def ul(*items):
        return ft.Ul(
            *[ft.Li(item, cls="text-gray-300 mb-1") for item in items],
            cls="list-disc list-inside space-y-1 mb-3"
        )

    return ft.Div(
        ft.H1("Privacy Policy", cls="text-3xl font-bold text-white mb-2"),
        ft.P("Last updated: March 2026", cls="text-gray-500 text-sm mb-8"),

        ft.Div(
            section(
                "1. Who We Are",
                p(
                    "OP TCG Leaderboard is a fan-made, non-commercial project that tracks One Piece TCG "
                    "tournament results, card prices, and meta statistics. It is operated by Florian Teutsch."
                ),
            ),
            section(
                "2. What Data We Collect",
                p("When you sign in with Google we receive and store the following data:"),
                ul(
                    "Your Google account ID (used as your unique user identifier)",
                    "Your display name",
                    "Your email address",
                    "Your profile picture URL",
                ),
                p(
                    "We also store any data you voluntarily create on this site, such as your watchlist "
                    "and your preference settings (default region and currency)."
                ),
                p("We do not collect payment information, precise location data, or any sensitive personal data."),
            ),
            section(
                "3. Why We Collect It",
                ul(
                    "To identify your account across sessions",
                    "To persist your watchlist and settings between visits",
                    "To allow you to delete your account and all associated data",
                ),
                p("We do not sell, rent, or share your personal data with third parties for marketing purposes."),
            ),
            section(
                "4. Google OAuth",
                p(
                    "Sign-in is handled via Google OAuth 2.0. By signing in you also agree to "
                    "Google's Privacy Policy and Terms of Service. We only request the minimum "
                    "OAuth scopes needed to identify your account (openid, email, profile)."
                ),
                ft.P(
                    "Google's privacy policy: ",
                    ft.A(
                        "https://policies.google.com/privacy",
                        href="https://policies.google.com/privacy",
                        target="_blank",
                        cls="text-blue-400 hover:text-blue-300"
                    ),
                    cls="text-gray-300 mb-3"
                ),
            ),
            section(
                "5. Data Retention",
                p(
                    "Your data is stored for as long as your account exists. "
                    "You can permanently delete your account — including your watchlist, settings, "
                    "and all stored profile data — at any time from the Settings page."
                ),
            ),
            section(
                "6. Your Rights (GDPR)",
                p("If you are located in the EU/EEA you have the following rights:"),
                ul(
                    "Right of access — request a copy of the data we hold about you",
                    "Right to rectification — request correction of inaccurate data",
                    "Right to erasure — delete your account and all data via Settings",
                    "Right to data portability — request your data in a machine-readable format",
                    "Right to object — object to processing of your personal data",
                ),
                ft.P(
                    "To exercise any of these rights, please open a bug report or contact us directly via the ",
                    ft.A("Bug Report", href="/bug-report", cls="text-blue-400 hover:text-blue-300"),
                    ft.Span(" page."),
                    cls="text-gray-300 mb-3"
                ),
            ),
            section(
                "7. Analytics",
                p(
                    "This site uses GoatCounter, a privacy-friendly, open-source analytics tool. "
                    "GoatCounter does not use cookies, does not collect personal data, and does not "
                    "track users across sites. Only anonymous page view counts and referrer information "
                    "are recorded."
                ),
                ft.P(
                    "GoatCounter's privacy policy: ",
                    ft.A(
                        "https://www.goatcounter.com/help/privacy",
                        href="https://www.goatcounter.com/help/privacy",
                        target="_blank",
                        cls="text-blue-400 hover:text-blue-300"
                    ),
                    cls="text-gray-300 mb-3"
                ),
            ),
            section(
                "8. Cookies & Sessions",
                p(
                    "We use a single session cookie to keep you signed in. This cookie is strictly "
                    "necessary for authentication and is not used for tracking or advertising."
                ),
            ),
            section(
                "9. Changes to This Policy",
                p(
                    "We may update this policy from time to time. The date at the top of this page "
                    "reflects the most recent revision. Continued use of the site after changes "
                    "constitutes acceptance of the updated policy."
                ),
            ),
            cls="bg-gray-800 rounded-lg p-8 shadow-lg"
        ),
        cls="container mx-auto px-4 py-8 max-w-3xl"
    )

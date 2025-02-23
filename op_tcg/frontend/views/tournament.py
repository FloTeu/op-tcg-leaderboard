from datetime import datetime

import streamlit as st

from op_tcg.backend.models.tournaments import TournamentExtended


def display_tournament_keyfacts(tournament: TournamentExtended, winner_name: str):
    st.write(f"""
    Name: {tournament.name}  {f'''
    Host: {tournament.host}  ''' if tournament.host else ""}{f'''
    Country: {tournament.country}  ''' if tournament.host else ""}
    Number Players: {tournament.num_players if tournament.num_players else "unknown"}  
    Winner: {winner_name}  
    Date: {tournament.tournament_timestamp.date() if isinstance(tournament.tournament_timestamp, datetime) else "unknown"} 
        """)
from op_tcg.backend.models.matches import MatchResult

def calculate_new_elo(current_elo: int, opponent_elo: int, result: MatchResult, k_factor=32):
    """
    Calculate the new Elo rating for a player based on the current rating,
    opponent's rating, and the match result.

    :param current_elo: int - The current Elo rating of the player
    :param opponent_elo: int - The Elo rating of the opponent
    :param result: MatchResult - The result of the match (0 for loss, 1 for draw, 2 for win)
    :param k_factor: int - The K-factor used in the Elo rating (default is 32)
    :return: int - The new Elo rating of the player
    """
    # Convert the result to the expected score format (0 for loss, 0.5 for draw, 1 for win)
    actual_score = result / 2

    # Calculate the expected score
    expected_score = 1 / (1 + 10 ** ((opponent_elo - current_elo) / 400))

    # Calculate the new Elo rating
    new_elo = current_elo + k_factor * (actual_score - expected_score)

    return round(new_elo)



def lid2win_rate(leader_id: str, df_meta_match_data) -> int:
    result_counts = df_meta_match_data.query(f"leader_id == '{leader_id}'").groupby("result").count()["id"]
    if 2 not in result_counts.index:
        return "0%"
    else:
        return f'{int(float("%.2f" % (result_counts.loc[2] / result_counts.sum())) * 100)}%'

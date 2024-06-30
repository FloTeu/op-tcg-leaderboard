from google.cloud import bigquery

from op_tcg.backend.models.leader import Leader


# TODO: Try to insert the functionality to op_tcg/backend/models/bq_classes.py
def update_bq_leader_row(bq_leader: Leader, table: bigquery.Table, client: bigquery.Client | None = None):
    """Creates new row in big query or if it already exists, the row get updated"""
    client = client if client else bigquery.Client()

    table_id = f"{table.project}.{table.dataset_id}.{table.table_id}"

    # Use MERGE to update if the row exists, or insert if it does not
    merge_query = f"""
    MERGE {table_id} T
    USING (SELECT 1) S
    ON T.id = @id
    WHEN MATCHED THEN
        UPDATE SET
            name = @name,
            life = @life,
            power = @power,
            release_meta = @release_meta,
            avatar_icon_url = @avatar_icon_url,
            image_url = @image_url,
            image_aa_url = @image_aa_url,
            colors = @colors,
            attributes = @attributes,
            ability = @ability,
            fractions = @fractions,
            language = @language
    WHEN NOT MATCHED THEN
        INSERT (id, name, life, power, release_meta, avatar_icon_url, image_url, image_aa_url, colors, attributes, ability, fractions, language)
        VALUES (@id, @name, @life, @power, @release_meta, @avatar_icon_url, @image_url, @image_aa_url, @colors, @attributes, @ability, @fractions, @language)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("id", "STRING", bq_leader.id),
            bigquery.ScalarQueryParameter("name", "STRING", bq_leader.name),
            bigquery.ScalarQueryParameter("life", "INT64", bq_leader.life),
            bigquery.ScalarQueryParameter("power", "INT64", bq_leader.power),
            bigquery.ScalarQueryParameter("release_meta", "STRING", bq_leader.release_meta.value if bq_leader.release_meta else None),
            bigquery.ScalarQueryParameter("avatar_icon_url", "STRING", bq_leader.avatar_icon_url),
            bigquery.ScalarQueryParameter("image_url", "STRING", bq_leader.image_url),
            bigquery.ScalarQueryParameter("image_aa_url", "STRING", bq_leader.image_aa_url),
            bigquery.ArrayQueryParameter("colors", "STRING", bq_leader.colors),
            bigquery.ArrayQueryParameter("attributes", "STRING", bq_leader.attributes),
            bigquery.ScalarQueryParameter("ability", "STRING", bq_leader.ability),
            bigquery.ArrayQueryParameter("fractions", "STRING", bq_leader.fractions),
            bigquery.ScalarQueryParameter("language", "STRING", bq_leader.language.value),
        ]
    )

    query_job = client.query(merge_query, job_config=job_config)
    query_job.result()  # Wait for the job to complete

    print("Row updated successfully")

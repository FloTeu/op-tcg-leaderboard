import functions_framework

from markupsafe import escape
from op_tcg.backend.etl.classes import EloUpdateToBigQueryEtlJob
from op_tcg.backend.models.input import MetaFormat


@functions_framework.http
def run_etl_elo_update(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
    request_json = request.get_json(silent=True)
    request_args = request.args

    if request_json and "meta_formats" in request_json:
        meta_formats = request_json["meta_formats"]
    elif request_args and "meta_formats" in request_args:
        meta_formats = request_args["meta_formats"]
    else:
        meta_formats = MetaFormat.to_list()

    print(meta_formats, type(meta_formats))

    etl_job = EloUpdateToBigQueryEtlJob(meta_formats=meta_formats, matches_csv_file_path=None)
    etl_job.run()
    return f"Success with meta formats {meta_formats}!"


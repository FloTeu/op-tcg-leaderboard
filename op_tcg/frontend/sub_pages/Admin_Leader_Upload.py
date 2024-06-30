import os
import tempfile
import requests

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from op_tcg.backend.etl.extract import limitless2bq_leader
from op_tcg.backend.etl.load import get_or_create_table
from op_tcg.backend.etl.load_update import update_bq_leader_row
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.leader import Leader, OPTcgLanguage, OPTcgColor, OPTcgAttribute
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.matches import LeaderWinRate
from op_tcg.backend.utils.utils import booleanize
from op_tcg.frontend.models.session import LeaderUploadForm
from op_tcg.frontend.sidebar import display_meta_select, display_release_meta_select, display_leader_color_multiselect, \
    display_leader_select
from op_tcg.frontend.utils.extract import get_leader_win_rate
from op_tcg.frontend.utils.leader_data import get_lid2ldata_dict_cached, lids_to_name_and_lids, lid_to_name_and_lid, \
    lname_and_lid_to_lid
from op_tcg.frontend.utils.utils import upload2gcp_storage, bq_client, run_bq_query

load_dotenv()


def display_upload_form(
        id_default_text: str | None = None,
        language_default_text: str | None = None,
        bq_leader_default_text: Leader | None = None,
        key: str = "upload_leader_form"
) -> tuple[Leader | None, str]:
    """
    return: BQLeader if form as correctly filled, None otherwise and an optional error message
    """
    bq_leader = None
    with st.form(key=key, clear_on_submit=False):
        id = st.text_input("Leader Id", help="e.g. OP01-001", value=id_default_text)
        language = st.selectbox("Language",
                                [language_default_text] if language_default_text else [OPTcgLanguage.EN,
                                                                                       OPTcgLanguage.JP],
                                help="Language of ability text")
        name = st.text_input("Leader Name", help="e.g. Charlotte Katakuri",
                             value=bq_leader_default_text.name if bq_leader_default_text else None)
        life = st.number_input("Leader Life", min_value=1, help="e.g. 5", step=1,
                               value=bq_leader_default_text.life if bq_leader_default_text else None)
        power = st.number_input("Leader Power", help="e.g. 5000", step=1000,
                                value=bq_leader_default_text.power if bq_leader_default_text else None)
        release_meta = st.selectbox("Release Meta", [
            bq_leader_default_text.release_meta] if bq_leader_default_text and bq_leader_default_text.release_meta else sorted(
            MetaFormat.to_list(), reverse=True),
                                    help="Sets like EB or pre-constructed decks match to the last released main set e.g. EB01 -> OP06")
        avatar_icon = st.text_input("Leader Avatar Icon", help="Public accessible url to an avatar icon of the leader",
                                    value=bq_leader_default_text.avatar_icon_url if bq_leader_default_text else None)

        image_url = st.text_input("Leader Card Image", help="Public accessible url to standard image",
                                  value=bq_leader_default_text.image_url if bq_leader_default_text else None)
        image_aa_url = st.text_input("Leader AA Card Image", help="Public accessible url to alternative artwork image",
                                     value=bq_leader_default_text.image_aa_url if bq_leader_default_text else None)
        colors = st.multiselect("Leader Colors", OPTcgColor.to_list(), help="Colors of the leader",
                                default=bq_leader_default_text.colors if bq_leader_default_text else None)
        attributes = st.multiselect("Leader Attribute", OPTcgAttribute.to_list(),
                                    help="Attribute of the leader, e.g. Slash",
                                    default=bq_leader_default_text.attributes if bq_leader_default_text else None)
        ability = st.text_area("Leader Ability", help="Ability of the leader",
                               value=bq_leader_default_text.ability if bq_leader_default_text else None)
        fractions = st.text_input("Leader Fractions",
                                  help="If the leader has more than one fraction, please split it by '/'",
                                  value="/".join(bq_leader_default_text.fractions) if bq_leader_default_text else None)

        submit_button = st.form_submit_button(label="Submit")

        if submit_button:

            st.session_state["submit_button_leader_upload_clicked"] = True
            try:
                # Note: None is used to trigger validation error
                bq_leader = Leader(id=id if id else None,
                                   name=name if name else None,
                                   life=life,
                                   power=power,
                                   release_meta=MetaFormat(release_meta) if release_meta else None,
                                   avatar_icon_url=avatar_icon if avatar_icon else None,
                                   image_url=image_url if image_url else None,
                                   image_aa_url=image_aa_url if image_aa_url else None,
                                   colors=[OPTcgColor(c) for c in colors] if colors else None,
                                   ability=ability if ability else None,
                                   attributes=attributes if attributes else None,
                                   fractions=fractions.split("/") if fractions else None,
                                   language=OPTcgLanguage(language) if language else None
                                   )
            except ValidationError as ex:
                error_text = "**Whoops! There were some problems with your input:**"
                for error in ex.errors():
                    if "loc" in error and "msg" in error:
                        location = ".".join(error["loc"]).replace("__root__.", "")  # type: ignore
                        error_msg = f"**{location}:** " + error["msg"]
                        error_text += "\n\n" + error_msg
                    else:
                        # Fallback
                        error_text += "\n\n" + str(error)
                return None, error_text
    return bq_leader, ""


# def upload_all_leader_ids():
#     if st.button("Uplaod all leader"):
#         all_leader_id_rows = run_bq_query(
#             f"""SELECT DISTINCT leader_id FROM `{st.secrets["gcp_service_account"]["project_id"]}.matches.leader_elo` as t0
#     LEFT JOIN `{st.secrets["gcp_service_account"]["project_id"]}.leaders.leaders` as t1
#     ON t0.leader_id = t1.id
#     where t1.id is NULL""")
#         all_leader_ids = [row["leader_id"] for row in all_leader_id_rows]
#         language_default_text = OPTcgLanguage.EN
#         for leader_id in all_leader_ids:
#             bq_leader = limitless2bq_leader(leader_id, language=language_default_text)
#             print(f"Upload leader: {leader_id} {bq_leader.name}")
#             upload2bq_and_storage(bq_leader)

def main_admin_leader_upload():
    with st.sidebar:
        release_meta_formats: list[MetaFormat] | None = display_release_meta_select(multiselect=True)
        selected_leader_colors: list[OPTcgColor] | None = display_leader_color_multiselect()
        only_without_meta: bool = st.checkbox("Without release meta")

    lid_to_ldata: dict[str, Leader] = get_lid2ldata_dict_cached()
    # filter leader data
    if release_meta_formats:
        lid_to_ldata = {lid: ldata for lid, ldata in lid_to_ldata.items() if
                        ldata.release_meta in release_meta_formats}
    if selected_leader_colors:
        lid_to_ldata = {lid: ldata for lid, ldata in lid_to_ldata.items() if
                        any(c in selected_leader_colors for c in ldata.colors)}
    if only_without_meta:
        lid_to_ldata = {lid: ldata for lid, ldata in lid_to_ldata.items() if ldata.release_meta is None}
    num_leaders = len(lid_to_ldata)

    tab1, tab2 = st.tabs(["Edit", "New"])
    with tab1:
        key = "upload_leader_form_edit"
        session_upload_form_data = st.session_state.get(f"{key}_data", LeaderUploadForm())
        st.header("Edit existing leader")
        st.write(f"Number existing leaders {num_leaders}")
        if len(lid_to_ldata) == 0:
            st.warning("No leaders available")
        else:
            available_leader_ids = [lid_to_name_and_lid(lid, ldata.name) for lid, ldata in lid_to_ldata.items()]
            selected_leader_name: str = display_leader_select(available_leader_ids=available_leader_ids,
                                                              multiselect=False, default=available_leader_ids[0])
            selected_leader_id: str = lname_and_lid_to_lid(selected_leader_name)
            bq_leader: Leader = lid_to_ldata[selected_leader_id]
            if session_upload_form_data.bq_leader is None or (bq_leader.id != session_upload_form_data.bq_leader.id):
                session_upload_form_data.bq_leader = bq_leader
                st.session_state[f"{key}_data"] = session_upload_form_data
            display_upload_view(session_upload_form_data, bq_leader.id, bq_leader.language, True,
                                new_upload=False,
                                key=key)

    with tab2:
        key = "upload_leader_form_new"
        session_upload_form_data = st.session_state.get(f"{key}_data", LeaderUploadForm())
        st.header("Upload new leader")
        selected_meta_win_rate_data: list[LeaderWinRate] = get_leader_win_rate(meta_formats=MetaFormat.to_list())
        # leader ids which exists in win rate table (in match table as well) but not in leader table
        leader_ids_not_yet_uploaded = list(
            set([lwd.leader_id for lwd in selected_meta_win_rate_data]) - set(get_lid2ldata_dict_cached().keys()))
        selected_leader_id = None
        col1, col2 = st.columns(2)
        if leader_ids_not_yet_uploaded:
            with col2:
                st.write("Leaders not yet uploaded")
                selected_leader_id: str | None = display_leader_select(
                    available_leader_ids=leader_ids_not_yet_uploaded,
                    multiselect=False, default=None)
        id_default_text = col1.text_input("Leader Id", value=selected_leader_id, help="e.g. OP01-001")
        language_default_text = st.selectbox("Language", [OPTcgLanguage.EN, OPTcgLanguage.JP],
                                             help="Language of ability text")

        if st.button("Auto fill"):
            bq_leader = limitless2bq_leader(id_default_text, language=language_default_text)
            session_upload_form_data.bq_leader = bq_leader
            st.session_state[f"{key}_data"] = session_upload_form_data

        display_upload_view(session_upload_form_data, id_default_text, language_default_text, False,
                            new_upload=True,
                            key=key)
# else:
#     st.error("You are not allowed to see this page")

def display_upload_view(session_upload_form_data, id_default_text, language_default_text, expanded=False,
                        new_upload: bool = False,
                        key="upload_leader_form"):
    with st.expander("Open Form", expanded=expanded):
        bq_leader, error_text = display_upload_form(id_default_text=id_default_text,
                                                    language_default_text=language_default_text,
                                                    bq_leader_default_text=session_upload_form_data.bq_leader,
                                                    key=key
                                                    )
        if isinstance(bq_leader, Leader):
            session_upload_form_data.bq_leader = bq_leader
            session_upload_form_data.new_upload = new_upload
            st.session_state[f"{key}_data"] = session_upload_form_data
        else:
            bq_leader = session_upload_form_data.bq_leader
    if error_text:
        st.error(error_text)
    if isinstance(bq_leader, Leader):
        display_bq_leader(bq_leader)

        if st.button("Upload Leader", key=f"{key}_button"):
            upload2bq_and_storage(bq_leader)


def upload2bq_and_storage(bq_leader):
    with st.spinner('Upload Images to GCP Storage...'):
        for blob_dir, img_url in {"avatar": bq_leader.avatar_icon_url, "standard": bq_leader.image_url,
                                  "alt-art": bq_leader.image_aa_url}.items():
            with tempfile.NamedTemporaryFile() as tmp:
                img_data = requests.get(img_url).content
                tmp.write(img_data)
                file_type = img_url.split('.')[-1]
                upload2gcp_storage(path_to_file=tmp.name,
                                   blob_name=f"leader/images/{blob_dir}/{bq_leader.language.upper()}/{bq_leader.id}.{file_type}",
                                   content_type=f"image/{file_type}")

    with st.spinner('Upload Leader Data to GCP BigQuery...'):
        bq_leader_table = get_or_create_table(dataset_id=BQDataset.LEADERS,
                                              model=Leader, client=bq_client)

        # change image urls to gcp storage urls
        file_type = bq_leader.avatar_icon_url.split('.')[-1]
        bq_leader.avatar_icon_url = f"https://storage.googleapis.com/op-tcg-leaderboard-public/leader/images/avatar/{bq_leader.language.upper()}/{bq_leader.id}.{file_type}"
        file_type = bq_leader.image_url.split('.')[-1]
        bq_leader.image_url = f"https://storage.googleapis.com/op-tcg-leaderboard-public/leader/images/standard/{bq_leader.language.upper()}/{bq_leader.id}.{file_type}"
        file_type = bq_leader.image_aa_url.split('.')[-1]
        bq_leader.image_aa_url = f"https://storage.googleapis.com/op-tcg-leaderboard-public/leader/images/alt-art/{bq_leader.language.upper()}/{bq_leader.id}.{file_type}"

        update_bq_leader_row(bq_leader, table=bq_leader_table, client=bq_client)


def display_bq_leader(bq_leader):
    col1, col2, col3 = st.columns(3)
    col1.text("Avatar Icon")
    col1.image(bq_leader.avatar_icon_url)
    col2.text("Leader Card Image")
    col2.image(bq_leader.image_url)
    col3.text("Leader AA Card Image")
    col3.image(bq_leader.image_aa_url)
    st.json(bq_leader.model_dump_json())

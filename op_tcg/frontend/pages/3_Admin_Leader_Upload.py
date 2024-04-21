import os
import tempfile
import time

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from op_tcg.backend.etl.extract import limitless2bq_leader
from op_tcg.backend.etl.load import get_or_create_table, update_bq_leader_row
from op_tcg.backend.models.bq import BQTable, BQDataset
from op_tcg.backend.models.leader import BQLeader, OPTcgLanguage, OPTcgColor, OPTcgAttribute
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.utils import booleanize
from op_tcg.frontend.models.session import LeaderUploadForm
from op_tcg.frontend.utils import upload2gcp_storage, bq_client, run_bq_query

load_dotenv()


def display_upload_form(
                        id_default_text: str | None=None,
                        language_default_text: str | None=None,
                        bq_leader_default_text: BQLeader | None=None,
) -> tuple[BQLeader | None, str]:
    """
    return: BQLeader if form as correctly filled, None otherwise and an optional error message
    """
    bq_leader = None
    with st.form(key="upload_leader_form", clear_on_submit=False):
        id = st.text_input("Leader Id", help="e.g. OP01-001", value=id_default_text)
        language = st.selectbox("Language",
                                [language_default_text] if language_default_text else [OPTcgLanguage.EN, OPTcgLanguage.JP],
                                help="Language of ability text")
        name = st.text_input("Leader Name", help="e.g. Charlotte Katakuri", value=bq_leader_default_text.name if bq_leader_default_text else None)
        life = st.number_input("Leader Life", min_value=1, help="e.g. 5", step=1, value=bq_leader_default_text.life if bq_leader_default_text else None)
        power = st.number_input("Leader Power", help="e.g. 5000", step=1000, value=bq_leader_default_text.power if bq_leader_default_text else None)
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
        colors = st.multiselect("Leader Colors", OPTcgColor.to_list(), help="Colors of the leader", default=bq_leader_default_text.colors if bq_leader_default_text else None)
        attributes = st.multiselect("Leader Attribute", OPTcgAttribute.to_list(), help="Attribute of the leader, e.g. Slash", default=bq_leader_default_text.attributes if bq_leader_default_text else None)
        ability = st.text_area("Leader Ability", help="Ability of the leader", value=bq_leader_default_text.ability if bq_leader_default_text else None)

        submit_button = st.form_submit_button(label="Submit")

        if submit_button:

            st.session_state["submit_button_leader_upload_clicked"] = True
            try:
                # Note: None is used to trigger validation error
                bq_leader = BQLeader(id=id if id else None,
                                name=name if name else None,
                                life=life,
                                power=power,
                                release_meta=MetaFormat(release_meta) if release_meta else None,
                                avatar_icon=avatar_icon if avatar_icon else None,
                                image_url=image_url if image_url else None,
                                image_aa_url=image_aa_url if image_aa_url else None,
                                colors=[OPTcgColor(c) for c in colors] if colors else None,
                                ability=ability if ability else None,
                                attributes=attributes if attributes else None,
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

def main():
    if booleanize(os.environ.get("DEBUG", "")):
        if st.button("Uplaod all leader"):
            all_leader_id_rows = run_bq_query("""SELECT DISTINCT leader_id FROM `op-tcg-leaderboard-dev.matches.leader_elo` as t0
LEFT JOIN `op-tcg-leaderboard-dev.leaders.leaders` as t1
ON t0.leader_id = t1.id
where t1.id is NULL""")
            all_leader_ids = [row["leader_id"] for row in all_leader_id_rows]
            language_default_text = OPTcgLanguage.EN
            for leader_id in all_leader_ids:
                bq_leader = limitless2bq_leader(leader_id, language=language_default_text)
                print(f"Upload leader: {leader_id} {bq_leader.name}")
                upload2bq_and_storage(bq_leader)

        session_upload_form_data = st.session_state.get("session_upload_form_data", LeaderUploadForm())
        expanded = False
        id_default_text = st.text_input("Leader Id", help="e.g. OP01-001")
        language_default_text = st.selectbox("Language", [OPTcgLanguage.EN, OPTcgLanguage.JP], help="Language of ability text")

        if st.button("Auto fill"):
            bq_leader = limitless2bq_leader(id_default_text, language=language_default_text)
            session_upload_form_data.bq_leader = bq_leader
            st.session_state["session_upload_form_data"] = session_upload_form_data

        with st.expander("Open Form", expanded=expanded):
            bq_leader, error_text = display_upload_form(id_default_text=id_default_text,
                                                         language_default_text=language_default_text,
                                                         bq_leader_default_text=session_upload_form_data.bq_leader
                                                         )
            if isinstance(bq_leader, BQLeader):
                session_upload_form_data.bq_leader = bq_leader
                st.session_state["session_upload_form_data"] = session_upload_form_data
            else:
                bq_leader = session_upload_form_data.bq_leader

        if error_text:
            st.error(error_text)

        if isinstance(bq_leader, BQLeader):
            display_images(bq_leader)

            if st.button("Upload Leader"):
                upload2bq_and_storage(bq_leader)


def upload2bq_and_storage(bq_leader):
    with st.spinner('Upload Leader Data to GCP BigQuery...'):
        bq_leader_table = get_or_create_table(table_id=BQTable.LEADER_DATA, dataset_id=BQDataset.LEADERS,
                                              model=BQLeader, client=bq_client)
        update_bq_leader_row(bq_leader, table=bq_leader_table, client=bq_client)
    with st.spinner('Upload Images to GCP Storage...'):
        for blob_dir, img_url in {"avatar": bq_leader.avatar_icon_url, "standard": bq_leader.image_url,
                                  "alt-art": bq_leader.image_aa_url}.items():
            with tempfile.NamedTemporaryFile() as tmp:
                import requests
                img_data = requests.get(img_url).content
                tmp.write(img_data)
                file_type = img_url.split('.')[-1]
                upload2gcp_storage(path_to_file=tmp.name,
                                   blob_name=f"leader/images/{blob_dir}/{bq_leader.language.upper()}/{bq_leader.id}.{file_type}",
                                   content_type=f"image/{file_type}")


def display_images(bq_leader):
    col1, col2, col3 = st.columns(3)
    col1.text("Avatar Icon")
    col1.image(bq_leader.avatar_icon_url)
    col2.text("Leader Card Image")
    col2.image(bq_leader.image_url)
    col3.text("Leader AA Card Image")
    col3.image(bq_leader.image_aa_url)
    st.json(bq_leader.model_dump_json())


if __name__ == "__main__":
    main()
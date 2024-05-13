import streamlit as st
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import Leader, OPTcgColor, OPTcgAttribute, OPTcgLanguage
from op_tcg.frontend.utils.extract import get_leader_data


def get_template_leader() -> Leader:
    """Returns an artificial leader, which can be used if no leader data ist available"""
    return Leader(id="NaN",
           name="NaN",
           life=5,
           power=5000,
           release_meta=MetaFormat.to_list()[-1],
           avatar_icon_url="",
           image_url="",
           image_aa_url="",
           colors=[OPTcgColor.BLACK],
           attributes=[OPTcgAttribute.SLASH],
           ability="",
           fractions=[""],
           language=OPTcgLanguage.EN
           )

@st.cache_data(ttl=60*60) # 1 hour
def get_lid2ldata_dict_cached() -> dict[str, Leader]:
    bq_leaders: list[Leader] = get_leader_data()
    return {bq_leader_data.id: bq_leader_data for bq_leader_data in
                                                bq_leaders}


def lid2ldata(lid, leader_id2leader_data: dict[str, Leader] | None=None) -> Leader:
    """Return the leader data to a specific leader id. If no leader data is available, the template leader is used"""
    if leader_id2leader_data is None:
        leader_id2leader_data = get_lid2ldata_dict_cached()
    return leader_id2leader_data[lid] if lid in leader_id2leader_data else get_template_leader()


def leader_id2aa_image_url(leader_id: str):
    """If exists, it returns the alternative art of a leader
    """
    constructed_deck_leaders_with_aa = ["ST13-001", "ST13-002", "ST13-002"]
    leader_data: Leader = lid2ldata(leader_id)
    has_aa = leader_id in constructed_deck_leaders_with_aa or not (leader_id[0:2] in ["ST"] or leader_id[0] in ["P"])
    return leader_data.image_aa_url if has_aa else leader_data.image_url

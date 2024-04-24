from pydantic import BaseModel

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import Leader


class LeaderUploadForm(BaseModel):
    avatar_icon_default_text: str | None = None
    image_url_default_text: str | None = None
    image_aa_url_default_text: str | None = None
    release_meta_default_text: MetaFormat | None = None
    bq_leader: Leader | None = None

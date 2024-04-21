from enum import StrEnum

class BQFieldMode(StrEnum):
    NULLABLE="NULLABLE"
    REQUIRED="REQUIRED"
    REPEATED="REPEATED"


class BQFieldType(StrEnum):
    STRING="STRING"
    BOOL="BOOL"
    REPEATED="REPEATED"
    INT64="INT64"
    FLOAT64="FLOAT64"
    TIMESTAMP="TIMESTAMP"
    DATE="DATE"
    TIME="TIME"

class BQTable(StrEnum):
    MATCHES="matches"
    LEADER_ELO="leader_elo"
    LEADER_DATA="leaders"

class BQDataset(StrEnum):
    MATCHES="matches"
    LEADERS="leaders"

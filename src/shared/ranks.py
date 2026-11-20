"""Price-file status, taken from the filename."""

STATUS_RANK = {
    "interim": 1,
    "incomplete": 2,
    "final": 3,
}


def status_rank(status: str) -> int:
    try:
        return STATUS_RANK[status]
    except KeyError as exc:
        raise ValueError(f"unknown price status: {status}") from exc

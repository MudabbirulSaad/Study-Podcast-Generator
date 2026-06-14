class DomainError(Exception):
    """Raised when domain invariants are violated."""


class ActiveJobExistsError(DomainError):
    def __init__(self, job_id: str) -> None:
        super().__init__("This project already has an active generation job.")
        self.job_id = job_id

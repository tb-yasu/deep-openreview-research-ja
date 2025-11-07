from app.domain.enums import BaseEnum


class Priority(BaseEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @classmethod
    def up_to(cls, target: "Priority") -> list["Priority"]:
        priorities = [cls.HIGH, cls.MEDIUM, cls.LOW]
        return priorities[: priorities.index(target) + 1]

from abc import abstractmethod, ABC
from typing import TypeVar, Generic

E = TypeVar("E")
T = TypeVar("T")


class AbstractETL(ABC, Generic[E, T]):
    """Abstract base class to define Extract, Transform, Load (ETL) functions"""

    @abstractmethod
    def extract(self) -> E:
        raise NotImplementedError

    @abstractmethod
    def validate(self, extracted_data: E) -> bool:
        raise NotImplementedError

    @abstractmethod
    def transform(self, extracted_data: E) -> T:
        raise NotImplementedError

    @abstractmethod
    def load(self, transformed_data: T) -> None:
        raise NotImplementedError


class AbstractETLJob(AbstractETL[E, T], ABC):
    """Abstract base class to handle ETL jobs"""

    def run(self) -> None:
        """Executes all components of an ETL data pipeline."""
        extracted_data = self.extract()
        self.validate(extracted_data)
        transformed_data = self.transform(extracted_data)
        self.load(transformed_data)

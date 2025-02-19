from sqlalchemy import (
    create_engine,
    ForeignKey,
    Column,
    String,
    Integer,
    DateTime,
    Boolean,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func

global base
base = declarative_base()


class Dbstruct:

    class demands(base):
        """
        Represents the 'demands' table.
        """

        __tablename__ = "demands"

        id = Column(
            "key_id", Integer, primary_key=True, autoincrement=True
        )  # Primary key
        research_id = Column(
            Integer, ForeignKey("research.id")
        )  # Foreign key to Researches table
        demand = Column("demand", String)  # Demand name
        added_by = Column("added_by", String)  # User who added the demand
        researcher = Column("researcher", String)  # Assigned researcher
        add_time = Column("add_time", DateTime, server_default=func.now())  # Time added
        deadline = Column("deadline", DateTime, nullable=True)  # Optional deadline
        done = Column("done", Boolean, default=False)  # Assigned researcher

        # Relationships
        research = relationship("research", back_populates="demands")
        resources = relationship("resources", back_populates="demand")

    class research(base):
        """
        Represents the 'research' table.
        """

        __tablename__ = "research"

        id = Column("id", Integer, primary_key=True, autoincrement=True)
        name = Column("name", String, nullable=False)

        # Relationships
        demands = relationship("demands", back_populates="research")
        resources = relationship("resources", back_populates="research")

    class resources(base):
        """
        Represents the 'resources' table connected to demands and research.

        Attributes:
            id (int): Primary key.
            resource_name (str): Name or description of the resource.
            resource_link (str): URL or path to the resource.
            research_id (int): Foreign key referencing research.
            demand_id (int): Foreign key referencing demands.
            added_by (str): User who added the resource.
            is_read (bool): Status indicating if the resource has been read.
            read_by (str, optional): User who read the resource.
            added_at (datetime): Timestamp when the resource was added.
        """

        __tablename__ = "resources"

        id = Column(Integer, primary_key=True, autoincrement=True)
        resource_name = Column(String, nullable=False)
        resource_link = Column(String, nullable=False)
        research_id = Column(Integer, ForeignKey("research.id"))
        demand_id = Column(Integer, ForeignKey("demands.key_id"))
        added_by = Column(String, nullable=False)  # User who added the resource
        is_read = Column(Boolean, default=False)  # Read status
        read_by = Column(String, nullable=True)  # User who read the resource
        added_at = Column(DateTime, server_default=func.now())  # Timestamp

        # Relationships
        research = relationship("research", back_populates="resources")
        demand = relationship("demands", back_populates="resources")


class BotDb:
    def __init__(self) -> None:
        engine = create_engine("sqlite:///database.db")
        base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        self.session = Session()

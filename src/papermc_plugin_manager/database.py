from sqlalchemy import create_engine, String, Integer, Text, select, ForeignKey, DateTime,  UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, relationship
from sqlalchemy.types import JSON
from sqlalchemy.ext.mutable import MutableList
from typing import List
from logzero import logger

from .connector_interface import ConnectorInterface, FileInfo, ProjectInfo


class Base(DeclarativeBase):
    pass


class FileTable(Base):
    __tablename__ = 'file'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"))
    version_id: Mapped[str] = mapped_column(String, index=True)
    version_name: Mapped[str] = mapped_column(String)
    version_type: Mapped[str] = mapped_column(String)
    release_date: Mapped[DateTime] = mapped_column(DateTime)
    game_versions: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    url: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    sha1: Mapped[str] = mapped_column(String, unique=True, index=True)

    @classmethod
    def from_file_info(cls, info: FileInfo):
        return FileTable(
            version_id=info.version_id,
            project_id=info.project_id,
            version_name=info.version_name,
            version_type=info.version_type,
            release_date=info.release_date,
            game_versions=info.game_versions,
            sha1=info.sha1,
            url=info.url,
            description=info.description,
        )
    
    def update(self, info: FileInfo):
        self.version_name = info.version_name
        self.version_type = info.version_type
        self.release_date = info.release_date
        self.game_versions = info.game_versions
        self.sha1 = info.sha1
        self.url = info.url
        self.description = info.description

    def to_file_info(self) -> FileInfo:
        return FileInfo(
            project_id=self.project_id,
            version_id=self.version_id,
            version_name=self.version_name,
            version_type=self.version_type,
            release_date=self.release_date,
            game_versions=self.game_versions,
            sha1=self.sha1,
            url=self.url,
            description=self.description or "",
        )


class ProjectTable(Base):
    __tablename__ = 'project'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    author: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    downloads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    @classmethod
    def from_project_info(cls, info: ProjectInfo):
        return ProjectTable(
            source=info.source,
            project_id=info.project_id,
            name=info.name,
            author=info.author,
            description=info.description,
            downloads=info.downloads,
        )
    
    def update(self, info: ProjectInfo):
        self.name = info.name
        self.author = info.author
        self.description = info.description
        self.downloads = info.downloads

    def to_project_info(self, info_list: List[FileTable]) -> ProjectInfo:
        return ProjectInfo(
            source=self.source,
            project_id=self.project_id,
            name=self.name,
            author=self.author,
            description=self.description,
            downloads=self.downloads,
            versions={file.version_id: file.to_file_info() for file in info_list},
        )
    
class InstallationTable(Base):
    __tablename__ = 'installation'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    sha1: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)
    filesize: Mapped[int] = mapped_column(Integer, nullable=False)

class SourceDatabase:

    def __init__(self, db_url: str = "sqlite:///ppm.db"):
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)

    def get_project_table_by_id(self, project_id: str) -> ProjectTable | None:
        with Session(self.engine) as session:
            stmt = select(ProjectTable).where(ProjectTable.project_id == project_id)
            project = session.execute(stmt).scalar_one_or_none()
            return project
        
    def get_project_table_by_name(self, name: str) -> ProjectTable | None:
        with Session(self.engine) as session:
            stmt = select(ProjectTable).where(ProjectTable.name == name)
            project = session.execute(stmt).scalar_one_or_none()
            return project
        
    def get_project_table(self, name) -> ProjectTable | None:
        project = self.get_project_table_by_id(name)
        if project is None:
            project = self.get_project_table_by_name(name)
        return project

    def get_all_files(self, project_id: str) -> list[FileTable]:
        with Session(self.engine) as session:
            stmt = select(FileTable).where(FileTable.project_id == project_id)
            files = session.execute(stmt).scalars().all()
            return files
        
    def get_file_by_sha1(self, sha1: str) -> FileTable | None:
        with Session(self.engine) as session:
            stmt = select(FileTable).where(FileTable.sha1 == sha1)
            file = session.execute(stmt).scalar_one_or_none()
            return file
        
    def get_project_by_file_sha1(self, sha1: str) -> ProjectInfo | None:
        file_table = self.get_file_by_sha1(sha1)
        if file_table is None:
            return None
        project_table = self.get_project_table_by_id(file_table.project_id)
        if project_table is None:
            return None
        files = self.get_all_files(project_table.project_id)
        return project_table.to_project_info(files)

    def get_project_info(self, name: str) -> ProjectInfo | None:
        project_table = self.get_project_table(name)
        if project_table is None:
            return None
        files = self.get_all_files(project_table.project_id)
        project_info = project_table.to_project_info(files)
        with Session(self.engine) as session:
            stmt = (
                select(InstallationTable.sha1)
                .join(FileTable, InstallationTable.sha1 == FileTable.sha1)
                .where(
                    FileTable.project_id == project_table.project_id,      # your subset condition(s)
                ).distinct()
            )
            installation_sha1 = session.scalars(stmt).one_or_none()
            if installation_sha1:
                project_info.current_version = self.get_file_by_sha1(installation_sha1).to_file_info()
        return project_info

    def save_project_info(self, info: ProjectInfo):
        with Session(self.engine) as session:
            project_table = self.get_project_table_by_id(info.project_id)
            if project_table is None:
                project_table = ProjectTable.from_project_info(info)
                session.add(project_table)
                session.commit()
            else:
                project_table.update(info)
                session.commit()
            
            for file_info in info.versions.values():
                stmt = select(FileTable).where(
                    FileTable.project_id == info.project_id,
                    FileTable.version_id == file_info.version_id
                )
                file_table = session.execute(stmt).scalar_one_or_none()
                if file_table is None:
                    file_table = FileTable.from_file_info(file_info)
                    session.add(file_table)
                else:
                    file_table.update(file_info)
            session.commit()

    def save_installation_info(self, filename: str, sha1: str, filesize: int):
        with Session(self.engine) as session:
            stmt = select(InstallationTable).where(InstallationTable.sha1 == sha1)
            installation = session.execute(stmt).scalar_one_or_none()
            if installation is None:
                logger.debug(f"Found new installation: {filename} with SHA1: {sha1}")
                installation = InstallationTable(
                    filename=filename,
                    sha1=sha1,
                    filesize=filesize,
                )
                session.add(installation)
            elif installation.filename != filename:
                logger.debug(f"Updating installation filename from {installation.filename} to {filename}.")
                installation.filename = filename
            session.commit()

    def remove_stale_installations(self, valid_sha1s: List[str]):
        with Session(self.engine) as session:
            stmt = select(InstallationTable).where(InstallationTable.sha1.not_in(valid_sha1s))
            stale_installations = session.execute(stmt).scalars().all()
            for installation in stale_installations:
                logger.debug(f"Removing stale installation: {installation.filename} with SHA1: {installation.sha1}")
                session.delete(installation)
            session.commit()

    def get_all_installations(self) -> List[InstallationTable]:
        with Session(self.engine) as session:
            stmt = select(InstallationTable)
            installations = session.execute(stmt).scalars().all()
            return installations
        
    def get_installation_by_sha1(self, sha1: str) -> InstallationTable | None:
        with Session(self.engine) as session:
            stmt = select(InstallationTable).where(InstallationTable.sha1 == sha1)
            installation = session.execute(stmt).scalar_one_or_none()
            return installation
        
    def is_sha1_known(self, sha1: str) -> bool:
        with Session(self.engine) as session:
            stmt = select(InstallationTable).where(InstallationTable.sha1 == sha1)
            installation = session.execute(stmt).scalar_one_or_none()
            return installation is not None
from datetime import datetime
from logzero import logger
from sqlalchemy import DateTime, Integer, String, Text, create_engine, select, ForeignKey, LargeBinary
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.types import JSON
from typing import Optional

from .connector_interface import FileInfo, ProjectInfo
from .config import Config

class Base(DeclarativeBase):
    pass

class SnapshotInfoTable(Base):
    __tablename__ = 'snapshot_info'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    description: Mapped[str] = mapped_column(Text)
    game_version: Mapped[str] = mapped_column(String, nullable=True)


class SnapshotFileTable(Base):
    __tablename__ = 'snapshot_file'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey('snapshot_info.id'), nullable=False, onupdate="CASCADE")
    filename: Mapped[str] = mapped_column(String, nullable=False)
    blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    


class FileHashTable(Base):
    __tablename__ = 'file_hash'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sha1: Mapped[str] = mapped_column(String, index=True)
    hash_type: Mapped[str] = mapped_column(String, nullable=False)
    hash_digest: Mapped[str] = mapped_column(String, nullable=False, index=True)

    @classmethod
    def from_hashes(cls, hashes: dict[str, str]) -> list["FileHashTable"]:
        hash_tables = []
        for hash_type, hash_digest in hashes.items():
            hash_tables.append(FileHashTable(
                sha1=hashes.get("sha1", ""),
                hash_type=hash_type,
                hash_digest=hash_digest,
            ))
        return hash_tables


class FileTable(Base):
    __tablename__ = 'file'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String, index=True)
    version_id: Mapped[str] = mapped_column(String, index=True)
    version_name: Mapped[str] = mapped_column(String)
    version_type: Mapped[str] = mapped_column(String)
    release_date: Mapped[datetime] = mapped_column(DateTime)
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
        self.project_id = info.project_id
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

    def to_project_info(self, info_list: list[FileTable], hashes: list[dict[str, str]]) -> ProjectInfo:
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
    installation_type: Mapped[str] = mapped_column(String, nullable=False, default="RELEASE")

class SourceDatabase:

    def __init__(self, db_url: str = f"sqlite:///{Config.DB_PATH}"):
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)

    def get_project_table_by_id(self, project_id: str) -> ProjectTable | None:
        with Session(self.engine) as session:
            stmt = select(ProjectTable).where(ProjectTable.project_id == project_id)
            return session.execute(stmt).scalar_one_or_none()

    def get_project_table_by_name(self, name: str) -> ProjectTable | None:
        with Session(self.engine) as session:
            stmt = select(ProjectTable).where(ProjectTable.name == name)
            return session.execute(stmt).scalar_one_or_none()

    def get_project_table(self, name) -> ProjectTable | None:
        project = self.get_project_table_by_id(name)
        if project is None:
            project = self.get_project_table_by_name(name)
        return project

    def get_all_files(self, project_id: str) -> list[FileTable]:
        with Session(self.engine) as session:
            stmt = select(FileTable).where(FileTable.project_id == project_id)
            files = session.execute(stmt).scalars().all()
            return list(files)

    def get_file_by_sha1(self, sha1: str) -> FileTable | None:
        with Session(self.engine) as session:
            stmt = select(FileTable).where(FileTable.sha1 == sha1)
            return session.execute(stmt).scalar_one_or_none()

    def get_project_by_file_sha1(self, sha1: str) -> ProjectInfo | None:
        file_table = self.get_file_by_sha1(sha1)
        if file_table is None:
            return None
        project_table = self.get_project_table_by_id(file_table.project_id)
        if project_table is None:
            return None
        return self.get_project_info(project_table.project_id)

    def get_hashes_by_file_sha1(self, sha1: str) -> dict[str, str]:
        stmt = select(FileHashTable).where(FileHashTable.sha1 == sha1)
        with Session(self.engine) as session:
            hash_tables = session.execute(stmt).scalars().all()
            if not hash_tables:
                return {}
            return {hash_table.hash_type: hash_table.hash_digest for hash_table in hash_tables}

    def get_project_info(self, name: str) -> ProjectInfo | None:
        project_table = self.get_project_table(name)
        if project_table is None:
            return None
        files = self.get_all_files(project_table.project_id)
        hashes = []
        for file in files:
            file_hashes = self.get_hashes_by_file_sha1(file.sha1)
            hashes.append(file_hashes)

        project_info = project_table.to_project_info(files, hashes)
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
                installed_file = self.get_file_by_sha1(installation_sha1)
                if installed_file:
                    project_info.current_version = installed_file.to_file_info()
                    project_info.current_version.hashes = self.get_hashes_by_file_sha1(installation_sha1)
                else:
                    logger.error(f"Installation with SHA1 {installation_sha1} not found in database.")
                installation = self.get_installation_by_sha1(installation_sha1)
                if installation:
                    project_info.installation_type = installation.installation_type
        return project_info
    
    def get_installed_project_sha1(self, project_name: str) -> str | None:
        project_table = self.get_project_table(project_name)
        if project_table is None:
            return None
        with Session(self.engine) as session:
            stmt = (
                select(InstallationTable.sha1)
                .join(FileTable, InstallationTable.sha1 == FileTable.sha1)
                .where(
                    FileTable.project_id == project_table.project_id,
                ).distinct()
            )
            return session.scalars(stmt).one_or_none()

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
                    FileTable.sha1 == file_info.sha1
                )
                file_table = session.execute(stmt).scalar_one_or_none()
                if file_table is None:
                    file_table = FileTable.from_file_info(file_info)
                    session.add(file_table)
                else:
                    file_table.update(file_info)

                hash_tables = FileHashTable.from_hashes(file_info.hashes)

                for hash_table in hash_tables:
                    stmt = select(FileHashTable).where(
                        FileHashTable.sha1 == hash_table.sha1,
                        FileHashTable.hash_type == hash_table.hash_type,
                    )
                    existing_hash = session.execute(stmt).scalar_one_or_none()
                    if existing_hash is None:
                        session.add(hash_table)
            logger.debug(f"Saved project info for '{info.name}' into database.")
            session.commit()

    def save_installation_info(self, filename: str, sha1: str, filesize: int, installation_type: str = "RELEASE"):
        with Session(self.engine) as session:
            stmt = select(InstallationTable).where(InstallationTable.sha1 == sha1)
            installation = session.execute(stmt).scalar_one_or_none()
            if installation is None:
                logger.debug(f"Found new installation: {filename} with SHA1: {sha1}")
                installation = InstallationTable(
                    filename=filename,
                    sha1=sha1,
                    filesize=filesize,
                    installation_type=installation_type,
                )
                session.add(installation)
            elif installation.filename != filename:
                logger.debug(f"Updating installation filename from {installation.filename} to {filename}.")
                installation.filename = filename
            session.commit()

    def remove_installation(self, filename: str):
        with Session(self.engine) as session:
            stmt = select(InstallationTable).where(InstallationTable.filename == filename)
            installation = session.execute(stmt).scalar_one_or_none()
            if installation:
                logger.debug(f"Removing installation: {installation.filename} with SHA1: {installation.sha1}")
                session.delete(installation)
                session.commit()

    def remove_stale_installations(self, valid_sha1s: list[str]):
        with Session(self.engine) as session:
            stmt = select(InstallationTable).where(InstallationTable.sha1.not_in(valid_sha1s))
            stale_installations = session.execute(stmt).scalars().all()
            for installation in stale_installations:
                logger.debug(f"Removing stale installation: {installation.filename} with SHA1: {installation.sha1}")
                session.delete(installation)
            session.commit()

    def get_all_installations(self) -> list[InstallationTable]:
        with Session(self.engine) as session:
            stmt = select(InstallationTable)
            installations = session.execute(stmt).scalars().all()
            return list(installations)

    def get_installation_by_sha1(self, sha1: str) -> InstallationTable | None:
        with Session(self.engine) as session:
            stmt = select(InstallationTable).where(InstallationTable.sha1 == sha1)
            return session.execute(stmt).scalar_one_or_none()

    def is_sha1_known(self, sha1: str) -> bool:
        with Session(self.engine) as session:
            stmt = select(InstallationTable).where(InstallationTable.sha1 == sha1)
            installation = session.execute(stmt).scalar_one_or_none()
            return installation is not None
        
    def update_installation_type(self, sha1: str, installation_type: str):
        with Session(self.engine) as session:
            stmt = select(InstallationTable).where(InstallationTable.sha1 == sha1)
            installation = session.execute(stmt).scalar_one_or_none()
            if installation:
                installation.installation_type = installation_type
                session.commit()

    def create_snapshot(self, name: str, description: str = "", game_version: Optional[str] = None) -> SnapshotInfoTable:
        with Session(self.engine) as session:
            snapshot = SnapshotInfoTable(
                name=name,
                description=description,
                game_version=game_version,
            )
            session.add(snapshot)
            session.commit()
            logger.debug(f"Created snapshot '{name}' with ID {snapshot.id}.")
            return snapshot
        
    def add_file_to_snapshot(self, snapshot_id: int, filename: str, blob: bytes) -> SnapshotFileTable:
        with Session(self.engine) as session:
            snapshot_file = SnapshotFileTable(
                snapshot_id=snapshot_id,
                filename=filename,
                blob=blob,
            )
            session.add(snapshot_file)
            session.commit()
            logger.debug(f"Added file '{filename}' to snapshot ID {snapshot_id}.")
            return snapshot_file

    def get_all_snapshots(self) -> list[SnapshotInfoTable]:
        with Session(self.engine) as session:
            stmt = select(SnapshotInfoTable)
            snapshots = session.execute(stmt).scalars().all()
            return list(snapshots)
        
    def get_snapshot_files(self, snapshot_id: int) -> list[SnapshotFileTable]:
        with Session(self.engine) as session:
            stmt = select(SnapshotFileTable).where(SnapshotFileTable.snapshot_id == snapshot_id)
            files = session.execute(stmt).scalars().all()
            return list(files)
        
    def get_snapshot_by_name(self, name: str) -> SnapshotInfoTable | None:
        with Session(self.engine) as session:
            stmt = select(SnapshotInfoTable).where(SnapshotInfoTable.name == name)
            return session.execute(stmt).scalar_one_or_none()
        
    def get_snapshot_names(self) -> list[str]:
        with Session(self.engine) as session:
            stmt = select(SnapshotInfoTable.name)
            names = session.execute(stmt).scalars().all()
            return list(names)
        
    def delete_snapshot(self, snapshot_id: int):
        with Session(self.engine) as session:
            snapshot = session.get(SnapshotInfoTable, snapshot_id)
            if snapshot:
                logger.debug(f"Deleting snapshot '{snapshot.name}' with ID {snapshot.id}.")
                session.delete(snapshot)
            files = self.get_snapshot_files(snapshot_id)
            for file in files:
                logger.debug(f"Deleting snapshot file '{file.filename}' from snapshot ID {snapshot_id}.")
                session.delete(file)
            session.commit()
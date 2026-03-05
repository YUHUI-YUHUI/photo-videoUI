"""Project management models for PAVUI"""

import json
import shutil
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, PrivateAttr

from .script import Script


class ProjectStatus(str, Enum):
    """Project status"""
    DRAFT = "draft"
    SCRIPT_GENERATING = "script_generating"
    SCRIPT_READY = "script_ready"
    IMAGES_GENERATING = "images_generating"  # Phase 2
    IMAGES_READY = "images_ready"            # Phase 2
    VIDEO_GENERATING = "video_generating"    # Phase 3
    COMPLETED = "completed"                  # Phase 3


class ProjectSummary(BaseModel):
    """Project summary for listing"""
    id: str
    name: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    thumbnail: str | None = None  # Path to thumbnail image


class Project(BaseModel):
    """Full project data"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    status: ProjectStatus = ProjectStatus.DRAFT
    script: Script | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Runtime fields (not persisted)
    _path: Path | None = PrivateAttr(default=None)

    @property
    def path(self) -> Path | None:
        """Get project directory path"""
        return self._path

    @path.setter
    def path(self, value: Path) -> None:
        """Set project directory path"""
        self._path = value

    def get_summary(self) -> ProjectSummary:
        """Get project summary"""
        thumbnail = None
        if self._path:
            thumb_path = self._path / "thumbnail.png"
            if thumb_path.exists():
                thumbnail = str(thumb_path)

        return ProjectSummary(
            id=self.id,
            name=self.name,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
            thumbnail=thumbnail,
        )

    def touch(self) -> None:
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now()

    def save(self, projects_dir: Path) -> None:
        """Save project to disk"""
        project_dir = projects_dir / self.id
        project_dir.mkdir(parents=True, exist_ok=True)
        self._path = project_dir

        # Save project metadata
        meta_path = project_dir / "project.json"
        meta_data = {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)

        # Save script if exists
        if self.script:
            script_path = project_dir / "script.json"
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(self.script.to_json())

        # Create subdirectories for future use
        (project_dir / "images" / "characters").mkdir(parents=True, exist_ok=True)
        (project_dir / "images" / "locations").mkdir(parents=True, exist_ok=True)
        (project_dir / "images" / "scenes").mkdir(parents=True, exist_ok=True)
        (project_dir / "audio").mkdir(parents=True, exist_ok=True)
        (project_dir / "output").mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls, project_dir: Path) -> "Project":
        """Load project from disk"""
        meta_path = project_dir / "project.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Project metadata not found: {meta_path}")

        with open(meta_path, "r", encoding="utf-8") as f:
            meta_data = json.load(f)

        # Load script if exists
        script = None
        script_path = project_dir / "script.json"
        if script_path.exists():
            with open(script_path, "r", encoding="utf-8") as f:
                script = Script.from_json(f.read())

        project = cls(
            id=meta_data["id"],
            name=meta_data["name"],
            status=ProjectStatus(meta_data["status"]),
            script=script,
            created_at=datetime.fromisoformat(meta_data["created_at"]),
            updated_at=datetime.fromisoformat(meta_data["updated_at"]),
        )
        project._path = project_dir

        return project

    def delete(self) -> None:
        """Delete project from disk"""
        if self._path and self._path.exists():
            shutil.rmtree(self._path)

    def export_script(self, output_path: Path, format: str = "json") -> Path:
        """Export script to file"""
        if not self.script:
            raise ValueError("No script to export")

        if format == "json":
            output_file = output_path / f"{self.name}_script.json"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(self.script.to_json())
            return output_file
        else:
            raise ValueError(f"Unsupported format: {format}")

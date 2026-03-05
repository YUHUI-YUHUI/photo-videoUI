"""Project management service"""

from pathlib import Path

from ..models import Project, ProjectStatus, ProjectSummary, Script
from ..utils.config import Config


class ProjectService:
    """Service for managing projects"""

    def __init__(self, projects_dir: Path | None = None):
        config = Config()
        self.projects_dir = projects_dir or config.projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> list[ProjectSummary]:
        """List all projects"""
        projects = []

        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                meta_path = project_dir / "project.json"
                if meta_path.exists():
                    try:
                        project = Project.load(project_dir)
                        projects.append(project.get_summary())
                    except Exception:
                        # Skip invalid projects
                        pass

        # Sort by updated_at, newest first
        projects.sort(key=lambda p: p.updated_at, reverse=True)
        return projects

    def create_project(self, name: str) -> Project:
        """Create a new project"""
        project = Project(name=name)
        project.save(self.projects_dir)
        return project

    def load_project(self, project_id: str) -> Project:
        """Load a project by ID"""
        project_dir = self.projects_dir / project_id
        if not project_dir.exists():
            raise FileNotFoundError(f"Project not found: {project_id}")
        return Project.load(project_dir)

    def save_project(self, project: Project) -> None:
        """Save a project"""
        project.touch()
        project.save(self.projects_dir)

    def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        try:
            project = self.load_project(project_id)
            project.delete()
            return True
        except FileNotFoundError:
            return False

    def update_script(self, project_id: str, script: Script) -> Project:
        """Update project's script"""
        project = self.load_project(project_id)
        project.script = script
        project.status = ProjectStatus.SCRIPT_READY
        self.save_project(project)
        return project

    def set_status(self, project_id: str, status: ProjectStatus) -> Project:
        """Update project status"""
        project = self.load_project(project_id)
        project.status = status
        self.save_project(project)
        return project

    def export_script(self, project_id: str, output_dir: Path, format: str = "json") -> Path:
        """Export project script"""
        project = self.load_project(project_id)
        return project.export_script(output_dir, format)

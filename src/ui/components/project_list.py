"""Project list component"""

import gradio as gr

from ...models import ProjectSummary, ProjectStatus
from ...services import ProjectService
from ...utils.i18n import t


def create_project_list(project_service: ProjectService) -> dict:
    """Create project list component"""

    with gr.Column():
        gr.Markdown(f"### {t('project.list_title')}")

        # Project list
        projects_html = gr.HTML(
            _render_projects(project_service.list_projects()),
            elem_id="projects-list",
        )

        # New project button
        with gr.Row():
            new_project_name = gr.Textbox(
                placeholder=t("project.name_placeholder"),
                show_label=False,
                scale=3,
            )
            create_btn = gr.Button(
                t("project.create"),
                variant="primary",
                scale=1,
            )

        # Selected project state
        selected_project_id = gr.State(None)

    def refresh_list():
        projects = project_service.list_projects()
        return _render_projects(projects)

    def create_project(name):
        if not name.strip():
            return gr.update(), None

        project = project_service.create_project(name.strip())
        return _render_projects(project_service.list_projects()), project.id

    create_btn.click(
        fn=create_project,
        inputs=[new_project_name],
        outputs=[projects_html, selected_project_id],
    )

    return {
        "projects_html": projects_html,
        "selected_project_id": selected_project_id,
        "refresh": refresh_list,
    }


def _render_projects(projects: list[ProjectSummary]) -> str:
    """Render projects list as HTML"""
    if not projects:
        return f"""
        <div class="empty-state">
            <div class="empty-state-icon">📁</div>
            <p>{t('project.no_projects')}</p>
        </div>
        """

    html = '<div class="scrollable-list">'
    for project in projects:
        status_class = {
            ProjectStatus.DRAFT: "status-draft",
            ProjectStatus.SCRIPT_READY: "status-ready",
            ProjectStatus.SCRIPT_GENERATING: "status-generating",
        }.get(project.status, "status-draft")

        status_text = {
            ProjectStatus.DRAFT: t("project.status_draft"),
            ProjectStatus.SCRIPT_READY: t("project.status_script_ready"),
            ProjectStatus.IMAGES_READY: t("project.status_images_ready"),
            ProjectStatus.COMPLETED: t("project.status_completed"),
        }.get(project.status, project.status.value)

        html += f"""
        <div class="card" onclick="selectProject('{project.id}')" style="cursor: pointer;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div class="card-title">📁 {project.name}</div>
                <span class="status-badge {status_class}">{status_text}</span>
            </div>
            <div class="card-subtitle">
                {t('project.updated_at')}: {project.updated_at.strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>
        """
    html += "</div>"
    return html

"""Theme configuration for PAVUI"""

import gradio as gr


def get_theme(mode: str = "dark") -> gr.Theme:
    """Get Gradio theme"""
    if mode == "dark":
        return gr.themes.Soft(
            primary_hue=gr.themes.colors.blue,
            secondary_hue=gr.themes.colors.purple,
            neutral_hue=gr.themes.colors.slate,
        ).set(
            body_background_fill="*neutral_950",
            body_background_fill_dark="*neutral_950",
            block_background_fill="*neutral_900",
            block_background_fill_dark="*neutral_900",
            block_border_color="*neutral_700",
            block_border_color_dark="*neutral_700",
            block_label_background_fill="*neutral_800",
            block_label_background_fill_dark="*neutral_800",
            input_background_fill="*neutral_800",
            input_background_fill_dark="*neutral_800",
            button_primary_background_fill="*primary_600",
            button_primary_background_fill_dark="*primary_600",
            button_primary_background_fill_hover="*primary_500",
            button_primary_background_fill_hover_dark="*primary_500",
        )
    else:
        return gr.themes.Soft(
            primary_hue=gr.themes.colors.blue,
            secondary_hue=gr.themes.colors.purple,
            neutral_hue=gr.themes.colors.gray,
        )


CUSTOM_CSS = """
/* PAVUI Custom Styles */

/* Header */
.pavui-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d1b4e 100%);
    padding: 1rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 1rem;
}

.pavui-header h1 {
    color: white;
    margin: 0;
    font-size: 1.5rem;
}

.pavui-header p {
    color: rgba(255, 255, 255, 0.7);
    margin: 0.25rem 0 0 0;
    font-size: 0.9rem;
}

/* Card styles */
.card {
    border: 1px solid var(--neutral-700);
    border-radius: 8px;
    padding: 1rem;
    background: var(--neutral-800);
    margin-bottom: 0.5rem;
    transition: all 0.2s ease;
}

.card:hover {
    border-color: var(--primary-500);
}

.card-title {
    font-weight: 600;
    margin-bottom: 0.5rem;
}

.card-subtitle {
    color: var(--neutral-400);
    font-size: 0.85rem;
}

/* Scene card */
.scene-card {
    border: 1px solid var(--neutral-700);
    border-radius: 8px;
    padding: 1rem;
    background: var(--neutral-850);
    margin-bottom: 0.75rem;
}

.scene-card .scene-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.scene-card .scene-number {
    background: var(--primary-600);
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 600;
}

.scene-card .scene-meta {
    color: var(--neutral-400);
    font-size: 0.8rem;
}

/* Character/Location chips */
.chip {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    background: var(--neutral-700);
    border-radius: 16px;
    font-size: 0.85rem;
    margin: 0.25rem;
    cursor: pointer;
    transition: all 0.2s ease;
}

.chip:hover {
    background: var(--primary-600);
}

.chip.selected {
    background: var(--primary-600);
}

/* Empty state */
.empty-state {
    text-align: center;
    padding: 2rem;
    color: var(--neutral-400);
}

.empty-state-icon {
    font-size: 2rem;
    margin-bottom: 0.5rem;
}

/* Progress */
.progress-container {
    padding: 1rem;
    background: var(--neutral-800);
    border-radius: 8px;
}

.progress-step {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0;
}

.progress-step.active {
    color: var(--primary-400);
}

.progress-step.done {
    color: var(--green-500);
}

/* Buttons */
.btn-icon {
    padding: 0.5rem;
    min-width: auto;
}

/* Section titles */
.section-title {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
    color: var(--neutral-200);
}

/* Form improvements */
.compact-form .gr-form {
    gap: 0.5rem;
}

/* Modal-like appearance for editors */
.editor-panel {
    background: var(--neutral-900);
    border: 1px solid var(--neutral-700);
    border-radius: 12px;
    padding: 1.5rem;
}

/* Language switcher */
.lang-switch {
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.85rem;
}

.lang-switch:hover {
    background: var(--neutral-700);
}

/* Scrollable list */
.scrollable-list {
    max-height: 400px;
    overflow-y: auto;
}

/* Animation */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}

.fade-in {
    animation: fadeIn 0.3s ease;
}

/* Status badges */
.status-badge {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
}

.status-draft { background: var(--neutral-600); }
.status-ready { background: var(--green-600); }
.status-generating { background: var(--yellow-600); }
"""

from fastapi import Request
from starlette_wtf import StarletteForm
from app import templates, schemas
from app.utils.enums import FeedbackType
from typing import Optional, List
from collections import defaultdict


def set_feedback(
    request: Request,
    feedback_type: FeedbackType,
    feedback_message: str,
):
    request.state.feedback_type = feedback_type.value
    request.state.feedback_message = feedback_message


def get_default_context(request: Request):
    return {
        "request": request,
        "header_links": getattr(request.state, "header_links", None),
        "feedback_type": getattr(request.state, "feedback_type", None),
        "feedback_message": getattr(request.state, "feedback_message", None),
    }


def render_template(
    template: str, request: Request, context_extra: Optional[dict] = None
):
    context = get_default_context(request)

    if context_extra:
        context.update(context_extra)

    return templates.TemplateResponse(template, context)


def render_form_template(template: str, request: Request, form: StarletteForm):
    return render_template(template, request, {"form": form})


def group_categories_by_section(categorie_list: List[schemas.CategoryData]):
    grouped_data = defaultdict(list)
    for item in categorie_list:
        grouped_data[item.section.label].append((item.id, item.label))
    return grouped_data

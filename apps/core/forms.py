"""Tiny helper so templates stay clean: Tailwind classes are applied to widgets in Python."""

from django.forms.widgets import CheckboxInput

CONTROL_CLASSES = (
    "block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm "
    "focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
)

CHECKBOX_CLASSES = "rounded-md text-indigo-600 focus:ring-indigo-500"


def style_fields(form):
    for field in form.fields.values():
        if isinstance(field.widget, CheckboxInput):
            field.widget.attrs.setdefault("class", CHECKBOX_CLASSES)
        else:
            field.widget.attrs.setdefault("class", CONTROL_CLASSES)
    return form

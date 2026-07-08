from django import forms


class StyledFormMixin:
    """Injects the project's Tailwind field classes into every widget so
    individual forms don't need to repeat them field-by-field."""

    checkbox_class = "h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 dark:border-gray-600"
    input_class = "field-input"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput,)):
                existing = widget.attrs.get("class", "")
                widget.attrs["class"] = f"{existing} {self.checkbox_class}".strip()
            elif not isinstance(widget, forms.CheckboxSelectMultiple):
                existing = widget.attrs.get("class", "")
                widget.attrs["class"] = f"{existing} {self.input_class}".strip()

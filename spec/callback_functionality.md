# Callback Functionality in Stand

This document describes all the ways callback functionality is used in the stand framework.

## 1. Widget Value Change Callbacks

All data widgets support a `callback` parameter that gets called when the widget's value changes (in [stand/widgets/simple.py](../stand/widgets/simple.py)):

```python
callback: Optional[Callable] = None

def store_widget_value_for_persist(self):
    self.value = st.session_state[self._widget_key]
    if hasattr(self, '_store'):
        self._store.update_set(self.value)
    if self.callback is not None: 
        self.callback(self)
```

**Usage:** Execute custom logic when a widget changes (e.g., auto-navigate to next document, sync two widgets)

## 2. Navigation Callbacks

Document navigation functions accept `on_change_callback` to execute when changing documents (from [stand/doc_navigation.py](../stand/doc_navigation.py)):

```python
def change_document(on_change_callback: Optional[Callable] = None, ...):
    # ... timing logic ...
    if on_change_callback is not None:
        on_change_callback()
```

**Usage:** Auto-save, cleanup, or other actions when navigating between documents

## 3. Widget Synchronization Callbacks

Keep two widgets in sync by updating each other (from [apps/annotate_documents/pathology/breast_part_fdx.py](../apps/annotate_documents/pathology/breast_part_fdx.py)):

```python
def button_callback_set_dropdown(widget):
    widget._parent_widget.widgets['label_dropdown'].value = widget.value

def dropdown_callback_set_button(widget):
    widget._parent_widget.widgets['label'].value = widget.value
```

**Usage:** Keep multiple representations of the same data in sync

## 4. Toggle/Conditional Display Callbacks

Control widget visibility with toggle callbacks (from [apps/annotate_documents/pathology/ihc.py](../apps/annotate_documents/pathology/ihc.py)):

```python
def callback_toggle_spans(self):
    spans_widget = self.get_parent_widget().widgets['relevant_spans']
    spans_widget.hide = not spans_widget.hide
```

**Usage:** Show/hide widgets conditionally

## 5. Dynamic Content Getters

Compute content dynamically at render time:

### a. DynamicTextElement

From [stand/widgets/dynamic_widgets.py](../stand/widgets/dynamic_widgets.py):

```python
text_getter: Callable[[], str]

def render_widget(self):
    text = self.text_getter(self)
    self.text_widget.render_widget(text=text)
```

**Usage:** Display text that updates based on other widget values

### b. CheckboxPerElement

From [stand/widgets/dynamic_widgets.py](../stand/widgets/dynamic_widgets.py):

```python
option_getter: Callable[[BaseWidget], List[str]]

def render_widget(self):
    current_options = self.option_getter(self)
    # ... render checkboxes for each option ...
```

**Usage:** Dynamically generate checkboxes based on another field's value

## 6. Auto-Navigation Callbacks

Move to next document automatically when completing an annotation (from [apps/annotate_documents/example_tasks/doc_label_few_categories.py](../apps/annotate_documents/example_tasks/doc_label_few_categories.py)):

```python
def move_to_next_doc_callback(self):
    on_click_next_doc_button()
```

**Usage:** Streamline annotation workflow by auto-advancing

## Summary

Callbacks in stand serve these purposes:

- **React to changes** - Widget value updates
- **Coordinate widgets** - Synchronization between multiple widgets
- **Control visibility** - Conditional display of widgets
- **Compute dynamic content** - Text/options getters
- **Workflow automation** - Auto-navigation between documents
- **Side effects** - Saving, logging, cleanup operations

from pydantic import BaseModel
from typing import Optional, List

from stand.base import Document
from stand.widgets.base import BaseWidget
from stand.widgets.simple import SegmentedControlWidget
from stand.widgets.containers import PDMConnnectedWidgets, WidgetSpacing
# from stand.doc_navigation import on_click_next_doc_button


# It is important to name this class Schema so app.py knows to import it.
# Note Schema() should run without error i.e. all arguments should have defaults provided; these defaults control the defaults for the widgets.
class Schema(BaseModel):
    primary_label: Optional[str] = None
    other_labels: Optional[str | List[str]] = None


# def move_to_next_doc_callback(self):
#     on_click_next_doc_button()


# It is important to name this function init_and_connect_widgets() so app.py knows to import it.
def init_and_connect_widgets(schema: Schema, document: Document) -> BaseWidget:
    """
    This function initializes the annotation widget for a single document.

    Parameters
    ----------
    schema:
        An instantiated schema object that stores the annotations for this document.
        If the user uploads an existing set of annotations for this document in their json file then this object is created by Schema.parse_obj(user_provided_data).
        Otherwise this is set to a fresh instantiation of Schema(); as a consequence it is important for Schema() to be able to initialized with no arguments.
        The provided schema argument will set the initial values of the widgets.

    document:
        The document object for this document. Some widgets (e.g. span annotations) need access to document information like the text.

    Output
    ------
    widget_this_document:
        The widget that controls the annotations for this document and is connected to the input schema data store.
    """
    # options = ['neoplastic_malignant'
    #             'no_significant_path_abnormality',
    #            'dysplastic',
    #            'proliferative_non_neoplastic',
    #            'inflammatory_or_other_non_proliferative',
    #            'other',
    #            ]
    options = ['No significant pathologic abnormality',
               'Inflammatory or other non-proliferative changes',
               'Proliferative non-neoplastic changes',
               'Dysplastic changes',
               'Neoplastic malignant changes',
               'Other',
               # 'Metaplasia'
               ]

    primary_label_widget = SegmentedControlWidget(
        label='Primary label for this diagnosis',
        options=options,
        selection_mode='single',
        # label_visibility='collapsed',
        )

    other_label_widget = SegmentedControlWidget(
        label='Other labels for this diagnosis',
        options=options,
        selection_mode='multi',
        # label_visibility='collapsed',
        )

    return PDMConnnectedWidgets(widgets={'primary_label': primary_label_widget,
                                         'other_labels': other_label_widget
                                         },
                                widget_spacing=WidgetSpacing(n_breaks=2),
                                value=schema,
                                label="Diagnosis category"
                                )

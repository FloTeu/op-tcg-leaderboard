import os
from enum import StrEnum
from typing import Any

import streamlit.components.v1 as components

from pathlib import Path
from op_tcg.backend.utils.utils import booleanize

class NivoChartType(StrEnum):
    STREAM = "ResponsiveStream"
    BAR = "ResponsiveBar"
    LINE = "ResponsiveLine"
    HEAT_MAP = "ResponsiveHeatMap"
    RADAR = "ResponsiveRadar"
    TIME_RANGE = "ResponsiveTimeRange"


# Create a _RELEASE constant. We'll set this to False while we're developing
# the component, and True when we're ready to package and distribute it.
# (This is, of course, optional - there are innumerable ways to manage your
# release process.)
_DEBUG = booleanize(os.environ.get("DEBUG", ""))

# Declare a Streamlit component. `declare_component` returns a function
# that is used to create instances of the component. We're naming this
# function "_component_func", with an underscore prefix, because we don't want
# to expose it directly to users. Instead, we will create a custom wrapper
# function, below, that will serve as our component's public API.

# It's worth noting that this call to `declare_component` is the
# *only thing* you need to do to create the binding between Streamlit and
# your component frontend. Everything else we do in this file is simply a
# best practice.

if _DEBUG:
    _component_func = components.declare_component(
        # We give the component a simple, descriptive name ("my_component"
        # does not fit this bill, so please choose something better for your
        # own component :)
        "nivo_charts",
        # Pass `url` here to tell Streamlit that the component will be served
        # by the local dev server that you run via `npm run start`.
        # (This is useful while your component is in development.)
        url="http://localhost:3002",
    )
else:
    # When we're distributing a production version of the component, we'll
    # replace the `url` param with `path`, and point it to the component's
    # build directory:
    root_dir = Path(os.path.abspath(__file__)).parent.parent.parent.parent
    build_dir = root_dir / "components/nivo_charts/nivo_charts/frontend/build"
    _component_func = components.declare_component("nivo_charts", path=str(build_dir))


# Create a wrapper function for the component. This is an optional
# best practice - we could simply expose the component function returned by
# `declare_component` and call it done. The wrapper allows us to customize
# our component's API: we can pre-process its input args, post-process its
# output value, and add a docstring for users.
def nivo_chart(data: Any,
               chart_type: NivoChartType,
               layout: dict,
               layout_callables: list[str] | None = None,
               styles: dict | None = None,
               custom_html: str | None = None,
               key=None):
    """Create a new instance of "nivo_charts".

    Parameters
    ----------
    data: Any
        The data to render a ivo chart. Format depends on the chart_type
    chart_type: NivoChartType
        String/Enum of nivo chart class name which should be rendered
    layout: dict
        Layout configurations, which can be used to customize the chart
    layout_callables: list[str]
        Optional list of paths inside of layout which should be transformed to callables inside of js code.
        A callable can be either a lookup dict or a string which containing valid js code
        E.g. "axisLeft.format" with layout = {"axisLeft": {"format": "function(x) { return (x * 2); }"}}
    styles: dict
        css stylings for outer div container of nivo chart
    custom_html: str
        Optional custom html string which can be used to extend the chart. E.g. for a chart title
    key: str or None
        An optional key that uniquely identifies this component. If this is
        None, and the component's arguments are changed, the component will
        be re-mounted in the Streamlit frontend and lose its current state.

    Returns
    -------
    int
        The number of times the component's "Click Me" button has been clicked.
        (This is the value passed to `Streamlit.setComponentValue` on the
        frontend.)

    """
    layout_callables = layout_callables or []
    styles = styles or {"height": "360px"}
    # Call through to our private component function. Arguments we pass here
    # will be sent to the frontend, where they'll be available in an "args"
    # dictionary.
    #
    # "default" is a special argument that specifies the initial return
    # value of the component before the user has interacted with it.
    component_value = _component_func(data=data,
                                      chartClassName=chart_type,
                                      layout=layout,
                                      layoutCallables=layout_callables,
                                      styles=styles,
                                      customHtml=custom_html,
                                      key=key)

    # We could modify the value returned from the component if we wanted.
    # There's no need to do this in our simple example - but it's an option.
    return component_value

import {
  Streamlit,
  StreamlitComponentBase,
  withStreamlitConnection,
} from "streamlit-component-lib"
import React, { ReactNode } from "react"
import { ResponsiveStream } from '@nivo/stream';
import { ResponsiveBar } from '@nivo/bar';
import { ResponsiveRadar } from '@nivo/radar'
import { ResponsiveLine } from '@nivo/line'
import { ResponsiveHeatMap } from '@nivo/heatmap'
import DOMPurify from 'dompurify';

// Define a type for the chart components
type NivoChartComponents = {
  ResponsiveStream: typeof ResponsiveStream;
  ResponsiveBar: typeof ResponsiveBar;
  ResponsiveRadar: typeof ResponsiveRadar;
  ResponsiveLine: typeof ResponsiveLine;
  ResponsiveHeatMap: typeof ResponsiveHeatMap;
  // Add more components as needed
};

// Assign components to a typed object
const NivoCharts: NivoChartComponents = {
  ResponsiveStream,
  ResponsiveBar,
  ResponsiveRadar,
  ResponsiveLine,
  ResponsiveHeatMap,
};

interface State {
  numClicks: number
  isFocused: boolean
}
interface StringMap {
    [key: string]: string;
}

function move_position_of_on_hover_legend(translateX: Number | undefined, translateY: Number | undefined){
    /** Applies translateX and translateY to (hovered) legend in nivo chart
    * Assumption: legend is inside of div element directly following a svg(plot)
    */
    // Find all svg elements in the document
    const svgElements = document.querySelectorAll('svg');
    svgElements.forEach(svg => {
        // Check if the next sibling of the svg is a div
        const nextSibling = svg.nextElementSibling;
        if (nextSibling && nextSibling.tagName.toLowerCase() === 'div') {
            // Cast nextSibling to HTMLElement to access the style property
            const divElement = nextSibling as HTMLElement;
            // Change the top and left styling of the div
            if (translateX){
               divElement.style.left = `${translateX}px`;
            }
            if (translateY){
               divElement.style.top = `${translateY}px`;
            }
        }
    });
}

function createCallable(obj: StringMap): (key: string | number) => string | undefined {
    return function(key: string | number): string | undefined {
        return obj[key.toString()];
    };
};

/**
 * This is a React-based component template. The `render()` function is called
 * automatically when your component should be re-rendered.
 */
class NivoChart extends StreamlitComponentBase<State> {
  public render = (): ReactNode => {
    // Streamlit sends us a theme object via props that we can use to ensure
    // that our component has visuals that match the active theme in a
    // streamlit app.
    const { data, chartClassName, layout, layoutCallables, key} = this.props.args
    const styles: React.CSSProperties = this.props.args["styles"];
    // ensure title is of type string and sanitized
    const cleanCustomHtml = (this.props.args["customHtml"] === undefined || this.props.args["customHtml"] === null) ? '' : DOMPurify.sanitize(String(this.props.args["customHtml"]));

    // Transform layout values specified in layoutCallables into callables
    layoutCallables.forEach((path: string) => {
      // For example path could be "axisLeft.format"
      // e.g. keys = ["axisLeft", "format"]
      const keys = path.split('.');
      let current = layout;
      for (let i = 0; i < keys.length - 1; i++) {
        current = current[keys[i]];
        if (!current) return;
      }
      // e.g. current = {"orient": 'left', "tickSize": 5, "format": {1: "OP01"}}
      // e.g. lastKey = "format"
      const lastKey = keys[keys.length - 1];
      if (typeof current[lastKey] === 'object') {
        current[lastKey] = createCallable(current[lastKey]);
      }
      // e.g. current = {"orient": 'left', "tickSize": 5, "format": 'function(x) { return x + (1.0 / 2); }'}
      if (typeof current[lastKey] === 'string') {
        current[lastKey] = eval(`(${current[lastKey]})`);
      }
    });


    // Access the component dynamically
    //const ChartComponent = NivoCharts[chartClassName as keyof NivoChartComponents];
    const ChartComponent = NivoCharts[chartClassName as keyof NivoChartComponents] as React.ComponentType<any>;

    if (!ChartComponent) {
      return <div>Invalid chart class name: {chartClassName}</div>;
    }


    // Safely access translateX and translateY using optional chaining
    const translateX = layout.legends?.[0]?.effects?.[0]?.style?.translateX ?? 0;
    const translateY = layout.legends?.[0]?.effects?.[0]?.style?.translateY ?? 0;

    // Create a new MutationObserver instance
    const observer = new MutationObserver((mutationsList) => {
        for (const mutation of mutationsList) {
            if (mutation.type === 'childList') {
                // Iterate over added nodes
                const addedNodesArray = Array.from(mutation.addedNodes);
                for (const node of addedNodesArray) {
                    if (node.nodeName === 'DIV') {
                        move_position_of_on_hover_legend(translateX, translateY);
                    }
                }
            }
        }
    });


    // Wait for 100 ms before checking the DOM structure
    setTimeout(() => {
        // Select the target element to observe
        const targetNode = document.getElementById('custom-nivo-chart');

        // Configuration for the observer (observe child nodes and subtree)
        const config = { childList: true, subtree: true };

        // Start observing the target node
        if (targetNode){
           observer.observe(targetNode, config);
        }
    }, 100); // n ms delay


    // Display nivo chart
    return (
      <div>
          <div id="custom-nivo-chart" style={styles} key={key} >
              <div dangerouslySetInnerHTML={{ __html: cleanCustomHtml }} />
                  <ChartComponent
                    data={data}
                    {...layout}
                  />
          </div>
      </div>
    )
  }
}

// "withStreamlitConnection" is a wrapper function. It bootstraps the
// connection between your component and the Streamlit app, and handles
// passing arguments from Python -> Component.
//
// You don't need to edit withStreamlitConnection (but you're welcome to!).
export default withStreamlitConnection(NivoChart)

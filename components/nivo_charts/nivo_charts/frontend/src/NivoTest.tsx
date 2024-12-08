import { ResponsiveBar } from '@nivo/bar';
import {
  Streamlit,
  StreamlitComponentBase,
  withStreamlitConnection,
} from "streamlit-component-lib"
import React, { ReactNode } from "react"

const barData = [
  { id: 'A', value: 30 },
  { id: 'B', value: 20 },
  { id: 'C', value: 50 },
];

const legendData = [
  { id: 'A', label: 'Category A' }, // Add 'label' property
  { id: 'B', label: 'Category B' }, // Add 'label' property
  { id: 'C', label: 'Category C' }, // Add 'label' property
];

interface State {
  numClicks: number
  isFocused: boolean
}

class NivoChart extends StreamlitComponentBase<State> {
  public render = (): ReactNode => {
    // Display nivo chart
    return (
  <div style={{ height: 400 }}>
    <ResponsiveBar
      data={barData} // Data for rendering the bars
      keys={['value']}
      indexBy="id"
      margin={{ top: 50, right: 130, bottom: 50, left: 60 }}
      // Customizing axes
      axisBottom={{
        tickSize: 5,
        tickPadding: 5,
        tickRotation: 0,
        legend: 'Categories',
        legendPosition: 'middle',
        legendOffset: 32,
      }}
      axisLeft={{
        tickSize: 5,
        tickPadding: 5,
        tickRotation: 0,
        legend: 'Values',
        legendPosition: 'middle',
        legendOffset: -40,
      }}
      // Custom legends
      legends={[
        {
          data: legendData, // Use the custom legend data
          dataFrom: 'keys', // This should be 'keys' for keys from barData
          anchor: 'bottom',
          direction: 'row',
          justify: false,
          translateY: 50,
          itemsSpacing: 10,
          itemWidth: 100,
          itemHeight: 20,
          itemDirection: 'left-to-right',
          itemOpacity: 0.85,
          symbolSize: 20,
          symbolShape: 'circle',
          // The legend will automatically use the 'id' property for display
          // You can customize the label using a custom render function if needed
          // However, this is not directly supported in Nivo's default legend
        },
      ]}
    />
  </div>
      )
  }
}

// You don't need to edit withStreamlitConnection (but you're welcome to!).
export default withStreamlitConnection(NivoChart)
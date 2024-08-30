import {
  Streamlit,
  StreamlitComponentBase,
  withStreamlitConnection,
} from "streamlit-component-lib"
import React, { ReactNode } from "react"
import { ResponsiveStream } from '@nivo/stream';

interface State {
  numClicks: number
  isFocused: boolean
}


/**
 * This is a React-based component template. The `render()` function is called
 * automatically when your component should be re-rendered.
 */
class NivoChart extends StreamlitComponentBase<State> {
  public state = { numClicks: 0, isFocused: false }

  public render = (): ReactNode => {
    // Arguments that are passed to the plugin in Python are accessible
    // via `this.props.args`. Here, we access the "name" arg.
    const name = this.props.args["name"]

    // Streamlit sends us a theme object via props that we can use to ensure
    // that our component has visuals that match the active theme in a
    // streamlit app.
    const { theme } = this.props
    const style: React.CSSProperties = {}

    // Maintain compatibility with older versions of Streamlit that don't send
    // a theme object.
    if (theme) {
      // Use the theme object to style our button border. Alternatively, the
      // theme style is defined in CSS vars.
      const borderStyling = `1px solid ${
        this.state.isFocused ? theme.primaryColor : "gray"
      }`
      style.border = borderStyling
      style.outline = borderStyling
    }

    const data = [
      {
        "Raoul": 16,
        "Josiane": 129,
        "Marcel": 145,
        "René": 99,
        "Paul": 12,
        "Jacques": 102
      },
      {
        "Raoul": 176,
        "Josiane": 106,
        "Marcel": 106,
        "René": 76,
        "Paul": 27,
        "Jacques": 173
      },
      {
        "Raoul": 107,
        "Josiane": 115,
        "Marcel": 109,
        "René": 191,
        "Paul": 164,
        "Jacques": 80
      },
      {
        "Raoul": 119,
        "Josiane": 150,
        "Marcel": 23,
        "René": 95,
        "Paul": 110,
        "Jacques": 103
      },
      {
        "Raoul": 20,
        "Josiane": 62,
        "Marcel": 173,
        "René": 71,
        "Paul": 135,
        "Jacques": 180
      },
      {
        "Raoul": 138,
        "Josiane": 51,
        "Marcel": 146,
        "René": 138,
        "Paul": 21,
        "Jacques": 52
      }
    ];

    const x_ticks = ["OP01", "OPß2", "OP03", "OP04", "OPß5", "OP06"];
    // Define custom tick values and labels
    const customTicks = [
      { value: 0, label: 'OP01' },
      { value: 1, label: 'OPß2' },
      { value: 2, label: 'OP03' },
      { value: 3, label: 'OP04' },
      { value: 4, label: 'OPß5' },
      { value: 5, label: 'OPß6' },
    ];

    // Show a button and some text.
    // When the button is clicked, we'll increment our "numClicks" state
    // variable, and send its new value back to Streamlit, where it'll
    // be available to the Python program.
    return (
      <div>
        <span>
          Hello, {name}! &nbsp;
          <button
            style={style}
            onClick={this.onClicked}
            disabled={this.props.disabled}
            onFocus={this._onFocus}
            onBlur={this._onBlur}
          >
            Click Me!
          </button>
        </span>
        <div style={{ height: 400 }}>
          <ResponsiveStream
            data={data}
            keys={[
                'Raoul',
                'Josiane',
                'Marcel',
                'René',
                'Paul',
                'Jacques'
            ]}
            margin={{ top: 50, right: 110, bottom: 50, left: 60 }}
            axisTop={null}
            axisRight={null}
            axisBottom={{
                tickSize: 5,
                tickPadding: 5,
                tickRotation: 0,
                legend: '',
                legendOffset: 36,
                truncateTickAt: 0,
                format: value => {
                const tick = customTicks.find(t => t.value === value);
                return tick ? tick.label : value;
                }
              }}
            axisLeft={{
                tickSize: 5,
                tickPadding: 5,
                tickRotation: 0,
                legend: '',
                legendOffset: -40,
                truncateTickAt: 0
            }}
            enableGridX={true}
            enableGridY={false}
            offsetType="silhouette"
            colors={{ scheme: 'nivo' }}
            fillOpacity={0.85}
            borderColor={{ theme: 'background' }}
            defs={[
                {
                    id: 'dots',
                    type: 'patternDots',
                    background: 'inherit',
                    color: '#2c998f',
                    size: 4,
                    padding: 2,
                    stagger: true
                },
                {
                    id: 'squares',
                    type: 'patternSquares',
                    background: 'inherit',
                    color: '#e4c912',
                    size: 6,
                    padding: 2,
                    stagger: true
                }
            ]}
            fill={[
                {
                    match: {
                        id: 'Paul'
                    },
                    id: 'dots'
                },
                {
                    match: {
                        id: 'Marcel'
                    },
                    id: 'squares'
                }
            ]}
            dotSize={8}
            dotColor={{ from: 'color' }}
            dotBorderWidth={2}
            dotBorderColor={{
                from: 'color',
                modifiers: [
                    [
                        'darker',
                        0.7
                    ]
                ]
            }}
            legends={[
                {
                    anchor: 'bottom-right',
                    direction: 'column',
                    translateX: 100,
                    itemWidth: 80,
                    itemHeight: 20,
                    itemTextColor: '#999999',
                    symbolSize: 12,
                    symbolShape: 'circle',
                    effects: [
                        {
                            on: 'hover',
                            style: {
                                itemTextColor: '#000000'
                            }
                        }
                    ]
                }
            ]}
          />
        </div>
      </div>
    )
  }

  /** Click handler for our "Click Me!" button. */
  private onClicked = (): void => {
    // Increment state.numClicks, and pass the new value back to
    // Streamlit via `Streamlit.setComponentValue`.
    this.setState(
      prevState => ({ numClicks: prevState.numClicks + 1 }),
      () => Streamlit.setComponentValue(this.state.numClicks)
    )
  }

  /** Focus handler for our "Click Me!" button. */
  private _onFocus = (): void => {
    this.setState({ isFocused: true })
  }

  /** Blur handler for our "Click Me!" button. */
  private _onBlur = (): void => {
    this.setState({ isFocused: false })
  }
}

// "withStreamlitConnection" is a wrapper function. It bootstraps the
// connection between your component and the Streamlit app, and handles
// passing arguments from Python -> Component.
//
// You don't need to edit withStreamlitConnection (but you're welcome to!).
export default withStreamlitConnection(NivoChart)

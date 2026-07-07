import ReactEChartsCore from "echarts-for-react/lib/core";
import type { EChartsReactProps } from "echarts-for-react";
import { BarChart, LineChart } from "echarts/charts";
import {
  DataZoomInsideComponent,
  DataZoomSliderComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  BarChart,
  LineChart,
  DataZoomInsideComponent,
  DataZoomSliderComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
  CanvasRenderer,
]);

export function AppChart({ opts, replaceMerge, ...props }: EChartsReactProps) {
  return (
    <ReactEChartsCore
      echarts={echarts}
      opts={{ renderer: "canvas", ...opts }}
      replaceMerge={replaceMerge ?? ["series"]}
      {...props}
    />
  );
}

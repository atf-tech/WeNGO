var options = {
  series: [
    {
      name: 'Leads',
      data: [18, 22, 12],
    },
    {
      name: 'Received',
      data: [155, 63, 78],
    },
    {
      name: 'Sent',
      data: [208, 82, 115],
    },
    {
      name: 'Conv %',
      data: [95, 100, 88],
    },
  ],

  chart: {
    type: 'bar',
    height: 420,
    stacked: false,
    toolbar: {
      show: false,
    },
    fontFamily: 'Poppins, sans-serif',
  },

  // New premium colors
  colors: [
    '#F59E0B', // Orange
    '#6366F1', // Indigo
    '#10B981', // Emerald
    '#06B6D4', // Cyan
  ],

  plotOptions: {
    bar: {
      horizontal: false,
      columnWidth: '52%',
      borderRadius: 12,
      borderRadiusApplication: 'end',
      distributed: false,
    },
  },

  stroke: {
    show: false,
  },

  dataLabels: {
    enabled: false,
  },

  fill: {
    type: 'gradient',
    gradient: {
      shade: 'light',
      type: 'vertical',
      shadeIntensity: 0.4,
      gradientToColors: undefined,
      inverseColors: false,
      opacityFrom: 0.95,
      opacityTo: 0.75,
      stops: [0, 100],
    },
  },

  grid: {
    borderColor: '#eef2f7',
    strokeDashArray: 5,
    padding: {
      left: 10,
      right: 10,
    },
  },

  xaxis: {
    categories: ['Madurai', 'Chennai', 'Bangalore'],

    axisBorder: {
      show: false,
    },

    axisTicks: {
      show: false,
    },

    labels: {
      style: {
        fontSize: '15px',
        fontWeight: 500,
        colors: '#6b7280',
      },
    },
  },

  yaxis: {
    min: 0,
    max: 250,
    tickAmount: 5,

    labels: {
      style: {
        fontSize: '13px',
        colors: '#94a3b8',
      },
    },
  },

  legend: {
    position: 'bottom',
    horizontalAlign: 'left',

    fontSize: '14px',
    fontWeight: 500,

    markers: {
      width: 10,
      height: 10,
      radius: 50,
    },

    itemMargin: {
      horizontal: 18,
      vertical: 8,
    },
  },

  tooltip: {
    shared: true,
    intersect: false,

    custom: function ({ dataPointIndex, w }) {
      const city =
        w.globals.categoryLabels[dataPointIndex];

      const leads =
        w.config.series[0].data[dataPointIndex];

      const received =
        w.config.series[1].data[dataPointIndex];

      const sent =
        w.config.series[2].data[dataPointIndex];

      const conv =
        w.config.series[3].data[dataPointIndex];

      return `
        <div style="
          background:#ffffff;
          border-radius:16px;
          box-shadow:0 10px 30px rgba(0,0,0,.12);
          min-width:230px;
          overflow:hidden;
          border:1px solid #f1f5f9;
        ">

          <div style="
            padding:14px 18px;
            background:#f8fafc;
            font-size:17px;
            font-weight:600;
            color:#1e293b;
          ">
            📍 ${city}
          </div>

          <div style="padding:18px">

            ${tooltipRow('#F59E0B', 'Leads', leads)}
            ${tooltipRow('#6366F1', 'Received', received)}
            ${tooltipRow('#10B981', 'Sent', sent)}
            ${tooltipRow('#06B6D4', 'Conv %', conv)}

          </div>
        </div>
      `;
    },
  },
};

// Tooltip reusable row
function tooltipRow(color, label, value) {
  return `
    <div style="
      display:flex;
      align-items:center;
      justify-content:space-between;
      margin-bottom:14px;
    ">
      <div style="
        display:flex;
        align-items:center;
        gap:10px;
      ">
        <span style="
          width:12px;
          height:12px;
          border-radius:50%;
          background:${color};
          display:inline-block;
        "></span>

        <span style="
          color:#475569;
          font-size:14px;
        ">
          ${label}
        </span>
      </div>

      <strong style="
        color:#0f172a;
        font-size:14px;
      ">
        ${value}
      </strong>
    </div>
  `;
}

var chart = new ApexCharts(
  document.querySelector('#branch_chart'),
  options
);

chart.render();
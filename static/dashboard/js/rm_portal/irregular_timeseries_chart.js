var options = {
  series: [
    {
      name: 'PRODUCT A',
      data: [1200000, 1500000, 1800000, 1700000, 1400000, 1600000, 1900000],
    },
    {
      name: 'PRODUCT B',
      data: [900000, 1300000, 1600000, 1400000, 1200000, 1350000, 1500000],
    },
    {
      name: 'PRODUCT C',
      data: [700000, 1000000, 1250000, 1500000, 1100000, 1300000, 1450000],
    },
  ],

  colors: ['#45d7eb', '#f7b84b', '#f672a7'],

  chart: {
    type: 'area',
    height: 350,
    stacked: false,
    zoom: {
      enabled: false,
    },
  },

  dataLabels: {
    enabled: false,
  },

  markers: {
    size: 4,
  },

  stroke: {
    curve: 'smooth',
    width: 2,
  },

  fill: {
    type: 'gradient',
    gradient: {
      shadeIntensity: 1,
      inverseColors: false,
      opacityFrom: 0.45,
      opacityTo: 0.05,
      stops: [20, 100, 100, 100],
    },
  },

  yaxis: {
    labels: {
      style: {
        colors: '#8e8da4',
      },
      formatter: function (val) {
        return (val / 1000000).toFixed(1) + 'M';
      },
    },
  },

  xaxis: {
    categories: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    labels: {
      style: {
        colors: '#8e8da4',
      },
    },
  },

  title: {
    text: '7 Days Data',
    align: 'left',
  },

  tooltip: {
    shared: true,
    y: {
      formatter: function (val) {
        return (val / 1000000).toFixed(1) + 'M';
      },
    },
  },

  legend: {
    position: 'top',
    horizontalAlign: 'right',
  },
};

var chart = new ApexCharts(
  document.querySelector('#area_chart_irregular_0101'),
  options
);

chart.render();
var options = {
  series: [
    {
      name: 'New Leads',
      type: 'area',
      data: [50, 140, 110, 65, 60, 55, 95, 85, 45, 82, 75, 60, 92, 35],
    },
    {
      name: 'Messages Received',
      type: 'bar',
      data: [55, 305, 320, 240, 160, 302, 360, 400, 190, 240, 275, 155, 340, 35],
    },
    {
      name: 'Messages Sent',
      type: 'bar',
      data: [45, 355, 540, 355, 175, 485, 490, 580, 270, 410, 445, 230, 525, 65],
    },
  ],

  chart: {
    height: 400,
    type: 'line',
    stacked: false,
    toolbar: {
      show: false,
    },
  },

  stroke: {
    width: [4, 0, 0],
    curve: 'smooth',
  },

  colors: ['#f7b84b', '#556ee6', '#34c38f'],

  fill: {
    type: ['gradient', 'solid', 'solid'],
    opacity: [0.6, 1, 1],
    gradient: {
      shade: 'light',
      type: 'vertical',
      opacityFrom: 0.8,
      opacityTo: 0.1,
      stops: [0, 100],
    },
  },

  plotOptions: {
    bar: {
      columnWidth: '35%',
      borderRadius: 5,
    },
  },

  dataLabels: {
    enabled: false,
  },

  grid: {
    borderColor: '#f1f1f1',
    strokeDashArray: 4,
  },

  markers: {
    size: 0,
  },

  xaxis: {
    categories: [
      '20 May',
      '21 May',
      '22 May',
      '23 May',
      '24 May',
      '25 May',
      '26 May',
      '27 May',
      '28 May',
      '29 May',
      '30 May',
      '31 May',
      '01 Jun',
      '02 Jun',
    ],
    axisBorder: {
      show: false,
    },
    axisTicks: {
      show: false,
    },
  },

  yaxis: {
    min: 0,
    max: 600,
    tickAmount: 6,
    labels: {
      formatter: function (val) {
        return val;
      },
    },
  },

  legend: {
    position: 'bottom',
    horizontalAlign: 'left',
    fontSize: '14px',
    markers: {
      radius: 12,
    },
  },

  tooltip: {
    shared: true,
    intersect: false,
  },
};

var chart = new ApexCharts(
  document.querySelector('#chart'),
  options
);

chart.render();
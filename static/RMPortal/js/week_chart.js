var options = {
  series: [25000, 15000, 44000, 55000, 41000, 17000],

  chart: {
    width: 520,
    type: 'donut', // pie → donut
    toolbar: {
      show: false,
    },
  },

  labels: [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
  ],

  // Cute soft colors
  colors: [
    '#6C63FF',
    '#FF6B81',
    '#FFC75F',
    '#00C9A7',
    '#4D96FF',
    '#B983FF',
  ],

  plotOptions: {
    pie: {
      expandOnClick: true,
      donut: {
        size: '68%', // center space
        labels: {
          show: true,

          total: {
            show: true,
            label: 'Total',
            formatter: function (w) {
              const total = w.globals.seriesTotals.reduce(
                (a, b) => a + b,
                0
              );
              return '₹' + total.toLocaleString('en-IN');
            },
          },
        },
      },
    },
  },

  dataLabels: {
    enabled: true,
    style: {
      fontSize: '12px',
      fontWeight: '600',
    },

    formatter: function (val, opts) {
      const amount =
        opts.w.config.series[opts.seriesIndex];

      return '₹' + amount.toLocaleString('en-IN');
    },
  },

  stroke: {
    width: 4,
    colors: ['#fff'], // clean separation
  },

  legend: {
    show: true,
    position: 'right',
    fontSize: '14px',

    markers: {
      radius: 12,
    },

    itemMargin: {
      vertical: 8,
    },

    formatter: function (seriesName, opts) {
      const amount =
        opts.w.globals.series[opts.seriesIndex];

      return (
        seriesName +
        ' - ₹' +
        amount.toLocaleString('en-IN')
      );
    },
  },

  tooltip: {
    y: {
      formatter: function (val) {
        return '₹' + val.toLocaleString('en-IN');
      },
    },
  },
};

var chart = new ApexCharts(
  document.querySelector('#month_pike'),
  options
);

chart.render();
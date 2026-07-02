var options = {
  series: [
    {
      name: 'Income',
      data: [25000, 42000, 35000, 50000], // Week amounts
    },
  ],

  chart: {
    height: 350,
    type: 'bar',

    toolbar: {
      show: false, // remove options
    },
  },

  plotOptions: {
    bar: {
      borderRadius: 12,
      columnWidth: '50%',
      distributed: true,

      dataLabels: {
        position: 'top',
      },
    },
  },

  // Cute colors
  colors: [
    '#6C63FF',
    '#FF6B81',
    '#00C9A7',
    '#FFC75F',
  ],

  dataLabels: {
    enabled: true,

    formatter: function (val) {
      return '₹' + val.toLocaleString('en-IN');
    },

    offsetY: -20,

    style: {
      fontSize: '12px',
      fontWeight: '600',
      colors: ['#444'],
    },
  },

  xaxis: {
    categories: [
      'Week 1',
      'Week 2',
      'Week 3',
      'Week 4',
    ],

    axisBorder: {
      show: false,
    },

    axisTicks: {
      show: false,
    },
  },

  yaxis: {
    labels: {
      formatter: function (val) {
        return '₹' + (val / 1000) + 'K';
      },
    },
  },

  tooltip: {
    y: {
      formatter: function (val) {
        return '₹' + val.toLocaleString('en-IN');
      },
    },
  },

  title: {
    text: 'Current Month Weekly Income',
    align: 'center',

    style: {
      fontSize: '16px',
      fontWeight: '600',
      color: '#444',
    },
  },
};

var chart = new ApexCharts(
  document.querySelector('#month_chart'),
  options
);

chart.render();
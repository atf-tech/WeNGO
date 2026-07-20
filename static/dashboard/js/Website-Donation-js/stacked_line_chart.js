// Backend-injected chart data should already be defined in the template:
//   const homeChartData = {{ home_chart_data|safe }};
//   const serviceChartData = {{ service_chart_data|safe }};

(function initStackedLineChart() {
  const isHomeArray = Array.isArray(window.homeChartData) || Array.isArray(homeChartData);
  const isServiceArray = Array.isArray(window.serviceChartData) || Array.isArray(serviceChartData);

  // Help debugging without breaking rendering.
  console.log('[Website_Donations] homeChartData:', homeChartData);
  console.log('[Website_Donations] serviceChartData:', serviceChartData);

  if (!isHomeArray || !isServiceArray) {
    console.error('[Website_Donations] Chart data is missing or not an array.');
    return;
  }

  const safeHome = homeChartData.map((d) => {
    const y = typeof d.y === 'number' ? d.y : Number(d.y);
    return { x: d.x, y: Number.isFinite(y) ? y : 0 };
  });

  const safeService = serviceChartData.map((d) => {
    const y = typeof d.y === 'number' ? d.y : Number(d.y);
    return { x: d.x, y: Number.isFinite(y) ? y : 0 };
  });

  // Use backend values for axis scaling.
  const allValues = [...safeHome.map((item) => item.y), ...safeService.map((item) => item.y)];
  const maxValue = allValues.length ? Math.max(...allValues) : 0;

  // Dynamic Y-axis max (avoid 0/NaN issues)
  const yAxisMax = Math.ceil(maxValue / 10) * 10 || 10;

  var options = {
    series: [
      {
        name: "Home's",
        data: safeHome,
      },
      {
        name: "Service's",
        data: safeService,
      },
    ],

    chart: {
      type: 'line',
      height: 380,

      toolbar: {
        show: false,
      },

      zoom: {
        enabled: false,
      },
    },

    stroke: {
      curve: 'smooth',
      width: 3,
    },

    dataLabels: {
      enabled: false,
    },

    markers: {
      size: 0,
      hover: {
        size: 6,
      },
    },

    colors: [
      '#D18A00',
      '#FF4D6D',
    ],

    tooltip: {
      shared: true,
      intersect: false,
      theme: 'light',
    },

    legend: {
      position: 'top',
      horizontalAlign: 'center',
    },

    grid: {
      borderColor: '#eef2f7',
      strokeDashArray: 5,
    },

    xaxis: {
      type: 'category',

      title: {
        text: 'Today Time (24 Hours)',
      },

      labels: {
        rotate: -45,
        style: {
          fontSize: '11px',
        },
      },

      axisBorder: {
        show: false,
      },

      axisTicks: {
        show: false,
      },
    },

    yaxis: {
      min: 0,
      max: yAxisMax,
      tickAmount: 5,
      title: {
        text: 'Collections',
      },
      labels: {
        formatter: function (value) {
          return '₹ ' + value;
        }
      }
    },
  };

  // Render Chart
  var el = document.querySelector('#stacked_line');
  if (!el) {
    console.error('[Website_Donations] #stacked_line container not found.');
    return;
  }

  var chart1 = new ApexCharts(el, options);
  chart1.render();
})();




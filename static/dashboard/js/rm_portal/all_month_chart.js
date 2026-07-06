var options = {
    series: [
      {
        name: "Chennai",
        data: [28000, 29000, 33000, 36000, 32000, 32000, 33000]
      },
      {
        name: "Bangalore",
        data: [14000, 11000, 14000, 18000, 17000, 13000, 13000]
      },
      {
        name: "Madurai",
        data: [7000, 11000, 14000, 18000, 17000, 13000, 13000]
      }
    ],
    chart: {
      height: 550,
      type: 'line',
      dropShadow: {
        enabled: true,
        color: '#000',
        top: 18,
        left: 7,
        blur: 10,
        opacity: 0.5
      },
      zoom: {
        enabled: false
      },
      toolbar: {
        show: false
      }
    },
    dataLabels: {
      enabled: true,
    },
    stroke: {
      curve: 'straight',

    },
    grid: {
      borderColor: '#e7e7e7',
      row: {
        colors: ['#f3f3f3', 'transparent'], // takes an array which will be repeated on columns
        opacity: 0.5
      },
    },
    markers: {
      size: 1
    },
    xaxis: {
      categories: [
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'
      ],
      title: {
        text: 'Monthly Based'
      }
    },
    yaxis: {
      title: {
        text: 'Collections'
      },
    },
    legend: {
      show: true,
      position: 'bottom',
      horizontalAlign: 'center',
      markers: { radius: 12 },
      fontSize: '14px',
      itemMargin: {
        horizontal: 10,
        vertical: 8
      }
    },
  };

  

  var chart = new ApexCharts(document.querySelector("#rmPortalBranchChart"), options);
  chart.render();
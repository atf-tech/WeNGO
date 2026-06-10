// Generate one-day hourly time data
function generateTodayTimeSeries() {
  let data = [];

  for (let i = 0; i < 24; i++) {
    let ampm = i >= 12 ? 'PM' : 'AM';
    let displayHour = i % 12 || 12;

    // Example: 12 AM, 01 AM, 02 PM
    let label =
      String(displayHour).padStart(2, '0') +
      ' ' +
      ampm;

    data.push({
      x: label,
      y: Math.floor(Math.random() * 60) + 10,
    });
  }

  return data;
}

var options = {
  series: [
    {
      name: 'Birthday',
      data: generateTodayTimeSeries(),
    },
    {
      name: "Home's",
      data: generateTodayTimeSeries(),
    },
    {
      name: "Service's",
      data: generateTodayTimeSeries(),
    },
    {
      name: "Student's",
      data: generateTodayTimeSeries(),
    },
    {
      name: "Festival's",
      data: generateTodayTimeSeries(),
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
    '#1E88E5',
    '#00A86B',
    '#D18A00',
    '#FF4D6D',
    '#8B6BE8',
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
      rotate: -45, // time overlap avoid
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
    title: {
      text: 'Collections',
    },
  },
};

// Render Chart
var chart1 = new ApexCharts(
  document.querySelector('#stacked_line'),
  options
);

chart1.render();
// Generate 24 hours time (Today)
function generate24Hours() {
  let hours = [];

  for (let i = 0; i < 24; i++) {
    let hour = i;
    let ampm = hour >= 12 ? 'PM' : 'AM';
    let displayHour = hour % 12 || 12;

    hours.push(
      String(displayHour).padStart(2, '0') + ' ' + ampm
    );
  }

  return hours;
} 


const allValues = [
    ...window.hourlyLinkValues,
    ...window.hourlyGpayValues
];

const maxValue = Math.max(...allValues, 0);
const yMax =
    maxValue <= 1000 ? 1000 :
    Math.ceil(maxValue / 1000) * 1000;

var options = {
  
  series: [
    {
      name: 'Link',
      data: window.hourlyLinkValues
    },
    {
      name: 'GPay',
      data: window.hourlyGpayValues
    }
  ],

  chart: {
    height: 350,
    type: 'line',

    // Download option remove
    toolbar: {
      show: false
    }
  },

  stroke: {
    width: 5,
    curve: 'smooth',
  },

  yaxis: {
      min: 0,
      max: yMax,
      tickAmount: 5
  },

  xaxis: {
    categories: generate24Hours(),
    tickAmount: 24,
    labels: {
      rotate: -45,
    },
  },

  title: {
    text: 'Today Sales (24 Hours)',
    align: 'left',
    style: {
      fontSize: '16px',
      color: '#666',
    },
  },

  fill: {
    type: 'gradient',
    gradient: {
      shade: 'dark',
      gradientToColors: ['#f335fd'],
      shadeIntensity: 1,
      type: 'horizontal',
      opacityFrom: 1,
      opacityTo: 1,
      stops: [0, 100],
    },
  },
};

var chart = new ApexCharts(document.querySelector('#gradient01'), options);
chart.render();
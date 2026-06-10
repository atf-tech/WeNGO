// Generate today hour time (AM/PM)
function generateTodayTimeSeries() {
  let data = [];

  for (let i = 0; i < 24; i++) {
    let hour = i;
    let ampm = hour >= 12 ? 'PM' : 'AM';
    let displayHour = hour % 12 || 12;

    let label =
      String(displayHour).padStart(2, '0') + ' ' + ampm;

    data.push({
      x: label,
      y: Math.floor(Math.random() * 60) + 10
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
    background: '#fff',

    toolbar: {
      show: false
    },

    zoom: {
      enabled: false
    },

    dropShadow: {
      enabled: false
    }
  },

  stroke: {
    curve: 'smooth',
    width: 3
  },

  dataLabels: {
    enabled: false
  },

  markers: {
    size: 0,
    hover: {
      size: 6
    }
  },

  tooltip: {
    shared: true,
    intersect: false,
    theme: 'light',

    x: {
      show: true
    }
  },

  colors: [
    '#1E88E5', // Birthday
    '#00A86B', // Home's
    '#D18A00', // Service's
    '#FF4D6D', // Student's
    '#8B6BE8'  // Festival's
  ],

  legend: {
    position: 'top',
    horizontalAlign: 'center',

    fontSize: '14px',
    fontFamily: 'Poppins, sans-serif',
    fontWeight: 500,

    labels: {
      colors: '#6b7280'
    },

    markers: {
      width: 10,
      height: 10,
      radius: 50,
      offsetX: -4
    },

    itemMargin: {
      horizontal: 18,
      vertical: 10
    }
  },

  grid: {
    borderColor: '#eef2f7',
    strokeDashArray: 5,
    padding: {
      top: 10,
      right: 15,
      left: 10,
      bottom: 0
    }
  },

  xaxis: {
    type: 'category',

    labels: {
      style: {
        colors: '#94a3b8',
        fontSize: '12px',
        fontFamily: 'Poppins, sans-serif'
      }
    },

    axisBorder: {
      show: false
    },

    axisTicks: {
      show: false
    },

    title: {
      text: 'Hour Based',
      style: {
        color: '#6b7280',
        fontSize: '14px',
        fontWeight: 600,
        fontFamily: 'Poppins, sans-serif'
      }
    }
  },

  yaxis: {
    labels: {
      style: {
        colors: '#94a3b8',
        fontSize: '12px',
        fontFamily: 'Poppins, sans-serif'
      }
    },

    title: {
      text: 'Collections',
      style: {
        color: '#6b7280',
        fontSize: '14px',
        fontWeight: 600,
        fontFamily: 'Poppins, sans-serif'
      }
    }
  }
};

// Render Chart
var chart1 = new ApexCharts(
  document.querySelector('#cha-line'),
  options
);

chart1.render();
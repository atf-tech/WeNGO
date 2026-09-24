var options = {
    series: [],

    chart: {
        height: 430,
        type: 'polarArea'
    },

    labels: [],

    colors: [
        '#0d6efd', // Blue
        '#20c997', // Green
        '#ffc107', // Yellow
        '#dc3545', // Red
        '#6f42c1', // Purple
        '#fd7e14'  // Orange
    ],

    fill: {
        opacity: 0.9
    },

    stroke: {
        width: 2,
        colors: ['#fff']
    },

    yaxis: {
        show: false
    },

    legend: {
        position: 'bottom'
    },

    plotOptions: {
        polarArea: {
            rings: {
                strokeWidth: 0
            },
            spokes: {
                strokeWidth: 1
            }
        }
    }
};

var chart = new ApexCharts(
    document.querySelector("#polarArea"),
    options
);

chart.render();

// Store globally so loadKpiData() can update it
window.polarChart = chart;

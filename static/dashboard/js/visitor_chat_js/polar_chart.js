var options = {
    series: [42, 47, 52, 58, 65, 72],

    chart: {
        height: 380,
        type: 'polarArea'
    },

    labels: [
        'Waiting',
        'Active',
        'Closed',
        'Missed',
        'Quickly Left',
        'Night Chat'
    ],

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
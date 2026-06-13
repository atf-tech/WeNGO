
var options = {
    series: [{
        name: "Response Time",
        data: [521.4, 63.6, 239.2, 192.6, 556.0, 501.9]
    }],

    chart: {
        type: 'bar',
        height: 350,
        toolbar: {
            show: false
        }
    },

    plotOptions: {
        bar: {
            horizontal: true,
            borderRadius: 6,
            barHeight: '55%',
            distributed: false
        }
    },

    colors: ['#ee775c'],

    dataLabels: {
        enabled: true,
        formatter: function(val) {
            return val.toFixed(1) + " min";
        },
        style: {
            colors: ['#fff'],
            fontSize: '13px',
            fontWeight: 600
        }
    },

    xaxis: {
        categories: ['1.0', '2.0', '3.0', '4.0', '5.0', '6.0'],
        min: 0,
        max: 600,
        labels: {
            formatter: function(val) {
                return val + " min";
            }
        }
    },

    yaxis: {
        labels: {
            style: {
                fontSize: '18px',
                fontWeight: 600
            }
        }
    },

    grid: {
        borderColor: '#e9ecef',
        strokeDashArray: 0
    },

    title: {
        text: '⏱ Response Time per RM',
        align: 'left',
        style: {
            fontSize: '22px',
            fontWeight: 'bold'
        }
    },

    legend: {
        position: 'top',
        horizontalAlign: 'right'
    },


    
    tooltip: {
        y: {
            formatter: function(val) {
                return val + " min";
            }
        }
    }
};


var chart = new ApexCharts(
    document.querySelector("#TimeChart"),
    options
);


chart.render();


var options = {
    series: [{
        name: "Response Time",
        data: []
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
        categories: [],
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


var responseTimeChart = new ApexCharts(
    document.querySelector("#TimeChart"),
    options
);


responseTimeChart.render();
window.responseTimeChart = responseTimeChart;

function responseTimeChartQueryParams() {
    const params = new URLSearchParams({
        chart: typeof gChart !== 'undefined' ? gChart : 'daily',
        period: typeof gPeriod !== 'undefined' ? gPeriod : 'today',
        branch: typeof gBranch !== 'undefined' ? gBranch : '',
    });

    if (typeof gPeriod !== 'undefined' && gPeriod === 'custom') {
        const from = document.getElementById('customFrom')?.value;
        const to = document.getElementById('customTo')?.value;
        if (from) params.set('from_date', from);
        if (to) params.set('to_date', to);
    }

    return params;
}

window.loadResponseTimeChart = function () {
    return fetch(`/dashboard/visitor_chat/api/charts/?${responseTimeChartQueryParams().toString()}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin'
    })
        .then(function(response) {
            if (!response.ok) throw new Error("HTTP " + response.status);
            return response.json();
        })
        .then(function(data) {
            if (!data || !data.response || !window.responseTimeChart) return;

            window.responseTimeChart.updateOptions({
                xaxis: {
                    categories: data.response.categories || []
                }
            });
            window.responseTimeChart.updateSeries([
                {
                    name: "Response Time",
                    data: data.response.data || []
                }
            ]);
        })
        .catch(function(error) {
            console.error("Response time chart error:", error);
        });
};
